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


class UpdateKnowledgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        shutil.copytree(SOURCE_ROOT / "ai", self.root / "ai")
        task_dir = self.root / "ai" / "tasks" / "TEST-1"
        task_dir.mkdir(parents=True)
        (task_dir / "task.yaml").write_text("id: TEST-1\n", encoding="utf-8")
        (task_dir / "state.yaml").write_text("status: completed\n", encoding="utf-8")
        (task_dir / "knowledge-updates.json").write_text(
            json.dumps(
                {
                    "task_id": "TEST-1",
                    "updates": [
                        {
                            "target": "ai/repos/backend/architecture.md",
                            "type": "proposal",
                            "summary": "first",
                            "content": "first content",
                            "approved": True,
                        },
                        {
                            "target": "ai/repos/backend/architecture.md",
                            "type": "proposal",
                            "summary": "second",
                            "content": "second content",
                            "approved": True,
                        },
                        {
                            "target": "ai/repos/backend/testing.md",
                            "type": "proposal",
                            "summary": "unapproved",
                            "content": "not applied",
                            "approved": False,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "ai" / "bin" / "update-knowledge"), "TEST-1", *args],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_plan_lists_approved_and_unapproved_entries(self) -> None:
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("[x] #001 proposal", result.stdout)
        self.assertIn("[ ] #003 proposal", result.stdout)
        self.assertIn("Plan only: 3 total, 2 approved", result.stdout)

    def test_proposals_for_same_target_do_not_overwrite(self) -> None:
        result = self.run_command("--apply")
        self.assertEqual(result.returncode, 0, result.stdout)
        proposal_dir = self.root / "ai" / "tasks" / "TEST-1" / "knowledge-proposals"
        proposals = sorted(proposal_dir.glob("*.md"))
        self.assertEqual(len(proposals), 2)
        self.assertIn("first content", proposals[0].read_text(encoding="utf-8"))
        self.assertIn("second content", proposals[1].read_text(encoding="utf-8"))

    def test_append_is_idempotent(self) -> None:
        task_dir = self.root / "ai" / "tasks" / "TEST-1"
        target = self.root / "ai" / "repos" / "backend" / "testing.md"
        data = json.loads((task_dir / "knowledge-updates.json").read_text(encoding="utf-8"))
        data["updates"] = [
            {
                "target": "ai/repos/backend/testing.md",
                "type": "append",
                "summary": "append once",
                "content": "## Stable section\n\nDurable rule.",
                "approved": True,
            }
        ]
        (task_dir / "knowledge-updates.json").write_text(json.dumps(data), encoding="utf-8")

        first = self.run_command("--apply")
        second = self.run_command("--apply")

        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(target.read_text(encoding="utf-8").count("## Stable section"), 1)
        self.assertIn("Already applied; skipped duplicate append", second.stdout)


if __name__ == "__main__":
    unittest.main()
