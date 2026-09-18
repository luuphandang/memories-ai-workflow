from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import threading
import unittest

from ai.bin.lib.coordination import CoordinationConflict, CoordinationStore
from ai.bin.lib.registries import RegistryService


class RegistryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = RegistryService(CoordinationStore(self.root / "coordination"))
        self.implementation = {
            "repository": "backend",
            "file": "src/user.service.ts",
            "symbol": "UserService.createUser",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_producer_then_consumer(self) -> None:
        self.registry.propose_and_claim("user.create", "TASK-A", self.implementation, actor="agent-a")
        dependency = self.registry.register_dependency("TASK-B", "user.create", actor="agent-b")
        self.assertEqual(dependency["producer_task"], "TASK-A")
        self.assertIn("TASK-B", self.registry.capability("user.create")["consumers"])

    def test_concurrent_claim_has_one_producer(self) -> None:
        barrier = threading.Barrier(2)
        results: list[dict] = []

        def claim(task: str) -> None:
            barrier.wait()
            results.append(self.registry.propose_and_claim("notification.send", task, self.implementation, actor=task))

        threads = [threading.Thread(target=claim, args=(task,)) for task in ("TASK-A", "TASK-B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(1 for item in results if item["claimed"]), 1)
        capability = self.registry.capability("notification.send")
        self.assertIn(capability["producer_task"], {"TASK-A", "TASK-B"})

    def test_available_requires_current_source_symbol_and_evidence(self) -> None:
        source = self.root / "repo" / "src" / "user.service.ts"
        source.parent.mkdir(parents=True)
        source.write_text("class UserService { createUser() {} }\n")
        self.registry.propose_and_claim("user.create", "TASK-A", self.implementation, actor="agent-a")
        dependency = self.registry.register_dependency("TASK-B", "user.create", actor="agent-b")
        self.registry.transition_capability("user.create", "BUILDING", actor="agent-a", task_id="TASK-A")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        available = self.registry.mark_available(
            "user.create", actor="agent-a", task_id="TASK-A", workspace=self.root / "repo",
            source_sha256=digest, validation_evidence="validation/run-1.json",
        )
        self.assertEqual(available["status"], "AVAILABLE")
        self.assertEqual(
            self.registry.snapshot()["dependencies"][dependency["id"]]["status"], "RESOLVED"
        )
        with self.assertRaises(CoordinationConflict):
            self.registry.mark_available(
                "user.create", actor="agent-a", task_id="TASK-A", workspace=self.root / "repo",
                source_sha256="stale", validation_evidence="validation/run-1.json",
            )

    def test_missing_capability_dependency_waits(self) -> None:
        dependency = self.registry.register_dependency("TASK-B", "pricing.calculate", actor="agent-b")
        self.assertEqual(dependency["status"], "WAITING")
        self.assertIsNone(dependency["producer_task"])

    def test_observed_read_is_distinct_from_confirmed_dependency(self) -> None:
        observed = self.registry.register_resource_access(
            "TASK-B", "backend", "src/user.ts", "READ", "SHARED", actor="agent-b"
        )
        confirmed = self.registry.register_resource_access(
            "TASK-B", "backend", "src/user.ts", "READ", "SHARED", actor="agent-b", confirmed=True
        )
        self.assertEqual(observed["classification"], "observed")
        self.assertEqual(confirmed["classification"], "confirmed_dependency")

    def test_capability_claim_has_lease_and_can_be_recovered(self) -> None:
        claimed = self.registry.propose_and_claim(
            "user.create", "TASK-A", self.implementation, actor="agent-a"
        )["capability"]
        self.assertTrue(claimed["claim_lease_id"])
        self.registry.store.release_lease(
            claimed["claim_lease_id"], claimed["claim_fencing_token"]
        )
        self.registry.renew_task_claims("TASK-A")
        recovered = self.registry.capability("user.create")
        self.assertNotEqual(recovered["claim_lease_id"], claimed["claim_lease_id"])
        self.assertGreater(recovered["claim_fencing_token"], claimed["claim_fencing_token"])

    def test_resource_claim_is_exclusive_and_releasable(self) -> None:
        claimed = self.registry.claim_resource(
            "TASK-A", "backend", "src/user.ts", actor="agent-a"
        )
        with self.assertRaises(CoordinationConflict):
            self.registry.claim_resource(
                "TASK-B", "backend", "src/user.ts", actor="agent-b"
            )
        self.assertEqual(
            self.registry.active_resource_claims(exclude_task="TASK-B")[0]["task"], "TASK-A"
        )
        released = self.registry.release_resource(claimed["id"], "TASK-A", actor="agent-a")
        self.assertEqual(released["status"], "RELEASED")
        self.assertEqual(self.registry.active_resource_claims(), [])

    def test_completing_task_releases_resources_and_freezes_capability(self) -> None:
        self.registry.propose_and_claim(
            "user.create", "TASK-A", self.implementation, actor="agent-a"
        )
        self.registry.transition_capability(
            "user.create", "BUILDING", actor="agent-a", task_id="TASK-A"
        )
        # The completion behavior is independent of source verification, which is tested
        # by mark_available; publish the verified transition payload directly here.
        self.registry.transition_capability(
            "user.create", "AVAILABLE", actor="agent-a", task_id="TASK-A",
            details={
                "source_sha256": "verified-test-snapshot",
                "validation_evidence": "validation/test.json",
            },
        )
        self.registry.claim_resource(
            "TASK-A", "backend", "src/user.ts", actor="agent-a"
        )
        self.registry.complete_task_claims("TASK-A")
        self.assertEqual(self.registry.capability("user.create")["status"], "FROZEN")
        self.assertEqual(self.registry.active_resource_claims(), [])


if __name__ == "__main__":
    unittest.main()
