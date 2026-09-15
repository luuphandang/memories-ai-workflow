#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #2: the design-system baseline delta gate must
fail on a new violation or a growing occurrence count, stay quiet about unchanged baseline
debt, and refuse a baseline whose ruleset_version doesn't match the checker's current one.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AI_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = AI_ROOT / "skills" / "establish-frontend-design-system" / "scripts" / "check_design_system_usage.py"
CLI_ENTRY = AI_ROOT / "tools" / "source-analysis" / "dist" / "cli.js"
RULESET_VERSION = "1"


def run_checker(root: Path, baseline: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--baseline", str(baseline)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def write_repeated_style(app_dir: Path, count: int, value: str = "#743F45") -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    for existing in app_dir.glob("widget-*.tsx"):
        existing.unlink()
    for index in range(count):
        (app_dir / f"widget-{index}.tsx").write_text(
            f"export function Widget{index}() {{\n  return <div style={{{{ color: '{value}' }}}} />;\n}}\n",
            encoding="utf-8",
        )


def write_baseline(path: Path, violations: list[dict], ruleset_version: str = RULESET_VERSION) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "repo": "test-repo",
        "ruleset_version": ruleset_version,
        "implementation_hash": "test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "violations": violations,
    }), encoding="utf-8")


@unittest.skipUnless(CLI_ENTRY.is_file(), "ai/tools/source-analysis not built (npm install && npm run build)")
class DesignSystemBaselineTest(unittest.TestCase):
    def test_clean_baseline_then_new_root_block_fails_as_new_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline.json"
            write_baseline(baseline, violations=[])
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 0, result.stdout)

            page_dir = root / "apps" / "public-web" / "app" / "route"
            page_dir.mkdir(parents=True)
            (page_dir / "page.css").write_text(":root { --local: 0 0% 0%; }\n", encoding="utf-8")
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("new violation", result.stdout)

    def test_business_data_addition_does_not_affect_delta_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline.json"
            write_baseline(baseline, violations=[])
            mock_dir = root / "apps" / "public-web" / "lib" / "mock"
            mock_dir.mkdir(parents=True)
            (mock_dir / "swatches.ts").write_text(
                "export const SWATCH = { a: '#111111', b: '#111111', c: '#111111', d: '#111111' } as const;\n",
                encoding="utf-8",
            )
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_occurrence_increase_on_existing_fingerprint_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_dir = root / "apps" / "public-web" / "components"
            write_repeated_style(app_dir, count=4)
            baseline = root / "baseline.json"
            write_baseline(baseline, violations=[
                {"fingerprint": "repeated-color:#743f45", "rule": "raw-color-repetition", "count": 4}
            ])
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 0, result.stdout)  # count unchanged: carried, not failed

            write_repeated_style(app_dir, count=6)
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("occurrence increased", result.stdout)

    def test_ruleset_version_mismatch_forces_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline.json"
            write_baseline(baseline, violations=[], ruleset_version="0")
            result = run_checker(root, baseline)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("regenerate", result.stdout)

    def test_missing_baseline_file_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_checker(root, root / "does-not-exist.json")
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("baseline file not found", result.stdout)

    def test_generate_baseline_round_trips_into_a_passing_delta_gate(self) -> None:
        generator = AI_ROOT / "skills" / "establish-frontend-design-system" / "scripts" / "generate_baseline.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_dir = root / "apps" / "public-web" / "components"
            write_repeated_style(app_dir, count=5)
            output = root / "baseline.json"
            result = subprocess.run(
                [sys.executable, str(generator), "test-repo", str(root), "--output", str(output)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            baseline = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(baseline["ruleset_version"], RULESET_VERSION)
            self.assertEqual(len(baseline["violations"]), 1)
            self.assertEqual(baseline["violations"][0]["count"], 5)

            # The freshly generated baseline should immediately pass its own delta gate.
            check_result = run_checker(root, output)
            self.assertEqual(check_result.returncode, 0, check_result.stdout)


if __name__ == "__main__":
    unittest.main()
