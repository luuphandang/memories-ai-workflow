from __future__ import annotations

import unittest

from ai.bin.lib.scheduler import SchedulingError, schedule


class SchedulerTest(unittest.TestCase):
    def slice(self, identifier: str, depends: list[str] | None = None, status: str = "pending") -> dict:
        return {
            "id": identifier, "depends_on": depends or [], "status": status,
            "external_dependencies": [], "resource_accesses": [],
        }

    def test_independent_slices_run_while_dependent_slice_waits(self) -> None:
        b1, b2, b3 = self.slice("b1"), self.slice("b2"), self.slice("b3")
        b4 = self.slice("b4", ["b1", "b2", "b3"])
        b4["external_dependencies"] = [{
            "dependency_id": "DEP-USER", "capability": "user.create", "blocking": True,
            "required_version": 1,
        }]
        b5 = self.slice("b5", ["b4"])
        result = schedule(
            {"slices": [b1, b2, b3, b4, b5]},
            {"dependencies": {"DEP-USER": {"status": "WAITING"}}},
        )
        self.assertEqual(result["runnable_slices"], ["b1", "b2", "b3"])
        self.assertEqual(result["dependency_state"], "partially_blocked")

    def test_ready_dependency_resumes_only_eligible_slice(self) -> None:
        b1, b2, b3 = self.slice("b1", status="completed"), self.slice("b2", status="completed"), self.slice("b3", status="completed")
        b4 = self.slice("b4", ["b1", "b2", "b3"])
        b4["external_dependencies"] = [{
            "dependency_id": "DEP-USER", "capability": "user.create", "blocking": True,
            "required_version": 1,
        }]
        b5 = self.slice("b5", ["b4"])
        result = schedule(
            {"slices": [b1, b2, b3, b4, b5]},
            {"dependencies": {"DEP-USER": {"status": "RESOLVED", "resolved_version": 1}}},
        )
        self.assertEqual(result["runnable_slices"], ["b4"])
        self.assertIn("b5", result["blocked_slices"])

    def test_write_conflict_blocks_slice(self) -> None:
        item = self.slice("write-user")
        item["resource_accesses"] = [{
            "repository": "backend", "path": "src/user.ts", "access": "WRITE", "visibility": "SHARED"
        }]
        result = schedule(
            {"slices": [item]}, {"dependencies": {}},
            active_resource_accesses=[{
                "repository": "backend", "path": "src/user.ts", "access": "WRITE", "visibility": "SHARED"
            }],
        )
        self.assertEqual(result["dependency_state"], "blocked")
        self.assertEqual(result["blocked_slices"]["write-user"][0]["reason"], "resource_conflict")

    def test_dependency_cycle_fails_instead_of_hanging(self) -> None:
        with self.assertRaises(SchedulingError):
            schedule({"slices": [self.slice("a", ["b"]), self.slice("b", ["a"])]}, {"dependencies": {}})


if __name__ == "__main__":
    unittest.main()
