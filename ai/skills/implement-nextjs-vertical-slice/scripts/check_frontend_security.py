#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


FORBIDDEN = re.compile(r"(?:localStorage|sessionStorage)\s*\.\s*(?:setItem|getItem)\s*\([^\n]*(?:token|credential|password)", re.IGNORECASE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check frontend source for persisted credentials")
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    findings = []
    for path in args.worktree.resolve().rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"} or any(part in {"node_modules", "dist", ".next", "coverage"} for part in path.parts):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if FORBIDDEN.search(line):
                findings.append(f"{path.relative_to(args.worktree)}:{number}")
    if findings:
        raise SystemExit("Browser credential persistence detected:\n- " + "\n- ".join(findings))
    print("Frontend credential-storage check PASSED")


if __name__ == "__main__":
    main()
