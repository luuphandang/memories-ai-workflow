from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


AI_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = AI_ROOT / "bin" / name
    loader = SourceFileLoader(f"test_{name.replace('-', '_')}", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AutonomousLoopRegressionTest(unittest.TestCase):
    def test_acceptance_requires_current_finalization_identity(self) -> None:
        module = load_script("accept-task")
        state = {
            "implementation_cycle": 2, "change_cycle": 1, "review_cycle": 4,
            "finalized_implementation_cycle": 2, "finalized_change_cycle": 1,
            "finalized_review_cycle": 4,
        }
        self.assertTrue(module.current_finalization_matches(state))
        state["review_cycle"] = 5
        self.assertFalse(module.current_finalization_matches(state))

    def test_validation_failure_queues_structured_checklist_and_state(self) -> None:
        module = load_script("run-task")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task_dir = root / "task"
            runtime = root / "runtime"
            (runtime / "validation").mkdir(parents=True)
            (runtime / "input").mkdir()
            task_dir.mkdir()
            (task_dir / "implementation-progress.json").write_text(json.dumps({"checklist": []}))
            (task_dir / "state.yaml").write_text("status: failed\n")
            (runtime / "validation" / "summary.json").write_text(json.dumps({
                "repositories": [{"repo": "backend", "commands": [{
                    "name": "test", "required": True, "status": "failed",
                    "command": "npm test", "output_tail": "failure",
                }]}]
            }))
            with patch.object(module, "runtime_dir", return_value=runtime), patch.object(module, "ensure_task", return_value=task_dir), patch.object(module, "ROOT", root):
                module.validation_fix_request("TEST-1", 2)
            progress = json.loads((task_dir / "implementation-progress.json").read_text())
            self.assertEqual(progress["checklist"][0]["status"], "pending")
            self.assertEqual(progress["checklist"][0]["source"], "validation")
            self.assertIn("changes_requested_by_validation", (task_dir / "state.yaml").read_text())

    def test_implementation_contract_failure_gets_autonomous_fix_request(self) -> None:
        module = load_script("run-task")
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            (runtime / "input").mkdir()
            with patch.object(module, "runtime_dir", return_value=runtime):
                path = module.implementation_contract_fix_request("TEST-2", 3, "checklist remains open")
            self.assertTrue(path.is_file())
            self.assertIn("checklist remains open", path.read_text())

    def test_partial_slice_handoff_resumes_at_validation(self) -> None:
        module = load_script("run-task")
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            task = {"scope": {"execution_plan_required": True}}
            state = {
                "status": "implementation_ready_for_validation",
                "implementation_cycle": 1, "change_cycle": 0,
                "last_completed_slice": "slice-a",
            }
            (task_dir / "implementation.json").write_text(json.dumps({
                "status": "implemented", "implementation_cycle": 1, "change_cycle": 0,
                "acceptance_criteria": [{"criterion": "slice:slice-a", "status": "passed", "evidence": "done"}],
            }))
            (task_dir / "implementation-progress.json").write_text(json.dumps({
                "completed_criteria": ["slice:slice-a"]
            }))
            (task_dir / "execution-plan.json").write_text(json.dumps({"slices": [
                {"id": "slice-a", "status": "pending"},
                {"id": "slice-b", "status": "pending"},
            ]}))
            self.assertTrue(module.can_resume_after_implementation(task, task_dir, state))

    def test_implementer_cannot_complete_unvalidated_plan_slice(self) -> None:
        module = load_script("run-claude")
        before = {"slices": [{"id": "a", "status": "pending"}, {"id": "b", "status": "pending"}]}
        current = {"slices": [{"id": "a", "status": "completed"}, {"id": "b", "status": "pending"}]}
        restored, identity_changed = module.restore_execution_plan_statuses(before, current)
        self.assertFalse(identity_changed)
        self.assertEqual([item["status"] for item in restored["slices"]], ["pending", "pending"])

    def test_implementer_cannot_advance_or_clear_checkpoint_slice(self) -> None:
        module = load_script("run-claude")
        with tempfile.TemporaryDirectory() as temp:
            checkpoint_path = Path(temp) / "implementation-progress.json"
            checkpoint_path.write_text(json.dumps({
                "current_slice": None,
                "completed_criteria": ["slice:first"],
                "current_step": "done",
            }))

            module.restore_orchestrator_checkpoint_slice(checkpoint_path, "first")

            checkpoint = json.loads(checkpoint_path.read_text())
            self.assertEqual(checkpoint["current_slice"], "first")
            self.assertEqual(checkpoint["completed_criteria"], ["slice:first"])

    def test_reconcile_repairs_interrupted_premature_completion(self) -> None:
        module = load_script("lib/ai_common.py")
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            (task_dir / "task.yaml").write_text("scope:\n  execution_plan_required: true\n")
            (task_dir / "execution-plan.json").write_text(json.dumps({"slices": [
                {"id": "audit-mapper", "status": "completed"},
                {"id": "next", "status": "pending"},
            ]}))
            (task_dir / "implementation-progress.json").write_text(json.dumps({
                "current_slice": "audit-mapper", "completed_criteria": []
            }))
            (task_dir / "implementation.json").write_text(json.dumps({"acceptance_criteria": []}))
            with patch.object(module, "ensure_task", return_value=task_dir):
                repaired = module.reconcile_execution_plan_evidence("TEST-3")
            self.assertEqual(repaired, ["audit-mapper"])
            plan = json.loads((task_dir / "execution-plan.json").read_text())
            self.assertEqual(plan["slices"][0]["status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
