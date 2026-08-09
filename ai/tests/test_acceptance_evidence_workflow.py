from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


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
                        ]
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
