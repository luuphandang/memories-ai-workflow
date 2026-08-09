#!/usr/bin/env python3
"""Validate completeness and shape of a UI fidelity evidence matrix."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

VIEWPORT = re.compile(r"^[1-9][0-9]{2,3}x[1-9][0-9]{2,3}$")
REQUIRED = {"route", "viewport", "state", "reference", "actual", "status"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_fidelity_matrix.py <matrix.json>")
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    entries = data.get("entries", []) if isinstance(data, dict) else []
    errors: list[str] = []
    if not entries:
        errors.append("matrix has no entries")
    for index, entry in enumerate(entries):
        missing = REQUIRED - set(entry)
        if missing:
            errors.append(f"entry {index} missing: {', '.join(sorted(missing))}")
            continue
        if not str(entry["route"]).startswith("/"):
            errors.append(f"entry {index} route must start with /")
        if not VIEWPORT.fullmatch(str(entry["viewport"])):
            errors.append(f"entry {index} viewport must be WIDTHxHEIGHT")
        if entry["status"] not in {"passed", "failed", "not_verified"}:
            errors.append(f"entry {index} has invalid status")
        if not entry["reference"] or not entry["actual"]:
            errors.append(f"entry {index} needs reference and actual evidence")
    if errors:
        print("Fidelity matrix FAILED")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print(f"Fidelity matrix PASSED: {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
