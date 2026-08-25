from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/review-vertical-slice-completeness/scripts/check_evidence_freshness.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("check_evidence_freshness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceFreshnessTest(unittest.TestCase):
    def test_missing_mandatory_current_state_facts_fail(self) -> None:
        module = load_module()
        implementation = {"acceptance_criteria": [{"evidence": "[unit-tests: 1 suites / 1 tests]"}]}
        tags = module.collect_tags(implementation)
        self.assertIn("implementation-attempt", module.MANDATORY_TAGS - tags.keys())
        self.assertIn("review-state", module.MANDATORY_TAGS - tags.keys())

    def test_attempt_and_handoff_ground_truth_come_from_state(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text(
                "implementation_attempt: 28\nimplementation_cycle: 1\nchange_cycle: 0\n"
                "status: changes_requested_by_codex\nuser_acceptance:\n  status: pending\n",
                encoding="utf-8",
            )
            self.assertEqual(module.ground_truth_implementation_attempt(task_dir, evidence_dir), "28")
            self.assertEqual(
                module.ground_truth_review_state(task_dir, evidence_dir),
                "changes_requested_by_codex",
            )
            self.assertEqual(module.ground_truth_acceptance_state(task_dir, evidence_dir), "pending")

    def test_stale_attempt_is_rejected_against_authoritative_state(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text("implementation_attempt: 28\n", encoding="utf-8")
            implementation = {"acceptance_criteria": [{"evidence": "[implementation-attempt: 27]"}]}
            with patch.dict(
                module.GROUND_TRUTH,
                {"implementation-attempt": module.ground_truth_implementation_attempt},
                clear=True,
            ), patch.object(module, "MANDATORY_TAGS", frozenset({"implementation-attempt"})):
                errors = module.freshness_errors(implementation, task_dir, evidence_dir)
            self.assertTrue(any("currently shows '28'" in error for error in errors), errors)

    def test_prepared_handoff_remains_fresh_during_review_transition(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text("status: reviewing\n", encoding="utf-8")
            implementation = {"acceptance_criteria": [{"evidence": "[review-state: prepared]"}]}
            with patch.dict(
                module.GROUND_TRUTH,
                {"review-state": module.ground_truth_review_state},
                clear=True,
            ), patch.object(module, "MANDATORY_TAGS", frozenset({"review-state"})):
                errors = module.freshness_errors(implementation, task_dir, evidence_dir)
            self.assertEqual(errors, [])

    def test_conflicting_current_attempt_inventory_in_audit_sections_is_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text("implementation_attempt: 28\n", encoding="utf-8")
            implementation = {
                "acceptance_criteria": [
                    {"evidence": "[unit-tests: 69 suites / 440 tests] [implementation-attempt: 28]"}
                ],
                "decisions": [{"decision": "Attempt 28 unit run: 69 suites / 436 tests passed."}],
                "validation_commands": [
                    {"command": "unit tests (attempt 28)", "result": "69 suites / 440 tests"}
                ],
            }
            with patch.dict(
                module.GROUND_TRUTH,
                {"implementation-attempt": module.ground_truth_implementation_attempt},
                clear=True,
            ), patch.object(module, "MANDATORY_TAGS", frozenset({"implementation-attempt"})):
                errors = module.freshness_errors(implementation, task_dir, evidence_dir)
            self.assertTrue(any("unit-tests" in error and "436" in error for error in errors), errors)

    def test_current_attempt_architecture_and_provenance_conflicts_are_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text("implementation_attempt: 28\n", encoding="utf-8")
            implementation = {
                "acceptance_criteria": [{"evidence": "[implementation-attempt: 28] [architecture: 474 modules / 1793 dependencies] [provenance-inventory: 56 inputs / 14 artifacts]"}],
                "validation_commands": [
                    {"command": "architecture attempt 28", "result": "473 modules / 1791 deps"},
                    {"command": "provenance attempt 28", "result": "56 inputs / 12 artifacts"},
                ],
            }
            with patch.dict(
                module.GROUND_TRUTH,
                {"implementation-attempt": module.ground_truth_implementation_attempt},
                clear=True,
            ), patch.object(module, "MANDATORY_TAGS", frozenset({"implementation-attempt"})):
                errors = module.freshness_errors(implementation, task_dir, evidence_dir)
            self.assertTrue(any("architecture" in error and "473" in error for error in errors), errors)
            self.assertTrue(any("provenance-inventory" in error and "12" in error for error in errors), errors)

    def test_current_attempt_applied_skill_provenance_conflict_is_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text("implementation_attempt: 28\n", encoding="utf-8")
            implementation = {
                "acceptance_criteria": [
                    {"evidence": "[implementation-attempt: 28] [provenance-inventory: 56 inputs / 14 artifacts]"}
                ],
                "applied_skills": [
                    {
                        "name": "validate-evidence-provenance",
                        "checks_completed": ["Attempt 28 sync PASSED at 56 inputs / 12 artifacts"],
                    }
                ],
            }
            with patch.dict(
                module.GROUND_TRUTH,
                {"implementation-attempt": module.ground_truth_implementation_attempt},
                clear=True,
            ), patch.object(module, "MANDATORY_TAGS", frozenset({"implementation-attempt"})):
                errors = module.freshness_errors(implementation, task_dir, evidence_dir)
            self.assertTrue(any("provenance-inventory" in error and "12" in error for error in errors), errors)

    def test_baseline_inventory_and_resolved_review_cycle_come_from_authoritative_files(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            evidence_dir = task_dir / "evidence"
            evidence_dir.mkdir()
            (task_dir / "state.yaml").write_text(
                "review_cycle: 19\nstatus: prepared\n", encoding="utf-8"
            )
            (evidence_dir / "characterization-baseline.md").write_text(
                "Current validated unit inventory: [unit-tests: 69 suites / 445 tests].\n",
                encoding="utf-8",
            )
            self.assertEqual(
                module.ground_truth_baseline_unit_tests(task_dir, evidence_dir),
                "69 suites / 445 tests",
            )
            self.assertEqual(
                module.ground_truth_resolved_review_cycles(task_dir, evidence_dir), "19"
            )


if __name__ == "__main__":
    unittest.main()
