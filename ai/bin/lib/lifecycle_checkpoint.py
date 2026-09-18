"""Persist and enforce plan/context/dependency/source freshness between lifecycle phases."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_common import (
    dirty_worktree_hash, read_json, read_yaml, runtime_dir, safe_workspace_path,
    sha256_file, task_dir, write_json,
)
from .impact import compare_checkpoint, make_checkpoint
from .integration import dependency_snapshot


def current_checkpoint(task_id: str, phase: str) -> dict[str, Any]:
    td = task_dir(task_id)
    task = read_yaml(td / "task.yaml")
    plan_path = td / "execution-plan.json"
    plan = read_json(plan_path) if plan_path.exists() else {"plan_version": 1}
    context_path = td / "context.lock.json"
    context_version = sha256_file(context_path) if context_path.exists() else "missing"
    dependencies = dependency_snapshot(task_id)
    sources = {
        item["repo"]: dirty_worktree_hash(safe_workspace_path(item["path"]))
        for item in task.get("worktrees", []) if safe_workspace_path(item["path"]).exists()
    }
    return make_checkpoint(
        phase=phase, plan_version=int(plan.get("plan_version", 1)),
        context_version=context_version, dependencies=dependencies,
        source_snapshots=sources,
    )


def checkpoint_path(task_id: str) -> Path:
    return runtime_dir(task_id) / "checkpoints" / "latest.json"


def write_checkpoint(task_id: str, phase: str) -> dict[str, Any]:
    checkpoint = current_checkpoint(task_id, phase)
    write_json(checkpoint_path(task_id), checkpoint)
    return checkpoint


def verify_checkpoint(task_id: str, expected_phases: set[str]) -> dict[str, Any]:
    path = checkpoint_path(task_id)
    if not path.exists():
        raise SystemExit(
            f"Lifecycle checkpoint missing for {task_id}; rerun implementation before continuing"
        )
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if recorded.get("phase") not in expected_phases:
        raise SystemExit(
            f"Lifecycle checkpoint phase {recorded.get('phase')} is not one of {sorted(expected_phases)}"
        )
    current = current_checkpoint(task_id, recorded["phase"])
    comparison = compare_checkpoint(recorded, current)
    if not comparison["fresh"]:
        raise SystemExit(
            "Lifecycle checkpoint is stale: " + ", ".join(comparison["reasons"])
        )
    return comparison
