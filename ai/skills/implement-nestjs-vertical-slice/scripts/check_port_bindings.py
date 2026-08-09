#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


TOKEN_RE = re.compile(r"export\s+const\s+([A-Z][A-Z0-9_]+)\s*=\s*Symbol\(")
INJECT_RE = re.compile(r"@Inject\(\s*([A-Z][A-Z0-9_]+)\s*\)")


def source_files(root: Path) -> list[Path]:
    return [
        path for path in root.rglob("*.ts")
        if not any(part in {"node_modules", "dist", "build", "coverage"} for part in path.parts)
        and not path.name.endswith((".spec.ts", ".e2e-spec.ts"))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Find injected Symbol tokens without Nest provider bindings")
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    files = source_files(args.worktree.resolve())
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}
    declared = {token for text in texts.values() for token in TOKEN_RE.findall(text)}
    injected = {token for text in texts.values() for token in INJECT_RE.findall(text)}
    missing: list[str] = []
    for token in sorted(declared & injected):
        binding = re.compile(rf"provide\s*:\s*{re.escape(token)}\b")
        if not any(binding.search(text) for text in texts.values()):
            locations = [str(path.relative_to(args.worktree)) for path, text in texts.items() if re.search(rf"@Inject\(\s*{re.escape(token)}\s*\)", text)]
            missing.append(f"{token}: injected in {', '.join(locations)} but no provider binding was found")
    if missing:
        raise SystemExit("Missing Nest provider bindings:\n- " + "\n- ".join(missing))
    print(f"Port binding check PASSED: {len(declared & injected)} injected Symbol tokens")


if __name__ == "__main__":
    main()
