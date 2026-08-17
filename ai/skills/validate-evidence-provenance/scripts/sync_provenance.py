#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_manifest(manifest_path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    for field in ("task_id", "implementation_cycle", "change_cycle", "generated_at", "command"):
        if data.get(field) in (None, ""):
            errors.append(f"missing {field}")
    for item in data.get("preconditions", []):
        if item.get("passed") is not True:
            errors.append(f"failed precondition: {item.get('name', '<unnamed>')}")
    for group in ("inputs", "artifacts"):
        items = data.get(group, [])
        if not items:
            errors.append(f"no {group} recorded")
        for item in items:
            relative = item.get("path", "")
            target = (manifest_path.parent / relative).resolve()
            if not target.is_file():
                errors.append(f"{group}: missing file {relative}")
            elif digest(target) != item.get("sha256"):
                errors.append(f"{group}: stale hash for {relative}")
    return errors


def rebase_paths(data: dict, source_dir: Path) -> dict:
    rebased = json.loads(json.dumps(data))
    for group in ("inputs", "artifacts"):
        for item in rebased.get(group, []):
            target = (source_dir / item["path"]).resolve()
            item["path"] = str(target)
    return rebased


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the durable task evidence manifest and publish it to runtime validation."
    )
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("runtime_validation_dir", type=Path)
    args = parser.parse_args()

    source = (args.task_dir / "evidence" / "provenance.json").resolve()
    destination = (args.runtime_validation_dir / "provenance.json").resolve()
    if not source.is_file():
        print(f"Provenance sync skipped: no durable manifest at {source}")
        return 0

    data = json.loads(source.read_text(encoding="utf-8"))
    errors = validate_manifest(source, data)
    if errors:
        print("Provenance sync FAILED; durable manifest is not current")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    # Absolute paths remain valid from either location and avoid fragile, repository-specific
    # assumptions about the relative depth between durable task evidence and runtime state.
    published = rebase_paths(data, source.parent)
    atomic_write(destination, published)
    print(
        f"Provenance sync PASSED: published {len(data['inputs'])} inputs and "
        f"{len(data['artifacts'])} artifacts to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
