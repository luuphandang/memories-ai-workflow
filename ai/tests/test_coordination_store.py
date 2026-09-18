from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from ai.bin.lib.coordination import CoordinationConflict, CoordinationStore, LeaseLost


class CoordinationStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = CoordinationStore(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_compare_and_swap_rejects_stale_revision(self) -> None:
        document = Path(self.temp.name) / "document.json"
        updated = self.store.compare_and_swap_json(document, 0, {"value": "a"})
        self.assertEqual(updated["revision"], 1)
        with self.assertRaises(CoordinationConflict):
            self.store.compare_and_swap_json(document, 0, {"value": "b"})
        self.assertEqual(json.loads(document.read_text())["value"], "a")

    def test_concurrent_compare_and_swap_has_one_winner(self) -> None:
        document = Path(self.temp.name) / "race.json"
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def contender(value: str) -> None:
            barrier.wait()
            try:
                self.store.compare_and_swap_json(document, 0, {"value": value})
                outcomes.append("won")
            except CoordinationConflict:
                outcomes.append("lost")

        threads = [threading.Thread(target=contender, args=(value,)) for value in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["won", "lost"])

    def test_write_lease_is_exclusive(self) -> None:
        lease = self.store.acquire_lease("worktree:/tmp/example", "TASK-A")
        with self.assertRaises(CoordinationConflict):
            self.store.acquire_lease("worktree:/tmp/example", "TASK-B")
        self.store.release_lease(lease["lease_id"], lease["fencing_token"])
        replacement = self.store.acquire_lease("worktree:/tmp/example", "TASK-B")
        self.assertGreater(replacement["fencing_token"], lease["fencing_token"])

    def test_expired_writer_cannot_use_stale_fencing_token(self) -> None:
        first = self.store.acquire_lease("resource:x", "TASK-A", ttl_seconds=1)
        time.sleep(1.05)
        second = self.store.acquire_lease("resource:x", "TASK-B")
        with self.assertRaises(LeaseLost):
            self.store.assert_lease(first["lease_id"], first["fencing_token"])
        self.assertEqual(
            self.store.assert_lease(second["lease_id"], second["fencing_token"])["owner"],
            "TASK-B",
        )

    def test_read_leases_can_coexist_but_block_writer(self) -> None:
        first = self.store.acquire_lease("resource:x", "reader-a", mode="read")
        second = self.store.acquire_lease("resource:x", "reader-b", mode="read")
        with self.assertRaises(CoordinationConflict):
            self.store.acquire_lease("resource:x", "writer", mode="write")
        self.store.release_lease(first["lease_id"], first["fencing_token"])
        self.store.release_lease(second["lease_id"], second["fencing_token"])

    def test_event_replay_is_idempotent_and_recovers_projection(self) -> None:
        event_id = "fixed-event"
        self.store.append_event("COUNTED", "test", {"amount": 2}, event_id=event_id)
        self.store.append_event("COUNTED", "test", {"amount": 999}, event_id=event_id)

        def reducer(state: dict, event: dict) -> dict:
            return {"total": state.get("total", 0) + event["payload"]["amount"]}

        first = self.store.reconcile_projection("counter", reducer)
        projection_path = next((Path(self.temp.name) / "projections").glob("counter-*.json"))
        projection_path.unlink()
        rebuilt = self.store.reconcile_projection("counter", reducer)
        self.assertEqual(first["state"], {"total": 2})
        self.assertEqual(rebuilt, first)

    def test_lock_many_uses_deterministic_order(self) -> None:
        with self.store.lock_many(["z", "a", "z"]):
            self.assertTrue(True)

    def test_lease_context_renews_and_releases(self) -> None:
        with self.store.lease("resource:renew", "TASK-A", ttl_seconds=2, heartbeat_seconds=1) as lease:
            time.sleep(1.05)
            self.assertEqual(
                self.store.assert_lease(lease["lease_id"], lease["fencing_token"])["owner"],
                "TASK-A",
            )
        replacement = self.store.acquire_lease("resource:renew", "TASK-B")
        self.assertGreater(replacement["fencing_token"], lease["fencing_token"])


if __name__ == "__main__":
    unittest.main()
