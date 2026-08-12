#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_provenance.py <manifest.json>")
        return 2
    manifest_path = Path(sys.argv[1]).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for field in ("task_id", "implementation_cycle", "change_cycle", "generated_at", "command"):
        if data.get(field) in (None, ""):
            errors.append(f"missing {field}")
    preconditions = data.get("preconditions", [])
    if not preconditions:
        errors.append("no runtime/data preconditions recorded")
    for item in preconditions:
        if item.get("passed") is not True:
            errors.append(f"failed precondition: {item.get('name', '<unnamed>')}")
    for group in ("inputs", "artifacts"):
        items = data.get(group, [])
        if not items:
            errors.append(f"no {group} recorded")
        for item in items:
            relative = item.get("path", "")
            path = manifest_path.parent / relative
            if not path.is_file():
                errors.append(f"{group}: missing file {relative}")
                continue
            actual = digest(path)
            if actual != item.get("sha256"):
                errors.append(f"{group}: stale hash for {relative}")
    if errors:
        print("Evidence provenance FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Evidence provenance PASSED: {len(data['inputs'])} inputs, {len(data['artifacts'])} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
