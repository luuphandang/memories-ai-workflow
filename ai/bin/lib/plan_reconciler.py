"""Versioned, optimistic plan patches owned by the orchestrator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ai_common import atomic_write, now_iso
from .coordination import CoordinationConflict, CoordinationStore


class PlanReconciler:
    def __init__(self, store: CoordinationStore) -> None:
        self.store = store

    @staticmethod
    def version(plan: dict[str, Any]) -> int:
        return int(plan.get("plan_version", 1))

    def apply(self, plan_path: Path, patch: dict[str, Any], *, actor: str) -> dict[str, Any]:
        with self.store.lock(f"execution-plan:{plan_path.resolve()}"):
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            patch_id = patch["patch_id"]
            if patch_id in plan.get("applied_patches", []):
                return plan
            current_version = self.version(plan)
            if int(patch["base_version"]) != current_version:
                self.store.append_event(
                    "PLAN_PATCH_REJECTED", actor,
                    {"patch_id": patch_id, "base_version": patch["base_version"], "current_version": current_version},
                    task_id=patch["task_id"], entity_id=patch_id,
                )
                raise CoordinationConflict(
                    f"Stale plan patch {patch_id}: base {patch['base_version']}, current {current_version}"
                )
            if patch["task_id"] != plan.get("task_id"):
                raise CoordinationConflict("Plan patch targets a different task")
            slices = {item["id"]: item for item in plan.get("slices", [])}
            for change in patch["changes"]:
                target = slices.get(change["slice_id"])
                if target is None:
                    raise CoordinationConflict(f"Unknown plan slice: {change['slice_id']}")
                if change["type"] == "ADD_DEPENDENCY":
                    dependency = change["dependency"]
                    existing = target.setdefault("external_dependencies", [])
                    if not any(item["dependency_id"] == dependency["dependency_id"] for item in existing):
                        existing.append(dependency)
                else:
                    raise CoordinationConflict(f"Unsupported plan change: {change['type']}")
            history_dir = plan_path.parent / "plan-history"
            history_dir.mkdir(parents=True, exist_ok=True)
            history = {
                "applied_at": now_iso(),
                "from_version": current_version,
                "to_version": current_version + 1,
                "patch": patch,
            }
            atomic_write(
                history_dir / f"v{current_version:04d}-to-v{current_version + 1:04d}__{patch_id}.json",
                json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            )
            plan["plan_version"] = current_version + 1
            plan.setdefault("applied_patches", []).append(patch_id)
            atomic_write(plan_path, json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
            self.store.append_event(
                "PLAN_PATCH_APPLIED", actor,
                {"patch_id": patch_id, "from_version": current_version, "to_version": current_version + 1},
                task_id=patch["task_id"], entity_id=patch_id,
            )
            return plan

    def recover(self, plan_path: Path) -> dict[str, Any]:
        """Finish interrupted proposed patches or repair a missing applied audit event."""
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        task_id = plan.get("task_id")
        events = self.store.read_events()
        applied_events = {
            event["payload"].get("patch_id") for event in events
            if event["type"] == "PLAN_PATCH_APPLIED"
        }
        proposals = [
            event["payload"] for event in events
            if event["type"] == "PLAN_PATCH_PROPOSED"
            and event.get("task_id") == task_id
        ]
        for patch in proposals:
            patch_id = patch["patch_id"]
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if patch_id in plan.get("applied_patches", []):
                if patch_id not in applied_events:
                    self.store.append_event(
                        "PLAN_PATCH_APPLIED", "recovery",
                        {
                            "patch_id": patch_id,
                            "from_version": int(patch["base_version"]),
                            "to_version": int(patch["base_version"]) + 1,
                            "recovered": True,
                        },
                        task_id=task_id, entity_id=patch_id,
                    )
                continue
            if int(patch["base_version"]) == self.version(plan):
                plan = self.apply(plan_path, patch, actor="recovery")
        return json.loads(plan_path.read_text(encoding="utf-8"))


def dependency_patch(
    task_id: str, slice_id: str, dependency: dict[str, Any], base_version: int,
    *, patch_id: str | None = None,
) -> dict[str, Any]:
    return {
        "patch_id": patch_id or f"PATCH-{uuid4()}",
        "task_id": task_id,
        "base_version": base_version,
        "source": {"task": task_id},
        "reason": "runtime_dependency_discovered",
        "changes": [{
            "type": "ADD_DEPENDENCY",
            "slice_id": slice_id,
            "dependency": {
                "dependency_id": dependency["id"],
                "capability": dependency["capability"],
                "required_version": dependency.get("required_version"),
                "blocking": dependency["blocking"],
            },
        }],
    }
