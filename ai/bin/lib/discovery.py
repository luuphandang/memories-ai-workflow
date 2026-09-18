"""Runtime dependency discovery orchestration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .ai_common import coordination_policy
from .plan_reconciler import PlanReconciler, dependency_patch
from .registries import RegistryService


class DependencyDiscovery:
    def __init__(
        self, registry: RegistryService, reconciler: PlanReconciler,
        producer_factory: Callable[[str, dict[str, Any]], str] | None = None,
    ) -> None:
        self.registry = registry
        self.reconciler = reconciler
        self.producer_factory = producer_factory

    def discover(
        self, *, task: dict[str, Any], plan_path: Path, slice_id: str,
        capability: str, actor: str, blocking: bool = True,
        required_version: int | None = None,
    ) -> dict[str, Any]:
        task_id = task["id"]
        self.registry.store.append_event(
            "DEPENDENCY_DISCOVERED", actor,
            {"capability": capability, "slice_id": slice_id, "blocking": blocking},
            task_id=task_id, entity_id=capability,
        )
        dependency = self.registry.register_dependency(
            task_id, capability, actor=actor, blocking=blocking, required_version=required_version,
        )
        plan = self.reconciler.recover(plan_path)
        patch = dependency_patch(task_id, slice_id, dependency, self.reconciler.version(plan))
        self.registry.store.append_event(
            "PLAN_PATCH_PROPOSED", actor, patch, task_id=task_id, entity_id=patch["patch_id"]
        )
        updated = self.reconciler.apply(plan_path, patch, actor=actor)
        producer_proposal = None
        if dependency.get("producer_task") is None:
            policy = coordination_policy(task)
            auto_create = policy["dynamic_producer"] == "auto_create_in_scope"
            created_task = self.producer_factory(capability, task) if auto_create and self.producer_factory else None
            if created_task:
                self.registry.propose_and_claim(
                    capability, created_task, {}, actor="orchestrator"
                )
                self.registry.store.append_event(
                    "DEPENDENCY_PRODUCER_REGISTERED", "orchestrator",
                    {"id": dependency["id"], "producer_task": created_task, "status": "WAITING"},
                    task_id=task_id, entity_id=dependency["id"],
                )
                dependency = self.registry.snapshot()["dependencies"][dependency["id"]]
            producer_proposal = {
                "capability": capability,
                "action": "created" if created_task else ("create_required" if auto_create else "needs_input"),
                "producer_task": created_task,
            }
            self.registry.store.append_event(
                "PRODUCER_PROPOSAL_CREATED", "orchestrator", producer_proposal,
                task_id=task_id, entity_id=capability,
            )
        return {"dependency": dependency, "plan": updated, "producer_proposal": producer_proposal}
