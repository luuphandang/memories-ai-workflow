from __future__ import annotations
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "create-task"
SPEC = importlib.util.spec_from_loader("create_task_script", SourceFileLoader("create_task_script", str(SCRIPT)))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class CreateTaskWorktreeTest(unittest.TestCase):
    def test_kebab_case_supports_vietnamese_and_symbols(self):
        self.assertEqual(MODULE.kebab_case("Đón ký ức: Mùa Hè!"), "don-ky-uc-mua-he")

    def test_epic_uses_master(self):
        self.assertEqual(MODULE.base_ref_for("epic", None), "origin/master")

    def test_child_uses_parent_registered_branch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); parent = root / "MEMORIES-10"; parent.mkdir()
            (parent / "task.yaml").write_text(yaml.safe_dump({"jira":{"type":"epic"}}))
            (parent / "state.yaml").write_text(yaml.safe_dump({"repositories":{
                "backend":{"branch":"epic/MEMORIES-10-parent"},
                "frontend":{"branch":"epic/MEMORIES-10-parent"},
            }}))
            with patch.object(MODULE, "task_dir", side_effect=lambda task_id: root / task_id):
                self.assertEqual(MODULE.base_ref_for("story", "MEMORIES-10"), "origin/epic/MEMORIES-10-parent")

    def test_parent_repositories_must_share_branch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); parent = root / "MEMORIES-10"; parent.mkdir()
            (parent / "task.yaml").write_text(yaml.safe_dump({"jira":{"type":"story"}}))
            (parent / "state.yaml").write_text(yaml.safe_dump({"repositories":{
                "backend":{"branch":"story/one"}, "frontend":{"branch":"story/two"},
            }}))
            with patch.object(MODULE, "task_dir", side_effect=lambda task_id: root / task_id):
                with self.assertRaises(SystemExit): MODULE.base_ref_for("task", "MEMORIES-10")

if __name__ == "__main__": unittest.main()
