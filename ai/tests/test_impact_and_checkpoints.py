from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ai.bin.lib.coordination import CoordinationStore
from ai.bin.lib.impact import LEVEL_0, LEVEL_1, LEVEL_3, compare_checkpoint, make_checkpoint
from ai.bin.lib.registries import RegistryService


class ImpactAndCheckpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.registry = RegistryService(CoordinationStore(Path(self.temp.name)))
        implementation = {"repository": "backend", "file": "user.ts", "symbol": "createUser"}
        self.registry.propose_and_claim("user.create", "TASK-A", implementation, actor="agent-a")
        self.registry.transition_capability("user.create", "BUILDING", actor="agent-a", task_id="TASK-A")
        self.dependency = self.registry.register_dependency("TASK-B", "user.create", actor="agent-b")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_breaking_contract_marks_consumer_dependency_stale(self) -> None:
        first = self.registry.change_contract(
            "user.create", {"kind": "typescript", "signature": "createUser(dto)"},
            actor="agent-a", task_id="TASK-A",
        )
        second = self.registry.change_contract(
            "user.create", {"kind": "typescript", "signature": "createUser(command)"},
            actor="agent-a", task_id="TASK-A",
        )
        self.assertEqual(first["impact_level"], LEVEL_3)
        self.assertEqual(second["impact_level"], LEVEL_3)
        dependency = self.registry.snapshot()["dependencies"][self.dependency["id"]]
        self.assertEqual(dependency["status"], "STALE")
        self.assertEqual(second["affected_consumers"], ["TASK-B"])

    def test_implementation_only_change_does_not_pause_consumer(self) -> None:
        contract = {"kind": "typescript", "signature": "createUser(dto)"}
        self.registry.change_contract("user.create", contract, actor="agent-a", task_id="TASK-A")
        result = self.registry.change_contract("user.create", contract, actor="agent-a", task_id="TASK-A")
        self.assertEqual(result["impact_level"], LEVEL_0)
        self.assertEqual(result["affected_consumers"], [])

    def test_additive_change_only_notifies(self) -> None:
        result = self.registry.change_contract(
            "user.create", {"kind": "schema", "fields": ["id", "nickname"], "compatibility_hint": "additive"},
            actor="agent-a", task_id="TASK-A",
        )
        self.assertEqual(result["impact_level"], LEVEL_1)
        self.assertEqual(result["affected_consumers"], [])

    def test_checkpoint_detects_relevant_dependency_and_target_changes(self) -> None:
        recorded = make_checkpoint(
            phase="HANDOFF_READY", plan_version=2, context_version="ctx-1",
            dependencies={"user.create": {"version": 1, "fingerprint": "a"}},
            source_snapshots={"backend": "source-a"}, fencing_tokens={"worktree": 3}, target_sha="target-a",
        )
        current = make_checkpoint(
            phase="HANDOFF_READY", plan_version=2, context_version="ctx-1",
            dependencies={"user.create": {"version": 2, "fingerprint": "b", "impact_level": LEVEL_3}},
            source_snapshots={"backend": "source-a"}, fencing_tokens={"worktree": 3}, target_sha="target-b",
        )
        comparison = compare_checkpoint(recorded, current)
        self.assertFalse(comparison["fresh"])
        self.assertEqual(comparison["impact_level"], LEVEL_3)
        self.assertIn("dependency_changed:user.create", comparison["reasons"])
        self.assertIn("target_sha_changed", comparison["reasons"])


if __name__ == "__main__":
    unittest.main()
