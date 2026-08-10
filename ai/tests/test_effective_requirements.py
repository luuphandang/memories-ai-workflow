#!/usr/bin/env python3
"""Unit coverage for the canonical effective-requirements resolver
(lib.ai_common.requirement_documents) used consistently by run-claude,
run-codex-review, prepare-plan and prepare-context."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def load_ai_common(root: Path):
    path = root / "ai" / "bin" / "lib" / "ai_common.py"
    spec = importlib.util.spec_from_file_location("ai_common_effective_requirements", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class EffectiveRequirementsResolverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        shutil.copytree(SOURCE_ROOT / "ai", self.root / "ai")
        self.task_dir = self.root / "ai" / "tasks" / "TEST-1"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "task.yaml").write_text("id: TEST-1\n", encoding="utf-8")
        (self.task_dir / "task.md").write_text("# Original task\n\nOriginal requirement.\n", encoding="utf-8")
        self.state_path = self.task_dir / "state.yaml"
        self.state_path.write_text(yaml.safe_dump({"status": "completed", "change_cycle": 2}), encoding="utf-8")
        for cycle in (1, 2):
            self.add_cycle(cycle)
        self.ai_common = load_ai_common(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add_cycle(self, cycle: int) -> None:
        cycle_dir = self.task_dir / "changes" / f"cycle-{cycle:03d}"
        cycle_dir.mkdir(parents=True)
        (cycle_dir / "requirement-addendum.md").write_text(
            f"# Addendum cycle {cycle}\n\nChange from cycle {cycle}.\n", encoding="utf-8"
        )
        (cycle_dir / "user-request.md").write_text(f"User request {cycle}\n", encoding="utf-8")

    def set_consolidated_through(self, value: int) -> None:
        state = yaml.safe_load(self.state_path.read_text(encoding="utf-8"))
        state["requirements_consolidated_through_cycle"] = value
        self.state_path.write_text(yaml.safe_dump(state), encoding="utf-8")

    def active(self) -> list[str]:
        return self.ai_common.requirement_documents("TEST-1")

    def addendum(self, cycle: int) -> str:
        return f"ai/tasks/TEST-1/changes/cycle-{cycle:03d}/requirement-addendum.md"

    def test_no_consolidation_includes_task_md_and_all_addenda_in_order(self) -> None:
        docs = self.active()
        self.assertEqual(docs[0], "ai/tasks/TEST-1/task.md")
        self.assertIn(self.addendum(1), docs)
        self.assertIn(self.addendum(2), docs)
        self.assertLess(docs.index(self.addendum(1)), docs.index(self.addendum(2)))

    def test_partial_consolidation_excludes_only_folded_cycles(self) -> None:
        self.set_consolidated_through(1)
        docs = self.active()
        self.assertIn("ai/tasks/TEST-1/task.md", docs)
        self.assertNotIn(self.addendum(1), docs)
        self.assertIn(self.addendum(2), docs)

    def test_all_cycles_consolidated_leaves_only_task_md(self) -> None:
        self.set_consolidated_through(2)
        docs = self.active()
        self.assertEqual(docs, ["ai/tasks/TEST-1/task.md"])

    def test_new_cycle_after_consolidation_is_included_and_prior_ones_stay_excluded(self) -> None:
        self.set_consolidated_through(2)
        self.add_cycle(3)
        docs = self.active()
        self.assertEqual(
            docs,
            ["ai/tasks/TEST-1/task.md", self.addendum(3), "ai/tasks/TEST-1/changes/cycle-003/user-request.md"],
        )
        self.assertNotIn(self.addendum(1), docs)
        self.assertNotIn(self.addendum(2), docs)

    def test_audit_mode_is_never_affected_by_consolidation(self) -> None:
        self.set_consolidated_through(2)
        self.add_cycle(3)
        docs = self.ai_common.requirement_documents("TEST-1", audit=True)
        self.assertIn(self.addendum(1), docs)
        self.assertIn(self.addendum(2), docs)
        self.assertIn(self.addendum(3), docs)

    def test_prepare_plan_avoids_duplicate_slices_after_consolidation(self) -> None:
        # Overwrite the default fixture with checkbox-bearing requirement text so
        # prepare-plan's heading/checkbox scan produces distinct sections.
        (self.task_dir / "task.md").write_text(
            "### Section A\n\n- [ ] Do thing A\n", encoding="utf-8"
        )
        (self.task_dir / "changes" / "cycle-001" / "requirement-addendum.md").write_text(
            "### Section A Replacement\n\n- [ ] Do replacement thing A\n", encoding="utf-8"
        )

        def run_prepare_plan() -> dict:
            prepare_plan = self.root / "ai" / "bin" / "prepare-plan"
            result = subprocess.run(
                [sys.executable, str(prepare_plan), "TEST-1", "--force"],
                cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            return json.loads((self.task_dir / "execution-plan.json").read_text(encoding="utf-8"))

        before = run_prepare_plan()
        self.assertEqual(len(before["slices"]), 2)  # task.md section + addendum's own section

        self.set_consolidated_through(1)
        after = run_prepare_plan()
        self.assertEqual(len(after["slices"]), 1)  # cycle-001 addendum no longer scanned separately
        self.assertEqual(after["slices"][0]["title"], "Section A")


if __name__ == "__main__":
    unittest.main()
