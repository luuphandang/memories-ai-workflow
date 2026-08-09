 #!/usr/bin/env python3
"""Reject legacy DOM patterns and runtime references to prototype sources."""
from __future__ import annotations

from pathlib import Path
import re
import sys

RULES = {
    "prototype runtime path": re.compile(r"(?:\.\./)*prototype/"),
    "manual DOM query": re.compile(r"document\.(?:querySelector|getElementById|getElementsByClassName)\s*\("),
    "innerHTML mutation": re.compile(r"\.innerHTML\s*="),
    "inline HTML handler": re.compile(r"\bon(?:click|change|input|submit)="),
}
SKIP = {"node_modules", ".next", "dist", "build", "coverage"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_prototype_migration.py <frontend-worktree>")
        return 2
    root = Path(sys.argv[1])
    failures: list[str] = []
    for path in root.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".css", ".html"} or SKIP.intersection(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in RULES.items():
            if pattern.search(text):
                failures.append(f"{name}: {path.relative_to(root)}")
    if failures:
        print("Prototype migration FAILED")
        print("\n".join(f"- {item}" for item in sorted(set(failures))))
        return 1
    print("Prototype migration PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
