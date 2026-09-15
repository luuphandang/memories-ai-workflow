#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #3: check_prototype_migration.py must use AST
(ai/tools/source-analysis, ts-morph) so a `prototype/` mention in a comment is never confused
with a real import, and a JSX `onClick` handler is never confused with the raw HTML
`onclick=` attribute the old regex flagged (the pattern targeted lowercase HTML attribute
casing, which JSX's camelCase `onClick`/`onChange` never collides with -- but a plain
substring/regex scan can't tell the difference between an attribute name and prose).
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AI_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = AI_ROOT / "skills" / "migrate-prototype-nextjs-page" / "scripts" / "check_prototype_migration.py"
CLI_ENTRY = AI_ROOT / "tools" / "source-analysis" / "dist" / "cli.js"


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


@unittest.skipUnless(CLI_ENTRY.is_file(), "ai/tools/source-analysis not built (npm install && npm run build)")
class PrototypeMigrationAstTest(unittest.TestCase):
    def test_traceability_comment_is_not_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "page.tsx").write_text(
                "// Migrated from prototype/home.html; keep parity with the design reference.\n"
                "export function Page() {\n"
                "  return <main>Hello</main>;\n"
                "}\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_real_prototype_import_is_a_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "page.tsx").write_text(
                "import { legacyHelper } from '../prototype/utils';\n"
                "export function Page() {\n"
                "  return <main>{legacyHelper()}</main>;\n"
                "}\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("prototype-import", result.stdout)

    def test_jsx_camel_case_onclick_is_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "button.tsx").write_text(
                "export function Button() {\n"
                "  return <button onClick={() => console.log('clicked')}>Go</button>;\n"
                "}\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_jsx_lowercase_onclick_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "button.tsx").write_text(
                "export function Button() {\n"
                "  return <button onclick=\"doThing()\">Go</button>;\n"
                "}\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("inline-html-handler", result.stdout)

    def test_manual_dom_query_and_innerhtml_are_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "legacy.ts") .write_text(
                "export function mount() {\n"
                "  const el = document.getElementById('root');\n"
                "  el.innerHTML = '<b>bad</b>';\n"
                "}\n",
                encoding="utf-8",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("manual-dom-query", result.stdout)
            self.assertIn("innerhtml-mutation", result.stdout)


if __name__ == "__main__":
    unittest.main()
