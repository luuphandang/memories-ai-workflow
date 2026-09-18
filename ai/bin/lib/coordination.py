"""Filesystem-backed coordination primitives for the local AI workflow.

Locks protect short atomic mutations. Leases express longer-lived ownership. Every lease
gets a monotonically increasing fencing token so a resumed/stale process cannot write after
another process has acquired the same resource.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import threading
from typing import Any, Callable, Iterator
from uuid import uuid4

from .ai_common import AI_ROOT, atomic_write, now_iso


class CoordinationConflict(RuntimeError):
    pass


class LeaseLost(CoordinationConflict):
    pass


def _safe_name(value: str) -> str:
    prefix = "".join(character if character.isalnum() or character in "-." else "-" for character in value)[:48]
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix or 'resource'}-{digest}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CoordinationStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (AI_ROOT / "runtime" / "coordination")
        self.locks = self.root / "locks"
        self.leases_path = self.root / "projections" / "leases.json"
        self.events_path = self.root / "events" / "events.jsonl"

    @contextlib.contextmanager
    def lock(self, resource: str, *, shared: bool = False, timeout: float = 30.0) -> Iterator[None]:
        path = self.locks / f"{_safe_name(resource)}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+")
        operation = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        deadline = time.monotonic() + timeout
        try:
            while True:
                try:
                    fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise CoordinationConflict(f"Timed out acquiring {'read' if shared else 'write'} lock: {resource}")
                    time.sleep(0.02)
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    @contextlib.contextmanager
    def lock_many(self, resources: list[str], *, timeout: float = 30.0) -> Iterator[None]:
        """Acquire exclusive locks in canonical order to prevent lock-order deadlocks."""
        with contextlib.ExitStack() as stack:
            for resource in sorted(set(resources)):
                stack.enter_context(self.lock(resource, timeout=timeout))
            yield

    def compare_and_swap_json(
        self, path: Path, expected_revision: int, value: dict[str, Any]
    ) -> dict[str, Any]:
        with self.lock(f"document:{path.resolve()}"):
            current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"revision": 0}
            actual = int(current.get("revision", 0))
            if actual != expected_revision:
                raise CoordinationConflict(
                    f"Stale document revision for {path}: expected {expected_revision}, found {actual}"
                )
            updated = {**value, "revision": actual + 1}
            atomic_write(path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            return updated

    def _read_leases(self) -> dict[str, Any]:
        if not self.leases_path.exists():
            return {"revision": 0, "fencing_counters": {}, "leases": {}}
        return json.loads(self.leases_path.read_text(encoding="utf-8"))

    def _write_leases(self, state: dict[str, Any]) -> None:
        state["revision"] = int(state.get("revision", 0)) + 1
        atomic_write(self.leases_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    @staticmethod
    def _expired(lease: dict[str, Any], now: datetime) -> bool:
        return datetime.fromisoformat(lease["expires_at"]) <= now

    def acquire_lease(
        self, resource: str, owner: str, *, ttl_seconds: int = 900, mode: str = "write"
    ) -> dict[str, Any]:
        if ttl_seconds <= 0 or mode not in {"read", "write"}:
            raise ValueError("Lease requires a positive TTL and read/write mode")
        with self.lock("lease-registry"):
            state = self._read_leases()
            now = _utc_now()
            active = {
                lease_id: lease for lease_id, lease in state["leases"].items()
                if not self._expired(lease, now)
            }
            conflicts = [
                lease for lease in active.values()
                if lease["resource"] == resource and (mode == "write" or lease["mode"] == "write")
            ]
            if conflicts:
                raise CoordinationConflict(
                    f"Resource already leased: {resource} by {conflicts[0]['owner']}"
                )
            same_resource = [lease for lease in active.values() if lease["resource"] == resource]
            current_token = int(state["fencing_counters"].get(resource, 0))
            token = current_token if same_resource else current_token + 1
            state["fencing_counters"][resource] = token
            lease_id = str(uuid4())
            lease = {
                "lease_id": lease_id,
                "resource": resource,
                "owner": owner,
                "mode": mode,
                "fencing_token": token,
                "acquired_at": now.isoformat(),
                "heartbeat_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            }
            active[lease_id] = lease
            state["leases"] = active
            self._write_leases(state)
            return lease

    @contextlib.contextmanager
    def lease(
        self, resource: str, owner: str, *, ttl_seconds: int = 900,
        heartbeat_seconds: int = 30, mode: str = "write",
    ) -> Iterator[dict[str, Any]]:
        """Hold a renewable lease and stop a long-running operation if ownership is lost."""
        lease = self.acquire_lease(resource, owner, ttl_seconds=ttl_seconds, mode=mode)
        stopped = threading.Event()
        failures: list[Exception] = []

        def renew() -> None:
            while not stopped.wait(heartbeat_seconds):
                try:
                    self.heartbeat(lease["lease_id"], lease["fencing_token"], ttl_seconds=ttl_seconds)
                except Exception as exc:  # surfaced when the protected operation exits
                    failures.append(exc)
                    stopped.set()

        thread = threading.Thread(target=renew, name=f"lease-{lease['lease_id']}", daemon=True)
        thread.start()
        operation_error = False
        try:
            yield lease
        except BaseException:
            operation_error = True
            raise
        finally:
            stopped.set()
            thread.join(timeout=max(1, heartbeat_seconds + 1))
            try:
                self.release_lease(lease["lease_id"], lease["fencing_token"])
            except LeaseLost:
                if not operation_error and not failures:
                    raise
            if failures and not operation_error:
                raise LeaseLost(f"Lease heartbeat failed for {resource}: {failures[0]}")

    @contextlib.contextmanager
    def maintain_lease(
        self, lease_id: str, fencing_token: int, *, ttl_seconds: int = 3600,
        heartbeat_seconds: int = 30,
    ) -> Iterator[dict[str, Any]]:
        """Heartbeat an existing ownership lease without releasing it on context exit."""
        lease = self.assert_lease(lease_id, fencing_token)
        stopped = threading.Event()
        failures: list[Exception] = []

        def renew() -> None:
            while not stopped.wait(heartbeat_seconds):
                try:
                    self.heartbeat(lease_id, fencing_token, ttl_seconds=ttl_seconds)
                except Exception as exc:
                    failures.append(exc)
                    stopped.set()

        thread = threading.Thread(target=renew, name=f"maintain-{lease_id}", daemon=True)
        thread.start()
        try:
            yield lease
        finally:
            stopped.set()
            thread.join(timeout=max(1, heartbeat_seconds + 1))
            if failures:
                raise LeaseLost(f"Lease heartbeat failed: {failures[0]}")

    def assert_lease(self, lease_id: str, fencing_token: int) -> dict[str, Any]:
        with self.lock("lease-registry", shared=True):
            state = self._read_leases()
            lease = state["leases"].get(lease_id)
            if not lease or self._expired(lease, _utc_now()):
                raise LeaseLost(f"Lease is missing or expired: {lease_id}")
            current_token = int(state["fencing_counters"].get(lease["resource"], 0))
            if lease["fencing_token"] != fencing_token or current_token != fencing_token:
                raise LeaseLost(f"Stale fencing token for lease: {lease_id}")
            return lease

    def active_leases(self, *, resource_prefix: str | None = None) -> list[dict[str, Any]]:
        with self.lock("lease-registry", shared=True):
            now = _utc_now()
            leases = [
                lease for lease in self._read_leases()["leases"].values()
                if not self._expired(lease, now)
            ]
            if resource_prefix is not None:
                leases = [lease for lease in leases if lease["resource"].startswith(resource_prefix)]
            return sorted(leases, key=lambda item: (item["resource"], item["owner"], item["lease_id"]))

    def heartbeat(self, lease_id: str, fencing_token: int, *, ttl_seconds: int = 900) -> dict[str, Any]:
        with self.lock("lease-registry"):
            state = self._read_leases()
            lease = state["leases"].get(lease_id)
            now = _utc_now()
            if not lease or self._expired(lease, now):
                raise LeaseLost(f"Lease is missing or expired: {lease_id}")
            current_token = int(state["fencing_counters"].get(lease["resource"], 0))
            if lease["fencing_token"] != fencing_token or current_token != fencing_token:
                raise LeaseLost(f"Stale fencing token for lease: {lease_id}")
            lease["heartbeat_at"] = now.isoformat()
            lease["expires_at"] = (now + timedelta(seconds=ttl_seconds)).isoformat()
            self._write_leases(state)
            return lease

    def release_lease(self, lease_id: str, fencing_token: int) -> None:
        with self.lock("lease-registry"):
            state = self._read_leases()
            lease = state["leases"].get(lease_id)
            if lease is None:
                return
            current_token = int(state["fencing_counters"].get(lease["resource"], 0))
            if lease["fencing_token"] != fencing_token or current_token != fencing_token:
                raise LeaseLost(f"Stale fencing token for lease: {lease_id}")
            del state["leases"][lease_id]
            self._write_leases(state)

    def append_event(
        self, event_type: str, actor: str, payload: dict[str, Any], *,
        task_id: str | None = None, entity_id: str | None = None,
        correlation_id: str | None = None, causation_id: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": event_id or str(uuid4()),
            "schema_version": 1,
            "type": event_type,
            "actor": actor,
            "task_id": task_id,
            "entity_id": entity_id,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "occurred_at": now_iso(),
            "payload": payload,
        }
        with self.lock("event-log"):
            existing = {item["event_id"] for item in self.read_events()}
            if event["event_id"] in existing:
                return next(item for item in self.read_events() if item["event_id"] == event["event_id"])
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return event

    def read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        return [json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines() if line]

    def reconcile_projection(
        self, name: str, reducer: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
        initial: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rebuild a deterministic materialized view from the durable event log."""
        with self.lock(f"projection:{name}"):
            state = dict(initial or {})
            applied: set[str] = set()
            last_applied: str | None = None
            for event in self.read_events():
                if event["event_id"] in applied:
                    continue
                state = reducer(state, event)
                applied.add(event["event_id"])
                last_applied = event["event_id"]
            projection = {
                "schema_version": 1,
                "last_applied_event": last_applied,
                "applied_event_ids": sorted(applied),
                "state": state,
            }
            path = self.root / "projections" / f"{_safe_name(name)}.json"
            atomic_write(path, json.dumps(projection, ensure_ascii=False, indent=2) + "\n")
            return projection
