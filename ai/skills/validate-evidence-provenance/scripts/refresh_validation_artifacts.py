#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


MANAGED_NAMES = ("backend.json", "frontend.json", "summary.json")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def atomic_write(path: Path, data: dict) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebind provenance to validation JSON files produced by the just-completed validation run."
    )
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("runtime_validation_dir", type=Path)
    args = parser.parse_args()

    manifest = (args.task_dir / "evidence" / "provenance.json").resolve()
    runtime = args.runtime_validation_dir.resolve()
    if not manifest.is_file():
        print(f"Validation provenance refresh skipped: no durable manifest at {manifest}")
        return 0

    data = json.loads(manifest.read_text(encoding="utf-8"))
    existing_names = tuple(name for name in MANAGED_NAMES if (runtime / name).is_file())
    targets = {(runtime / name).resolve(): name for name in existing_names}
    refreshed: set[str] = set()
    for item in data.get("artifacts", []):
        target = (manifest.parent / item.get("path", "")).resolve()
        name = targets.get(target)
        if name is None:
            continue
        if not target.is_file():
            print(f"Validation provenance refresh FAILED: missing {target}")
            return 1
        item["sha256"] = digest(target)
        refreshed.add(name)

    for name in existing_names:
        if name in refreshed:
            continue
        target = (runtime / name).resolve()
        data.setdefault("artifacts", []).append(
            {
                "path": os.path.relpath(target, manifest.parent),
                "sha256": digest(target),
            }
        )
        refreshed.add(name)

    summary = json.loads((runtime / "summary.json").read_text(encoding="utf-8"))
    data["generated_at"] = summary["generated_at"]
    data["validation_artifact_refresh"] = {
        "command": f"./ai/bin/ai task validate-code {data.get('task_id')} --tier full",
        "generated_at": summary["generated_at"],
        "artifacts": list(existing_names),
    }
    atomic_write(manifest, data)
    print("Validation provenance refreshed: " + ", ".join(existing_names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
