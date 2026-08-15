#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]

TASK_YAML = """\
version: 1
id: TEST-9
title: Memory test task
jira:
  type: task
status: ready
worktrees: []
agents:
  implementer: claude
  reviewer: codex
skills:
  implement: []
  review: []
scope:
  execution_plan_required: false
review:
  max_cycles: 5
  fail_on: [blocker, major]
validation: {{}}
report:
  language: vi
  include_diff_stat: false
  include_changed_files: false
  include_test_results: false
  include_review_findings: false
  include_knowledge_updates: false
{memory_block}
"""

CONTEXT_YAML = """\
version: 1
mandatory: []
repositories: {}
domains: []
exclude: []
"""

TASK_MD = "# Memory test task\n\n## Mo ta\n\nDeterministic fixture for memory integration tests.\n"


class MemoryIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="ai-memory-test-")
        self.root = Path(self.temp_dir.name)
        shutil.copytree(SOURCE_ROOT / "ai", self.root / "ai")
        self.task_dir = self.root / "ai" / "tasks" / "TEST-9"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "task.md").write_text(TASK_MD, encoding="utf-8")
        (self.task_dir / "context.yaml").write_text(CONTEXT_YAML, encoding="utf-8")
        (self.task_dir / "knowledge-updates.json").write_text(
            json.dumps({"task_id": "TEST-9", "updates": []}), encoding="utf-8"
        )
        self.write_task_yaml()
        self.write_state()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_task_yaml(self, memory_block: str = "") -> None:
        (self.task_dir / "task.yaml").write_text(
            TASK_YAML.format(memory_block=memory_block), encoding="utf-8"
        )

    def write_state(self, **fields: object) -> None:
        defaults = {"status": "created", "implementation_cycle": 1, "change_cycle": 0}
        defaults.update(fields)
        lines = "\n".join(f"{key}: {value}" for key, value in defaults.items())
        (self.task_dir / "state.yaml").write_text(lines + "\n", encoding="utf-8")

    def write_acceptance(self, status: str) -> None:
        (self.task_dir / "acceptance.yaml").write_text(
            f"task_id: TEST-9\nstatus: {status}\n", encoding="utf-8"
        )

    def run_script(
        self, script: str, args: list[str], env: dict[str, str], expected: int | None = None
    ) -> subprocess.CompletedProcess[str]:
        import os

        result = subprocess.run(
            [sys.executable, str(self.root / "ai" / "bin" / script), *args],
            cwd=self.root,
            env={**os.environ, **env},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
        if expected is not None:
            self.assertEqual(
                result.returncode, expected, f"{script} {' '.join(args)}\n{result.stdout}"
            )
        return result

    # -- disabled ---------------------------------------------------------

    def test_disabled_writes_nothing_and_reports_disabled(self) -> None:
        result = self.run_script(
            "memory-recall", ["TEST-9"], {"AI_MEMORY_ENABLED": "false"}, expected=0
        )
        self.assertEqual(json.loads(result.stdout), {"enabled": False})
        self.assertFalse((self.task_dir / "memory" / "recall.json").exists())

    # -- available ----------------------------------------------------------

    def test_available_writes_snapshot_hash_and_lock(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n")
        self.run_script(
            "prepare-context",
            ["TEST-9"],
            {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake"},
            expected=0,
        )
        snapshot = json.loads((self.task_dir / "memory" / "recall.json").read_text(encoding="utf-8"))
        self.assertTrue(snapshot["available"])
        self.assertTrue(snapshot["content_sha256"])
        self.assertTrue((self.task_dir / "memory" / "recall.md").is_file())

        lock = json.loads((self.task_dir / "context.lock.json").read_text(encoding="utf-8"))
        self.assertTrue(lock["memory"]["enabled"])
        self.assertTrue(lock["memory"]["available"])
        self.assertEqual(lock["memory"]["sha256"], snapshot["content_sha256"])

    # -- unavailable + optional ---------------------------------------------

    def test_unavailable_optional_warns_and_falls_back(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n  required: false\n")
        result = self.run_script(
            "prepare-context",
            ["TEST-9"],
            {
                "AI_MEMORY_ENABLED": "true",
                "AI_MEMORY_PROVIDER": "tencentdb",
                "AI_MEMORY_BASE_URL": "http://127.0.0.1:1",
                "AI_MEMORY_TIMEOUT_SECONDS": "2",
            },
            expected=0,
        )
        self.assertIn("WARNING: backend unavailable", result.stdout)
        lock = json.loads((self.task_dir / "context.lock.json").read_text(encoding="utf-8"))
        self.assertFalse(lock["memory"]["available"])
        self.assertEqual(lock["memory"]["fallback"], "static_context")
        self.assertEqual(lock["memory"]["error_code"], "MEMORY_UNAVAILABLE")

    # -- unavailable + required ----------------------------------------------

    def test_unavailable_required_blocks(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n  required: true\n")
        result = self.run_script(
            "prepare-context",
            ["TEST-9"],
            {
                "AI_MEMORY_ENABLED": "true",
                "AI_MEMORY_PROVIDER": "tencentdb",
                "AI_MEMORY_BASE_URL": "http://127.0.0.1:1",
                "AI_MEMORY_TIMEOUT_SECONDS": "2",
            },
            expected=1,
        )
        self.assertIn("memory recall unavailable", result.stdout)
        self.assertFalse((self.task_dir / "context.lock.json").exists())

    # -- stale snapshot -------------------------------------------------------

    def test_stale_snapshot_not_reused_across_cycles(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n")
        env = {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake"}
        self.run_script("prepare-context", ["TEST-9"], env, expected=0)
        first = json.loads((self.task_dir / "memory" / "recall.json").read_text(encoding="utf-8"))
        self.assertEqual(first["implementation_cycle"], 1)

        self.write_state(status="created", implementation_cycle=2, change_cycle=0)
        self.run_script("prepare-context", ["TEST-9"], env, expected=0)
        second = json.loads((self.task_dir / "memory" / "recall.json").read_text(encoding="utf-8"))
        self.assertEqual(second["implementation_cycle"], 2)
        self.assertNotEqual(first["implementation_cycle"], second["implementation_cycle"])

    # -- publish gating -------------------------------------------------------

    def test_publish_before_acceptance_rejected(self) -> None:
        result = self.run_script(
            "memory-publish",
            ["TEST-9"],
            {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake"},
            expected=1,
        )
        self.assertIn("state.status == completed", result.stdout)

    def test_publish_after_completed_accepted_allowed(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n")
        self.write_state(status="completed", implementation_cycle=1, change_cycle=0)
        self.write_acceptance("accepted")
        (self.task_dir / "knowledge-updates.json").write_text(
            json.dumps(
                {
                    "task_id": "TEST-9",
                    "updates": [
                        {
                            "target": "ai/repos/backend/known-issues.md",
                            "type": "append",
                            "summary": "Deterministic fixture",
                            "content": "## Fixture\n\nDeterministic content.",
                            "approved": True,
                            "category": "known_issue",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = self.run_script(
            "memory-publish",
            ["TEST-9"],
            {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake"},
            expected=0,
        )
        published = json.loads(result.stdout)
        self.assertEqual(len(published["published"]), 1)
        self.assertEqual(published["published"][0]["category"], "known_issue")

    # -- correction archival ---------------------------------------------------

    def test_correction_archives_snapshot_and_still_blocks_publish(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n")
        env = {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake"}
        self.run_script("prepare-context", ["TEST-9"], env, expected=0)
        self.write_state(status="awaiting_user_acceptance", implementation_cycle=1, change_cycle=0)

        result = self.run_script(
            "request-change",
            ["TEST-9", "--kind", "correction", "--title", "Fixture correction"],
            {},
            expected=0,
        )
        self.assertIn("Created correction cycle", result.stdout)
        archived = self.task_dir / "changes" / "cycle-001" / "baseline" / "memory" / "recall.json"
        self.assertTrue(archived.is_file())

        publish_result = self.run_script("memory-publish", ["TEST-9"], env, expected=1)
        self.assertIn("state.status == completed", publish_result.stdout)

    # -- secrets never leak ------------------------------------------------

    def test_no_secret_written_to_any_artifact(self) -> None:
        self.write_task_yaml("memory:\n  enabled: true\n")
        secret = "sk-mem-thisistestonlyvalue1234567890"
        env = {"AI_MEMORY_ENABLED": "true", "AI_MEMORY_PROVIDER": "fake", "AI_MEMORY_API_KEY": secret}
        result = self.run_script("prepare-context", ["TEST-9"], env, expected=0)
        self.assertNotIn(secret, result.stdout)

        health_result = self.run_script("memory-health", [], env, expected=None)
        self.assertNotIn(secret, health_result.stdout)

        for path in self.task_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.assertNotIn(secret, text, f"secret leaked into {path}")


if __name__ == "__main__":
    unittest.main()
