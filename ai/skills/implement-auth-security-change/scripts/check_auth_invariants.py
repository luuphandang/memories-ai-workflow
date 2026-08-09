#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check basic deterministic auth persistence invariants")
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve()
    texts = []
    migration_text = []
    for path in root.rglob("*.ts"):
        if any(part in {"node_modules", "dist", "build", "coverage"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        texts.append(text)
        if "migration" in path.name.lower() or "migrations" in path.parts:
            migration_text.append(text)
    source = "\n".join(texts)
    migrations = "\n".join(migration_text)
    findings = []
    if "existsByProviderAndIdentifier" in source:
        has_unique = bool(re.search(r"(?:unique|UNIQUE)[\s\S]{0,500}provider[\s\S]{0,500}identifier|provider[\s\S]{0,500}identifier[\s\S]{0,500}(?:unique|UNIQUE)", migrations, re.IGNORECASE))
        if not has_unique:
            findings.append("provider/identifier existence preflight exists but no matching database uniqueness evidence was found in migrations")
    if re.search(r"(?:console\.(?:log|debug|info)|logger\.(?:log|debug|info))\([^\n]*(?:password|refreshToken|accessToken)", source, re.IGNORECASE):
        findings.append("possible credential/token logging detected")
    if findings:
        raise SystemExit("Auth invariant check failed:\n- " + "\n- ".join(findings))
    print("Auth invariant check PASSED")


if __name__ == "__main__":
    main()
