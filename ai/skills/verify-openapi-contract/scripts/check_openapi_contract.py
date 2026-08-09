#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HTTP_STATUS = {
    "OK": 200,
    "CREATED": 201,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "UNPROCESSABLE_ENTITY": 422,
    "TOO_MANY_REQUESTS": 429,
    "INTERNAL_SERVER_ERROR": 500,
}


def response_statuses(decorator_block: str) -> set[int]:
    statuses = {int(value) for value in re.findall(r"status\s*:\s*(\d{3})", decorator_block)}
    for name in re.findall(r"status\s*:\s*HttpStatus\.([A-Z_]+)", decorator_block):
        if name in HTTP_STATUS:
            statuses.add(HTTP_STATUS[name])
    return statuses


def handler_decorators(source: str, handler: str) -> str | None:
    match = re.search(rf"\b(?:async\s+)?{re.escape(handler)}\s*\(", source)
    if not match:
        return None
    prefix = source[: match.start()]
    boundary = max(prefix.rfind("\n  }"), prefix.rfind("\n}"))
    return prefix[boundary + 1 :]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check required Swagger responses for declared API operations")
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve()
    manifest_path = root / "openapi-contracts.json"
    if not manifest_path.is_file():
        raise SystemExit(f"OpenAPI contract check FAILED: missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for operation in manifest.get("operations", []):
        label = f"{str(operation.get('method', '')).upper()} {operation.get('path', '')}"
        source_path = root / operation["source"]
        test_path = root / operation["contract_test"]
        if not source_path.is_file():
            failures.append(f"{label}: missing controller source {operation['source']}")
            continue
        block = handler_decorators(source_path.read_text(encoding="utf-8"), operation["handler"])
        if block is None:
            failures.append(f"{label}: missing handler {operation['handler']}")
            continue
        documented = response_statuses(block)
        missing = sorted(set(operation["required_statuses"]) - documented)
        if missing:
            failures.append(f"{label}: missing explicit Swagger responses {missing}")
        if not test_path.is_file():
            failures.append(f"{label}: missing generated-document contract test {operation['contract_test']}")
    if failures:
        raise SystemExit("OpenAPI contract check FAILED:\n- " + "\n- ".join(failures))
    print(f"OpenAPI contract check PASSED: {len(manifest.get('operations', []))} operations")


if __name__ == "__main__":
    main()
