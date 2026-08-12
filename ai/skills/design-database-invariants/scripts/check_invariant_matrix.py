#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_invariant_matrix.py <matrix.json>")
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    entries = data.get("invariants", [])
    errors: list[str] = []
    if not entries:
        errors.append("matrix has no invariants")
    for index, entry in enumerate(entries):
        for field in ("invariant", "enforcement", "cases"):
            if not entry.get(field):
                errors.append(f"invariant {index} missing {field}")
        for case_index, case in enumerate(entry.get("cases", [])):
            for field in ("operation", "expected", "test"):
                if not case.get(field):
                    errors.append(f"invariant {index} case {case_index} missing {field}")
    if errors:
        print("Database invariant matrix FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Database invariant matrix PASSED: {len(entries)} invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
