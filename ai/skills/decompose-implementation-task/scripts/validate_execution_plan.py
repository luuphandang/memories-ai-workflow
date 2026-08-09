#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate execution-plan.json")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()
    schema = args.schema or Path(__file__).resolve().parents[3] / "schemas" / "execution-plan.schema.json"
    data = json.loads(args.plan.read_text(encoding="utf-8"))
    jsonschema.validate(data, json.loads(schema.read_text(encoding="utf-8")))
    ids = [item["id"] for item in data["slices"]]
    if len(ids) != len(set(ids)):
        raise SystemExit("execution plan contains duplicate slice ids")
    known = set(ids)
    for item in data["slices"]:
        unknown = sorted(set(item["depends_on"]) - known)
        if unknown:
            raise SystemExit(f"slice {item['id']} has unknown dependencies: {', '.join(unknown)}")
        if item["id"] in item["depends_on"]:
            raise SystemExit(f"slice {item['id']} depends on itself")
    print(f"Execution plan PASSED: {len(ids)} slices")


if __name__ == "__main__":
    main()
