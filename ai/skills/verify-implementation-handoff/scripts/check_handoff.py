#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "bin"))
from lib.ai_common import git_worktree_paths as changed_files  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_handoff.py <task-dir>")
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    handoff = json.loads((task_dir / "implementation.json").read_text(encoding="utf-8"))
    declared = {item["name"]: item.get("changed_files", []) for item in handoff.get("repositories", [])}
    errors: list[str] = []
    for worktree in task.get("worktrees", []):
        name = worktree["repo"]
        repo = (task_dir.parents[2] / worktree["path"]).resolve()
        actual = changed_files(repo)
        values = declared.get(name)
        if values is None:
            errors.append(f"{name}: repository is missing from implementation.json")
            continue
        duplicates = sorted({value for value in values if values.count(value) > 1})
        missing = sorted(actual - set(values))
        extra = sorted(set(values) - actual)
        if duplicates:
            errors.append(f"{name}: duplicate paths: {', '.join(duplicates)}")
        if missing:
            errors.append(f"{name}: missing paths: {', '.join(missing)}")
        if extra:
            errors.append(f"{name}: non-worktree paths or annotated strings: {', '.join(extra)}")
    unexpected = sorted(set(declared) - {item["repo"] for item in task.get("worktrees", [])})
    if unexpected:
        errors.append("unexpected repositories: " + ", ".join(unexpected))
    if errors:
        print("Implementation handoff FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Implementation handoff PASSED: {sum(len(v) for v in declared.values())} exact paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
