#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import tempfile


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a manifest after its complete evidence-producing run")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--command", required=True)
    parser.add_argument("--precondition", action="append", default=[])
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for group in ("inputs", "artifacts"):
        for item in data.get(group, []):
            target = (manifest.parent / item["path"]).resolve()
            if not target.is_file():
                raise SystemExit(f"missing {group} file: {target}")
            item["sha256"] = digest(target)
    data["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    data["command"] = args.command
    data["preconditions"] = [{"name": item, "passed": True} for item in args.precondition]
    data.pop("validation_artifact_refresh", None)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=manifest.parent, delete=False) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(manifest)
    print(f"Finalized provenance: {len(data['inputs'])} inputs, {len(data['artifacts'])} artifacts")
    print(data["generated_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
