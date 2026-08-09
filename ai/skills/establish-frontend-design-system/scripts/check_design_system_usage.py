#!/usr/bin/env python3
"""Report repeated raw visual values and page-local root token blocks."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
ROOT = re.compile(r":root\s*\{")
SKIP = {"node_modules", ".next", "dist", "build", "coverage"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_design_system_usage.py <frontend-worktree>")
        return 2
    root = Path(sys.argv[1])
    files = [p for p in root.rglob("*") if p.suffix in {".css", ".ts", ".tsx"} and not SKIP.intersection(p.parts)]
    failures: list[str] = []
    colors: Counter[str] = Counter()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(root)
        colors.update(value.lower() for value in HEX.findall(text))
        if "apps/" in rel.as_posix() and path.name != "globals.css" and ROOT.search(text):
            failures.append(f"page-local :root token block: {rel}")
    repeated = sorted((value, count) for value, count in colors.items() if count >= 4)
    if repeated:
        failures.append("raw colors repeated >=4 times: " + ", ".join(f"{v} ({n})" for v, n in repeated))
    if failures:
        print("Design-system usage FAILED")
        print("\n".join(f"- {item}" for item in failures))
        return 1
    print("Design-system usage PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
