#!/usr/bin/env python3
"""Unit coverage for request-fixes' machine-readable correction-scope sidecar
(build_correction_scope): mapping findings/criteria to slices, multi-slice
findings, unmapped-finding fallback, and sensitive-term escalation."""
from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import unittest


def load_request_fixes():
    path = Path(__file__).resolve().parents[1] / "bin" / "request-fixes"
    loader = importlib.machinery.SourceFileLoader("request_fixes_under_test", str(path))
    spec = importlib.util.spec_from_file_location("request_fixes_under_test", path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


SLICES = [
    {"id": "slice-a", "depends_on": [], "acceptance_criteria": ["AC1"], "deliverables": ["libs/foo/a.ts"]},
    {"id": "slice-b", "depends_on": ["slice-a"], "acceptance_criteria": ["AC2"], "deliverables": ["libs/bar/b.ts"]},
    {"id": "slice-c", "depends_on": [], "acceptance_criteria": ["AC3"], "deliverables": ["libs/baz/c.ts"]},
]


class CorrectionScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rf = load_request_fixes()

    def test_one_finding_maps_to_one_slice(self) -> None:
        finding = {"title": "Bug", "evidence": "broke", "expected_fix": "fix it", "file": "libs/foo/a.ts"}
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, [finding], [], [])
        self.assertEqual(scope["impacted_slices"], ["slice-a"])
        self.assertFalse(scope["full_plan_fallback_required"])
        self.assertIsNone(scope["full_plan_fallback_reason"])
        self.assertEqual(scope["risk_categories"], [])

    def test_findings_spanning_multiple_slices(self) -> None:
        findings = [
            {"title": "Bug A", "evidence": "e", "expected_fix": "f", "file": "libs/foo/a.ts"},
            {"title": "Bug C", "evidence": "e", "expected_fix": "f", "file": "libs/baz/c.ts"},
        ]
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, findings, [], [])
        self.assertEqual(scope["impacted_slices"], ["slice-a", "slice-c"])
        self.assertFalse(scope["full_plan_fallback_required"])

    def test_slice_prefixed_criterion_maps_directly(self) -> None:
        failed_criteria = [{"criterion": "slice:slice-b", "status": "failed"}]
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, [], failed_criteria, [])
        self.assertEqual(scope["impacted_slices"], ["slice-b"])
        self.assertFalse(scope["full_plan_fallback_required"])

    def test_unmapped_finding_requires_full_plan_fallback(self) -> None:
        finding = {"title": "Bug", "evidence": "e", "expected_fix": "f", "file": "some/unrelated/path.ts"}
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, [finding], [], [])
        self.assertEqual(scope["impacted_slices"], [])
        self.assertTrue(scope["full_plan_fallback_required"])
        self.assertIn("could not be mapped", scope["full_plan_fallback_reason"])

    def test_sensitive_finding_escalates_even_when_mapped(self) -> None:
        finding = {
            "title": "Auth bypass",
            "evidence": "the auth check can be skipped",
            "expected_fix": "fix it",
            "file": "libs/foo/a.ts",
        }
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, [finding], [], [])
        self.assertEqual(scope["impacted_slices"], ["slice-a"])  # still mapped...
        self.assertIn("auth", scope["risk_categories"])
        self.assertTrue(scope["full_plan_fallback_required"])  # ...but escalates anyway
        self.assertIn("sensitive correction", scope["full_plan_fallback_reason"])

    def test_missing_validation_forces_fallback(self) -> None:
        scope = self.rf.build_correction_scope("T-1", 1, True, SLICES, [], [], ["backend: e2e coverage missing"])
        self.assertTrue(scope["full_plan_fallback_required"])
        self.assertIn("not attributable to a specific slice", scope["full_plan_fallback_reason"])

    def test_no_execution_plan_skips_slice_scoping(self) -> None:
        finding = {"title": "Bug", "evidence": "e", "expected_fix": "f", "file": "libs/foo/a.ts"}
        scope = self.rf.build_correction_scope("T-1", 1, False, [], [finding], [], [])
        self.assertEqual(scope["impacted_slices"], [])
        self.assertFalse(scope["full_plan_fallback_required"])
        self.assertEqual(scope["execution_plan_required"], False)


if __name__ == "__main__":
    unittest.main()
