from __future__ import annotations

from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import ai.bin.lib.integration as integration_module
from ai.bin.lib.coordination import CoordinationConflict, CoordinationStore
from ai.bin.lib.integration import IntegrationError, IntegrationGate, IntegrationQueue, integration_fingerprint, manifest_fresh


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class IntegrationGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "master")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "value.txt").write_text("base\n")
        git(self.repo, "add", "value.txt")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "branch", "target")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self, commands: list[str]) -> dict:
        return IntegrationGate().validate(
            task_id="TASK-A", repository="backend", source=self.repo, base_sha=self.base,
            target_ref="target", plan_version=1, dependency_versions={}, validation_commands=commands,
        )

    def test_clean_change_becomes_merge_ready(self) -> None:
        (self.repo / "new.txt").write_text("new\n")
        result = self.validate(["git diff --check"])
        self.assertEqual(result["status"], "MERGE_READY")
        self.assertTrue(result["integration_tree_sha"])

    def test_empty_validation_cannot_be_merge_ready(self) -> None:
        with self.assertRaises(IntegrationError):
            self.validate([])

    def test_textual_conflict_is_reported(self) -> None:
        (self.repo / "value.txt").write_text("source\n")
        target_tree = Path(self.temp.name) / "target-tree"
        git(self.repo, "worktree", "add", "-q", str(target_tree), "target")
        git(target_tree, "config", "user.email", "test@example.invalid")
        git(target_tree, "config", "user.name", "Test")
        (target_tree / "value.txt").write_text("target\n")
        git(target_tree, "add", "value.txt")
        git(target_tree, "commit", "-qm", "target change")
        result = self.validate(["git diff --check"])
        self.assertEqual(result["status"], "CONFLICTED")

    def test_combined_validation_can_reject_clean_textual_integration(self) -> None:
        (self.repo / "new.txt").write_text("new\n")
        result = self.validate(["sh -c false"])
        self.assertEqual(result["status"], "CONFLICTED")
        self.assertEqual(result["validation"][0]["exit_code"], 1)

    def test_untracked_file_cannot_overwrite_target_silently(self) -> None:
        target_tree = Path(self.temp.name) / "target-untracked-conflict"
        git(self.repo, "worktree", "add", "-q", str(target_tree), "target")
        git(target_tree, "config", "user.email", "test@example.invalid")
        git(target_tree, "config", "user.name", "Test")
        (target_tree / "collision.txt").write_text("target\n")
        git(target_tree, "add", "collision.txt")
        git(target_tree, "commit", "-qm", "target owns collision")
        (self.repo / "collision.txt").write_text("source untracked\n")
        result = self.validate(["git diff --check"])
        self.assertEqual(result["status"], "CONFLICTED")
        self.assertIn("Untracked source file conflicts", result["conflict_output"])

    def test_unavailable_dependency_blocks_integration(self) -> None:
        with self.assertRaises(IntegrationError):
            IntegrationGate().validate(
                task_id="TASK-A", repository="backend", source=self.repo, base_sha=self.base,
                target_ref="target", plan_version=1,
                dependency_versions={"user.create": {"status": "BUILDING", "version": 1}},
                validation_commands=["git diff --check"],
            )

    def test_manifest_stales_when_source_changes(self) -> None:
        current = integration_fingerprint(self.repo, "target", plan_version=1, dependency_versions={})
        manifest = dict(current)
        (self.repo / "new.txt").write_text("changed\n")
        latest = integration_fingerprint(self.repo, "target", plan_version=1, dependency_versions={})
        result = manifest_fresh(manifest, latest)
        self.assertFalse(result["fresh"])
        self.assertIn("source_dirty_snapshot", result["changed"])

    def test_manifest_stales_when_target_advances(self) -> None:
        manifest = integration_fingerprint(self.repo, "target", plan_version=1, dependency_versions={})
        target_tree = Path(self.temp.name) / "target-advance"
        git(self.repo, "worktree", "add", "-q", str(target_tree), "target")
        git(target_tree, "config", "user.email", "test@example.invalid")
        git(target_tree, "config", "user.name", "Test")
        (target_tree / "target.txt").write_text("advance\n")
        git(target_tree, "add", "target.txt")
        git(target_tree, "commit", "-qm", "advance target")
        latest = integration_fingerprint(self.repo, "target", plan_version=1, dependency_versions={})
        result = manifest_fresh(manifest, latest)
        self.assertFalse(result["fresh"])
        self.assertIn("target_sha", result["changed"])

    def test_queue_serializes_same_resource(self) -> None:
        queue = IntegrationQueue(CoordinationStore(Path(self.temp.name) / "coordination"))
        with queue.claim("TASK-A", ["backend:src/user.ts"]):
            with self.assertRaises(CoordinationConflict):
                with queue.claim("TASK-B", ["backend:src/user.ts"]):
                    pass

    def test_delivery_readiness_requires_current_merge_ready_manifest(self) -> None:
        task_dir = Path(self.temp.name) / "task"
        runtime = Path(self.temp.name) / "runtime"
        task_dir.mkdir()
        (task_dir / "task.yaml").write_text(
            "worktrees:\n  - repo: backend\n    path: ignored\n    base_ref: target\n    target_ref: target\n    writable: true\n"
        )
        (task_dir / "execution-plan.json").write_text(json.dumps({
            "task_id": "TASK-A", "plan_version": 1,
            "slices": [{"id": "slice", "external_dependencies": [], "resource_accesses": [{
                "repository": "backend", "path": "new.txt", "access": "WRITE", "visibility": "SHARED"
            }]}],
        }))
        manifest_path = runtime / "integration" / "backend.json"
        manifest_path.parent.mkdir(parents=True)
        IntegrationGate().validate(
            task_id="TASK-A", repository="backend", source=self.repo, base_sha=self.base,
            target_ref="target", plan_version=1, dependency_versions={},
            validation_commands=["git diff --check"], manifest_path=manifest_path,
        )
        with patch.object(integration_module, "task_dir", return_value=task_dir), patch.object(
            integration_module, "runtime_dir", return_value=runtime
        ), patch.object(integration_module, "safe_workspace_path", return_value=self.repo), patch.object(
            integration_module, "dependency_snapshot", return_value={}
        ):
            integration_module.verify_integration_ready("TASK-A")
            (self.repo / "new.txt").write_text("changed after integration\n")
            with self.assertRaises(SystemExit):
                integration_module.verify_integration_ready("TASK-A")


if __name__ == "__main__":
    unittest.main()
