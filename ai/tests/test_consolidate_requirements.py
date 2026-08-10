#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]
DRAFT_NAME = "requirements-consolidation-draft.md"
MANIFEST_NAME = "requirements-consolidation-manifest.json"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ApplyRequirementsConsolidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        shutil.copytree(SOURCE_ROOT / "ai", self.root / "ai")
        self.task_dir = self.root / "ai" / "tasks" / "TEST-1"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "task.yaml").write_text("id: TEST-1\n", encoding="utf-8")
        (self.task_dir / "task.md").write_text("# Original task\n\nOriginal requirement.\n", encoding="utf-8")
        (self.task_dir / "state.yaml").write_text(
            yaml.safe_dump({"status": "completed", "change_cycle": 2}), encoding="utf-8"
        )
        for cycle in (1, 2):
            cycle_dir = self.task_dir / "changes" / f"cycle-{cycle:03d}"
            cycle_dir.mkdir(parents=True)
            (cycle_dir / "requirement-addendum.md").write_text(
                f"# Addendum cycle {cycle}\n\nChange from cycle {cycle}.\n", encoding="utf-8"
            )
            (cycle_dir / "user-request.md").write_text(f"User request {cycle}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_apply(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "ai" / "bin" / "apply-requirements-consolidation"), "TEST-1", *args],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def set_state_field(self, key: str, value) -> None:
        state = yaml.safe_load((self.task_dir / "state.yaml").read_text(encoding="utf-8"))
        state[key] = value
        (self.task_dir / "state.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")

    def write_manifest_and_draft(
        self, draft_text: str = "# Consolidated task\n\nFolded requirement.\n", **manifest_overrides
    ) -> tuple[Path, Path]:
        """Write a self-consistent draft + manifest pair reflecting the current
        on-disk task.md/addenda content, then apply any deliberate overrides."""
        draft_path = self.task_dir / DRAFT_NAME
        manifest_path = self.task_dir / MANIFEST_NAME
        draft_path.write_text(draft_text, encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "task_id": "TEST-1",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "source_task_md_sha256": sha256_of(self.task_dir / "task.md"),
            "source_consolidated_through_cycle": 0,
            "target_change_cycle": 2,
            "addenda": [
                {
                    "path": f"ai/tasks/TEST-1/changes/cycle-{cycle:03d}/requirement-addendum.md",
                    "sha256": sha256_of(self.task_dir / "changes" / f"cycle-{cycle:03d}" / "requirement-addendum.md"),
                }
                for cycle in (1, 2)
            ],
            "draft_path": f"ai/tasks/TEST-1/{DRAFT_NAME}",
            "draft_sha256": sha256_of(draft_path),
        }
        manifest.update(manifest_overrides)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return draft_path, manifest_path

    # --- preconditions -----------------------------------------------------

    def test_apply_requires_draft(self) -> None:
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing requirements consolidation draft", result.stdout)

    def test_missing_manifest_is_rejected(self) -> None:
        (self.task_dir / DRAFT_NAME).write_text("# Consolidated\n\nSome content.\n", encoding="utf-8")
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing requirements consolidation manifest", result.stdout)

    def test_empty_approver_is_rejected(self) -> None:
        self.write_manifest_and_draft()
        result = self.run_apply("--approved-by", "   ")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--approved-by must be non-empty", result.stdout)

    def test_apply_rejects_empty_draft(self) -> None:
        self.write_manifest_and_draft(draft_text="   \n")
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("draft is empty", result.stdout)

    # --- tamper/staleness detection -----------------------------------------

    def test_stale_task_md_is_rejected(self) -> None:
        self.write_manifest_and_draft()
        (self.task_dir / "task.md").write_text("# Original task\n\nEDITED after manifest generation.\n", encoding="utf-8")
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task.md has changed", result.stdout)

    def test_changed_addendum_is_rejected(self) -> None:
        self.write_manifest_and_draft()
        (self.task_dir / "changes" / "cycle-001" / "requirement-addendum.md").write_text(
            "EDITED addendum after manifest generation\n", encoding="utf-8"
        )
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("addendum changed", result.stdout)

    def test_changed_draft_is_rejected(self) -> None:
        draft_path, _ = self.write_manifest_and_draft()
        draft_path.write_text("# Tampered draft\n\nEdited after generation.\n", encoding="utf-8")
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("draft was edited", result.stdout)

    def test_old_pre_existing_draft_is_rejected(self) -> None:
        # Draft/manifest are internally self-consistent, but a different consolidation
        # already advanced requirements_consolidated_through_cycle in the meantime, so
        # this is now a stale leftover draft from before that happened.
        self.write_manifest_and_draft()
        self.set_state_field("requirements_consolidated_through_cycle", 1)
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale draft", result.stdout)

    def test_cycle_mismatch_is_rejected(self) -> None:
        # A new requirement-change cycle was opened after the draft was generated, so
        # the draft's target_change_cycle no longer matches the current one.
        self.write_manifest_and_draft()
        self.set_state_field("change_cycle", 3)
        result = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out-of-cycle", result.stdout)

    # --- happy path ----------------------------------------------------------

    def test_valid_apply_succeeds_and_preserves_provenance(self) -> None:
        self.write_manifest_and_draft()
        result = self.run_apply("--approved-by", "tester")
        self.assertEqual(result.returncode, 0, result.stdout)

        self.assertEqual(
            (self.task_dir / "task.md").read_text(encoding="utf-8"),
            "# Consolidated task\n\nFolded requirement.\n",
        )
        self.assertFalse((self.task_dir / DRAFT_NAME).exists())
        self.assertFalse((self.task_dir / MANIFEST_NAME).exists())

        history_dirs = list((self.task_dir / "task-md-history").iterdir())
        self.assertEqual(len(history_dirs), 1)
        history_dir = history_dirs[0]
        self.assertIn("Original requirement.", (history_dir / "task.md").read_text(encoding="utf-8"))
        self.assertTrue((history_dir / DRAFT_NAME).is_file())
        self.assertTrue((history_dir / MANIFEST_NAME).is_file())

        state = yaml.safe_load((self.task_dir / "state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["requirements_consolidated_through_cycle"], 2)
        self.assertEqual(len(state["requirements_consolidation_history"]), 1)
        self.assertEqual(state["requirements_consolidation_history"][0]["approved_by"], "tester")
        self.assertEqual(state["requirements_consolidation_history"][0]["folded_cycles"], "1..2")

    def test_apply_rejects_second_run_without_new_draft(self) -> None:
        self.write_manifest_and_draft()
        first = self.run_apply("--approved-by", "tester")
        self.assertEqual(first.returncode, 0, first.stdout)

        second = self.run_apply("--approved-by", "tester")
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("No pending consolidation draft", second.stdout)


if __name__ == "__main__":
    unittest.main()
