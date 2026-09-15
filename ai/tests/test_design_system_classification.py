#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #2/#3: check_design_system_usage.py must
distinguish a raw color literal's AST context (styling vs. token-definition vs. typed
business/mock data) via ai/tools/source-analysis, instead of counting every repeated hex
literal in the repo the same way regardless of where it appears -- the concrete case that
motivated this: apps/frontend/apps/public-web/lib/mock/swatches.ts repeats the same hex
values across a typed product-swatch catalog (business data), which the old regex-only
checker flagged as a raw-color-repetition violation.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AI_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = AI_ROOT / "skills" / "establish-frontend-design-system" / "scripts" / "check_design_system_usage.py"
CLI_ENTRY = AI_ROOT / "tools" / "source-analysis" / "dist" / "cli.js"


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


@unittest.skipUnless(CLI_ENTRY.is_file(), "ai/tools/source-analysis not built (npm install && npm run build)")
class DesignSystemClassificationTest(unittest.TestCase):
    def test_repeated_hex_in_mock_catalog_is_not_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_dir = root / "apps" / "public-web" / "lib" / "mock"
            mock_dir.mkdir(parents=True)
            (mock_dir / "swatches.ts").write_text(
                "export const SWATCH = {\n"
                "  ivory: '#F7F1E7',\n"
                "  cream: '#EFE2CF',\n"
                "  rose: '#C98786',\n"
                "  burgundy: '#743F45',\n"
                "} as const;\n",
                encoding="utf-8",
            )
            # Same value repeated 4 times across the catalog -- would trip the old regex rule.
            (mock_dir / "card-templates.ts").write_text(
                "import { SWATCH } from './swatches';\n"
                "export const TEMPLATES = [\n"
                "  { id: 1, accent: '#EFE2CF' },\n"
                "  { id: 2, accent: '#EFE2CF' },\n"
                "  { id: 3, accent: '#EFE2CF' },\n"
                "  { id: 4, accent: '#EFE2CF' },\n"
                "];\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("PASSED", result.stdout)

    def test_repeated_hex_in_jsx_inline_style_is_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_dir = root / "apps" / "public-web" / "components"
            app_dir.mkdir(parents=True)
            for index in range(4):
                (app_dir / f"widget-{index}.tsx").write_text(
                    "export function Widget() {\n"
                    "  return <div style={{ backgroundColor: '#743F45' }} />;\n"
                    "}\n",
                    encoding="utf-8",
                )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("raw color repeated", result.stdout)

    def test_repeated_hex_in_design_system_token_file_is_not_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tokens_dir = root / "packages" / "design-system" / "src"
            tokens_dir.mkdir(parents=True)
            declarations = "\n".join(f"  --brand-{i}: #743F45;" for i in range(4))
            (tokens_dir / "tokens.css").write_text(f":root {{\n{declarations}\n}}\n", encoding="utf-8")
            result = run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_page_local_root_block_is_still_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page_dir = root / "apps" / "public-web" / "app" / "some-route"
            page_dir.mkdir(parents=True)
            (page_dir / "page.css").write_text(":root { --local: 0 0% 0%; }\n", encoding="utf-8")
            result = run_checker(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("page-local :root token block", result.stdout)


if __name__ == "__main__":
    unittest.main()
