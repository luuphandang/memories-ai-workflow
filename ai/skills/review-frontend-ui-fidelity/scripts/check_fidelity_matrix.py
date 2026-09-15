#!/usr/bin/env python3
"""Validate completeness and shape of a UI fidelity evidence matrix.

Structural shape (every entry has a well-formed route/viewport, and a `passed` entry
carries reference/actual paths, their sha256 and a comparison record) is enforced via
ai/schemas/fidelity-matrix.schema.json. This script additionally recomputes the sha256
of every `passed` entry's reference/actual files on disk against the manifest's declared
hash (so swapping the image after the manifest was written is caught), and checks
`comparison.score` against `comparison.threshold` (lower score = more similar, as with
every diff tool currently in this repo).

Two gates share this script:
  - default (schema/completeness): `failed`/`not_verified` entries are acceptable — this
    is what a reviewer runs while still building the matrix.
  - `--require-all-passed` (acceptance): every entry must additionally be `passed` — this
    is what finalize/report-time gating uses. Scaffolded or incomplete evidence can never
    pass this second gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("Missing jsonschema. Run: pip install -r ai/requirements.txt") from exc

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "fidelity-matrix.schema.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument(
        "--root", type=Path, default=None,
        help="base directory for relative reference/actual paths; defaults to the matrix file's directory",
    )
    parser.add_argument("--require-all-passed", action="store_true")
    args = parser.parse_args()

    root = args.root or args.matrix.parent
    errors: list[str] = []
    try:
        data = json.loads(args.matrix.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Fidelity matrix FAILED\n- cannot read/parse matrix: {exc}")
        return 1

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        print(f"Fidelity matrix FAILED\n- schema violation: {exc.message}")
        return 1

    entries = data.get("entries", [])
    for index, entry in enumerate(entries):
        if entry["status"] != "passed":
            if args.require_all_passed:
                errors.append(f"entry {index} ({entry['route']}) is {entry['status']!r}, not passed")
            continue
        for key, hash_key in (("reference", "reference_sha256"), ("actual", "actual_sha256")):
            path = (root / entry[key]).resolve()
            if not path.is_file():
                errors.append(f"entry {index} {key} file does not exist: {path}")
                continue
            actual_hash = sha256_file(path)
            if actual_hash != entry[hash_key]:
                errors.append(
                    f"entry {index} {key} sha256 mismatch: manifest declares {entry[hash_key]}, "
                    f"file on disk hashes to {actual_hash} (file changed since comparison was recorded)"
                )
        comparison = entry["comparison"]
        if comparison["score"] > comparison["threshold"]:
            errors.append(
                f"entry {index} comparison score {comparison['score']} exceeds threshold {comparison['threshold']}"
            )

    if errors:
        print("Fidelity matrix FAILED")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    mode = "acceptance (all-passed)" if args.require_all_passed else "schema/completeness"
    print(f"Fidelity matrix PASSED ({mode}): {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
