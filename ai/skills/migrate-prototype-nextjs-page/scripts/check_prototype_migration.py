#!/usr/bin/env python3
"""Reject legacy DOM patterns and runtime references to prototype sources.

AST-scoped via ai/tools/source-analysis (ts-morph) instead of plain-text regex, so a
`prototype/` substring inside a comment or traceability note is never confused with an
actual import/require of prototype code, and a legitimate JSX `onClick` handler is never
confused with a raw HTML `onclick=` attribute surviving migration. See
ai/tools/source-analysis/src/prototype-migration.ts for the classifier.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ANALYSIS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "source-analysis"
CLI_ENTRY = ANALYSIS_ROOT / "dist" / "cli.js"

# prototype-comment findings (a `prototype/` mention that isn't an import specifier) are
# informational traceability, never a violation.
VIOLATION_RULES = {"prototype-import", "manual-dom-query", "innerhtml-mutation", "inline-html-handler"}


def run_analyzer(root: Path) -> dict:
    if not CLI_ENTRY.is_file():
        raise SystemExit(
            f"Missing {CLI_ENTRY}.\nNext: (cd {ANALYSIS_ROOT} && npm install && npm run build)"
        )
    result = subprocess.run(
        ["node", str(CLI_ENTRY), "prototype-migration", str(root)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"source-analysis prototype-migration analyzer failed:\n{result.stdout}")
    return json.loads(result.stdout)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_prototype_migration.py <frontend-worktree>")
        return 2
    root = Path(sys.argv[1])
    analysis = run_analyzer(root)
    failures = sorted(
        f"{item['rule']}: {item['file']}:{item['line']} ({item['snippet']})"
        for item in analysis["findings"]
        if item["rule"] in VIOLATION_RULES
    )
    if failures:
        print("Prototype migration FAILED")
        print("\n".join(f"- {item}" for item in failures))
        return 1
    print("Prototype migration PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
