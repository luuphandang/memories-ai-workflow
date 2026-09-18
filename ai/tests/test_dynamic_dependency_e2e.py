from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ai.bin.lib.coordination import CoordinationStore
from ai.bin.lib.discovery import DependencyDiscovery
from ai.bin.lib.plan_reconciler import PlanReconciler
from ai.bin.lib.registries import RegistryService
from ai.bin.lib.scheduler import schedule


class DynamicDependencyEndToEndTest(unittest.TestCase):
    def test_discover_wait_resume_breaking_change_reblocks_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            store = CoordinationStore(root / "coordination")
            registry = RegistryService(store)
            reconciler = PlanReconciler(store)
            source = root / "producer" / "src" / "user.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export class UserService { createUser(dto: object) {} }\n")
            implementation = {
                "repository": "backend", "file": "src/user.ts",
                "symbol": "UserService.createUser",
            }
            registry.propose_and_claim("user.create", "TASK-A", implementation, actor="agent-a")
            registry.transition_capability("user.create", "BUILDING", actor="agent-a", task_id="TASK-A")
            registry.change_contract(
                "user.create", {"kind": "typescript", "signature": "createUser(dto)"},
                actor="agent-a", task_id="TASK-A",
            )

            plan_path = root / "execution-plan.json"
            plan_path.write_text(json.dumps({
                "task_id": "TASK-B", "plan_version": 1, "applied_patches": [],
                "slices": [{
                    "id": "order", "depends_on": [], "status": "pending",
                    "external_dependencies": [], "resource_accesses": [],
                }],
            }))
            discovery = DependencyDiscovery(registry, reconciler)
            discovered = discovery.discover(
                task={"id": "TASK-B"}, plan_path=plan_path, slice_id="order",
                capability="user.create", actor="agent-b",
            )
            waiting = schedule(discovered["plan"], registry.snapshot())
            self.assertEqual(waiting["dependency_state"], "blocked")

            registry.mark_available(
                "user.create", actor="agent-a", task_id="TASK-A", workspace=root / "producer",
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                validation_evidence="validation/producer.json",
            )
            ready = schedule(json.loads(plan_path.read_text()), registry.snapshot())
            self.assertEqual(ready["runnable_slices"], ["order"])
            self.assertTrue(any(
                event["type"] == "TASK_DEPENDENCY_READY" and event["task_id"] == "TASK-B"
                for event in store.read_events()
            ))

            impact = registry.change_contract(
                "user.create", {"kind": "typescript", "signature": "createUser(command)"},
                actor="agent-a", task_id="TASK-A",
            )
            self.assertEqual(impact["impact_level"], "LEVEL_3")
            stale = schedule(json.loads(plan_path.read_text()), registry.snapshot())
            self.assertEqual(stale["dependency_state"], "blocked")


if __name__ == "__main__":
    unittest.main()
