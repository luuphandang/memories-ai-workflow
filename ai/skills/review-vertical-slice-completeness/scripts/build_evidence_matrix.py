#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic acceptance-evidence coverage")
    parser.add_argument("execution_plan", type=Path)
    parser.add_argument("implementation", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = json.loads(args.execution_plan.read_text(encoding="utf-8"))
    implementation = json.loads(args.implementation.read_text(encoding="utf-8"))
    handoff = {item["criterion"]: item for item in implementation.get("acceptance_criteria", [])}
    planned_criteria = [
        criterion
        for slice_item in plan["slices"]
        for criterion in slice_item["acceptance_criteria"]
    ]
    explicit = sorted({int(match.group(1)) for item in planned_criteria if (match := re.fullmatch(r"AC(\d+)", item))})
    if explicit:
        expected = list(range(1, max(explicit) + 1))
        if explicit != expected or explicit[-1] != 22:
            raise SystemExit("execution plan must represent every explicit criterion AC1 through AC22")
    elif planned_criteria:
        raise SystemExit("execution plan uses generic umbrella criteria instead of explicit AC1 through AC22")
    rows = []
    missing = []
    for slice_item in plan["slices"]:
        slice_evidence = handoff.get(f"slice:{slice_item['id']}")
        for criterion in slice_item["acceptance_criteria"]:
            evidence = handoff.get(criterion) or slice_evidence
            row = {
                "criterion": criterion,
                "slice": slice_item["id"],
                "status": evidence.get("status") if evidence else "missing",
                "evidence": evidence.get("evidence", "") if evidence else "",
                "coverage": "criterion" if handoff.get(criterion) else ("slice" if slice_evidence else "missing"),
            }
            rows.append(row)
            if not evidence or not evidence.get("evidence") or evidence.get("status") != "passed":
                missing.append(criterion)
    output = {"passed": not missing, "rows": rows, "missing": missing}
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
