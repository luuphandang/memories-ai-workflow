#!/usr/bin/env python3
"""Check required Swagger responses for declared API operations.

Verifies directly against the generated OpenAPI document (`SwaggerModule.createDocument`'s
output, exported by `npm run export:openapi` -- see apps/backend/apps/api/src/export-openapi.ts)
instead of regex-parsing decorator source. Regex/substring scanning of a decorator block is
fragile to formatting (Prettier line-wrapping breaks a backward brace-boundary search) and can
never see what the framework actually assembled; the generated document is the same artifact
real clients see, so a required response missing from it fails regardless of how the source
happens to be formatted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

PATH_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def to_openapi_path(path: str) -> str:
    """NestJS `:id`-style route params -> OpenAPI `{id}`-style path template segments."""
    return PATH_PARAM_RE.sub(r"{\1}", path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=Path)
    parser.add_argument(
        "--document", type=Path, default=None,
        help="generated OpenAPI document (default: <worktree>/openapi.json, the default "
        "output of `npm run export:openapi`)",
    )
    args = parser.parse_args()
    root = args.worktree.resolve()
    document_path = args.document if args.document is not None else root / "openapi.json"
    manifest_path = root / "openapi-contracts.json"

    if not manifest_path.is_file():
        raise SystemExit(f"OpenAPI contract check FAILED: missing {manifest_path}")
    if not document_path.is_file():
        raise SystemExit(
            f"OpenAPI contract check FAILED: missing generated document {document_path}\n"
            "Next: run `npm run export:openapi` in the backend worktree (requires the same "
            "infrastructure apps/api needs to boot -- see docker/docker-compose.yml --profile infrastructure)."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document = json.loads(document_path.read_text(encoding="utf-8"))
    paths = document.get("paths", {})

    failures: list[str] = []
    for operation in manifest.get("operations", []):
        label = f"{str(operation.get('method', '')).upper()} {operation.get('path', '')}"
        source_path = root / operation["source"]
        test_path = root / operation["contract_test"]
        if not source_path.is_file():
            failures.append(f"{label}: manifest references missing controller source {operation['source']}")

        document_path_key = to_openapi_path(operation["path"])
        method = str(operation.get("method", "")).lower()
        path_item = paths.get(document_path_key)
        operation_item = path_item.get(method) if isinstance(path_item, dict) else None
        if operation_item is None:
            failures.append(
                f"{label}: not present in generated document at paths[{document_path_key!r}][{method!r}] "
                "(route not wired, or openapi.json is stale -- rerun npm run export:openapi)"
            )
        else:
            documented = {str(status) for status in operation_item.get("responses", {})}
            missing = sorted(status for status in operation["required_statuses"] if str(status) not in documented)
            if missing:
                failures.append(f"{label}: generated document is missing required responses {missing}")

        if not test_path.is_file():
            failures.append(f"{label}: missing generated-document contract test {operation['contract_test']}")

    if failures:
        raise SystemExit("OpenAPI contract check FAILED:\n- " + "\n- ".join(failures))
    print(f"OpenAPI contract check PASSED: {len(manifest.get('operations', []))} operations")


if __name__ == "__main__":
    main()
