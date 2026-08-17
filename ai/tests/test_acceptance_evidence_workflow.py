from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess


AI_ROOT = Path(__file__).resolve().parents[1]


def load_run_task_module():
    path = AI_ROOT / "bin" / "run-task"
    loader = SourceFileLoader("run_task", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AcceptanceEvidenceWorkflowTest(unittest.TestCase):
    def test_no_progress_guard_only_stops_failed_unchanged_attempts(self) -> None:
        module = load_run_task_module()
        self.assertTrue(module.is_no_progress_failure(1, "failed", "same", "same"))
        self.assertFalse(module.is_no_progress_failure(0, "prepared", "same", "same"))
        self.assertFalse(module.is_no_progress_failure(1, "failed", "before", "after"))

    def test_repository_fingerprint_detects_code_progress(self) -> None:
        module = load_run_task_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            source = repo / "source.txt"
            source.write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "source.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            task = {"worktrees": [{"repo": "test", "path": "repo"}]}
            with patch.object(module, "ROOT", root):
                before = module.repository_fingerprint(task)
                self.assertEqual(before, module.repository_fingerprint(task))
                source.write_text("after\n", encoding="utf-8")
                self.assertNotEqual(before, module.repository_fingerprint(task))

    def test_delivery_gate_fix_request_includes_missing_criteria(self) -> None:
        module = load_run_task_module()
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            gate_path = runtime / "validation" / "skills" / "delivery-gates.json"
            gate_path.parent.mkdir(parents=True)
            gate_path.write_text(
                json.dumps(
                    {
                        "checks": [
                            {
                                "name": "acceptance-evidence",
                                "passed": False,
                                "missing": ["Module boundary", "Tests"],
                            }
                        ],
                        "passed": False,
                        "failures": ["acceptance-evidence"],
                    }
                ),
                encoding="utf-8",
            )
            (runtime / "input").mkdir()
            with patch.object(module, "runtime_dir", return_value=runtime):
                result = module.delivery_gate_fix_request("TEST-1", 1)
            content = result.read_text(encoding="utf-8")
            self.assertIn("slice:<slice-id>", content)
            self.assertIn("missing: Module boundary", content)
            self.assertIn("missing: Tests", content)

    def test_delivery_gate_fix_request_is_not_created_for_passing_gate(self) -> None:
        module = load_run_task_module()
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            gate_path = runtime / "validation" / "skills" / "delivery-gates.json"
            gate_path.parent.mkdir(parents=True)
            gate_path.write_text(
                json.dumps({"passed": True, "checks": [], "failures": []}),
                encoding="utf-8",
            )
            (runtime / "input").mkdir()
            with patch.object(module, "runtime_dir", return_value=runtime):
                result = module.delivery_gate_fix_request("TEST-1", 1)
            self.assertIsNone(result)
            self.assertFalse((runtime / "input" / "fix-request-delivery-gates-attempt-001.md").exists())

    def test_delivery_gate_fix_request_is_not_created_without_failures(self) -> None:
        module = load_run_task_module()
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            gate_path = runtime / "validation" / "skills" / "delivery-gates.json"
            gate_path.parent.mkdir(parents=True)
            gate_path.write_text(
                json.dumps(
                    {
                        "passed": False,
                        "checks": [{"name": "stale-check", "passed": False}],
                        "failures": [],
                    }
                ),
                encoding="utf-8",
            )
            (runtime / "input").mkdir()
            with patch.object(module, "runtime_dir", return_value=runtime):
                result = module.delivery_gate_fix_request("TEST-1", 2)
            self.assertIsNone(result)
            self.assertFalse((runtime / "input" / "fix-request-delivery-gates-attempt-002.md").exists())

    def test_all_prepared_task_plans_expose_slice_keys(self) -> None:
        tasks_root = AI_ROOT / "tasks"
        for task_dir in tasks_root.iterdir():
            plan_path = task_dir / "execution-plan.json"
            task_path = task_dir / "task.yaml"
            if not plan_path.exists() or not task_path.exists():
                continue
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            keys = [f"slice:{item['id']}" for item in plan.get("slices", [])]
            self.assertEqual(len(keys), len(set(keys)), task_dir.name)
            self.assertTrue(all(key != "slice:" for key in keys), task_dir.name)


if __name__ == "__main__":
    unittest.main()
