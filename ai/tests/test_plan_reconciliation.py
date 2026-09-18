from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ai.bin.lib.coordination import CoordinationConflict, CoordinationStore
from ai.bin.lib.discovery import DependencyDiscovery
from ai.bin.lib.plan_reconciler import PlanReconciler, dependency_patch
from ai.bin.lib.registries import RegistryService


class PlanReconciliationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = CoordinationStore(self.root / "coordination")
        self.reconciler = PlanReconciler(self.store)
        self.plan_path = self.root / "execution-plan.json"
        self.plan_path.write_text(json.dumps({
            "task_id": "TASK-B", "implementation_cycle": 1, "change_cycle": 0,
            "status": "ready", "plan_version": 1, "applied_patches": [],
            "slices": [{"id": "orders", "external_dependencies": []}],
        }))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_runtime_discovery_applies_versioned_patch(self) -> None:
        service = DependencyDiscovery(RegistryService(self.store), self.reconciler)
        result = service.discover(
            task={"id": "TASK-B"}, plan_path=self.plan_path, slice_id="orders",
            capability="user.create", actor="agent-b",
        )
        self.assertEqual(result["plan"]["plan_version"], 2)
        self.assertEqual(result["producer_proposal"]["action"], "needs_input")
        self.assertEqual(
            result["plan"]["slices"][0]["external_dependencies"][0]["capability"], "user.create"
        )
        self.assertEqual(len(list((self.root / "plan-history").glob("*.json"))), 1)

    def test_same_patch_is_idempotent(self) -> None:
        dependency = {"id": "DEP-1", "capability": "user.create", "blocking": True}
        patch = dependency_patch("TASK-B", "orders", dependency, 1, patch_id="PATCH-1")
        first = self.reconciler.apply(self.plan_path, patch, actor="agent-b")
        second = self.reconciler.apply(self.plan_path, patch, actor="agent-b")
        self.assertEqual(second, first)

    def test_missing_capability_can_create_producer_under_explicit_policy(self) -> None:
        created: list[str] = []

        def factory(capability: str, task: dict) -> str:
            created.append(capability)
            return "AUTO-0001"

        service = DependencyDiscovery(RegistryService(self.store), self.reconciler, factory)
        result = service.discover(
            task={"id": "TASK-B", "coordination": {"dynamic_producer": "auto_create_in_scope"}},
            plan_path=self.plan_path, slice_id="orders", capability="pricing.calculate", actor="agent-b",
        )
        self.assertEqual(created, ["pricing.calculate"])
        self.assertEqual(result["producer_proposal"]["action"], "created")
        self.assertEqual(result["producer_proposal"]["producer_task"], "AUTO-0001")

    def test_two_patches_from_same_base_cannot_silent_overwrite(self) -> None:
        first = dependency_patch(
            "TASK-B", "orders", {"id": "DEP-1", "capability": "user.create", "blocking": True},
            1, patch_id="PATCH-1",
        )
        second = dependency_patch(
            "TASK-B", "orders", {"id": "DEP-2", "capability": "pricing.calculate", "blocking": True},
            1, patch_id="PATCH-2",
        )
        self.reconciler.apply(self.plan_path, first, actor="agent-b")
        with self.assertRaises(CoordinationConflict):
            self.reconciler.apply(self.plan_path, second, actor="agent-b")
        plan = json.loads(self.plan_path.read_text())
        self.assertEqual(plan["applied_patches"], ["PATCH-1"])

    def test_recovery_applies_durable_proposal_after_interruption(self) -> None:
        patch = dependency_patch(
            "TASK-B", "orders", {"id": "DEP-1", "capability": "user.create", "blocking": True},
            1, patch_id="PATCH-RECOVER",
        )
        self.store.append_event(
            "PLAN_PATCH_PROPOSED", "agent-b", patch,
            task_id="TASK-B", entity_id=patch["patch_id"],
        )
        recovered = self.reconciler.recover(self.plan_path)
        self.assertEqual(recovered["plan_version"], 2)
        self.assertIn("PATCH-RECOVER", recovered["applied_patches"])


if __name__ == "__main__":
    unittest.main()
