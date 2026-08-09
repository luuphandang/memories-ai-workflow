#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


CLASS_RE = re.compile(r"export\s+class\s+(\w+)")


def files(root: Path, pattern: str) -> list[Path]:
    return [path for path in root.rglob(pattern) if not any(part in {"node_modules", "dist", "build", "coverage"} for part in path.parts)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Nest use-case/controller reachability from modules")
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve()
    module_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files(root, "*.module.ts"))
    findings = []
    candidates = [(path, "provider") for path in files(root, "*.use-case.ts")] + [(path, "controller") for path in files(root, "*.controller.ts")]
    for path, kind in candidates:
        text = path.read_text(encoding="utf-8", errors="replace")
        match = CLASS_RE.search(text)
        if not match:
            continue
        name = match.group(1)
        if not re.search(rf"\b{re.escape(name)}\b", module_text):
            findings.append(f"{kind} {name} ({path.relative_to(root)}) is not referenced by any Nest module")
    migration_files = files(root, "*migration*.ts") + [path for path in files(root, "*.ts") if "migrations" in path.parts]
    if migration_files:
        config_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files(root, "*.ts") if any(word in path.name.lower() for word in ("data-source", "database", "typeorm")))
        if "migration" not in config_text.lower():
            findings.append("migration files exist but no TypeORM migration registration was found in database/data-source configuration")
    if findings:
        raise SystemExit("Nest module wiring check failed:\n- " + "\n- ".join(findings))
    print(f"Nest module wiring check PASSED: {len(candidates)} use-case/controller classes")


if __name__ == "__main__":
    main()
