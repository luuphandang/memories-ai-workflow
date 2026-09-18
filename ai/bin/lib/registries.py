"""Event-sourced capability, dependency and resource-access registries."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ai_common import canonical_resource_id, validate_capability_name
from .coordination import CoordinationConflict, CoordinationStore
from .impact import LEVEL_0, LEVEL_1, classify_contract_change, contract_fingerprint


ACTIVE_CAPABILITY_STATES = {"PROPOSED", "CLAIMED", "BUILDING", "AVAILABLE", "FROZEN"}
CAPABILITY_TRANSITIONS = {
    None: {"PROPOSED"},
    "PROPOSED": {"CLAIMED", "DEPRECATED", "INVALID"},
    "CLAIMED": {"BUILDING", "DEPRECATED", "INVALID"},
    "BUILDING": {"AVAILABLE", "DEPRECATED", "INVALID"},
    "AVAILABLE": {"FROZEN", "BUILDING", "DEPRECATED", "INVALID"},
    "FROZEN": {"DEPRECATED"},
    "DEPRECATED": set(),
    "INVALID": {"BUILDING", "DEPRECATED"},
}


def registry_reducer(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    state = {
        "capabilities": dict(state.get("capabilities", {})),
        "dependencies": dict(state.get("dependencies", {})),
        "resource_accesses": dict(state.get("resource_accesses", {})),
    }
    payload = event["payload"]
    event_type = event["type"]
    if event_type.startswith("CAPABILITY_"):
        name = payload["name"]
        capability = dict(state["capabilities"].get(name, {"name": name, "consumers": []}))
        capability.update(payload)
        if "status" in payload:
            capability["status"] = payload["status"]
        capability["last_event_id"] = event["event_id"]
        state["capabilities"][name] = capability
    elif event_type == "CONSUMER_REGISTERED":
        name = payload["capability"]
        capability = dict(state["capabilities"].get(name, {"name": name, "consumers": []}))
        consumers = list(capability.get("consumers", []))
        if payload["task"] not in consumers:
            consumers.append(payload["task"])
        capability["consumers"] = sorted(consumers)
        capability["last_event_id"] = event["event_id"]
        state["capabilities"][name] = capability
    elif event_type.startswith("DEPENDENCY_") and "id" in payload:
        dependency = dict(state["dependencies"].get(payload["id"], {}))
        dependency.update(payload)
        dependency["last_event_id"] = event["event_id"]
        state["dependencies"][payload["id"]] = dependency
    elif event_type.startswith("RESOURCE_"):
        access = dict(payload)
        access["last_event_id"] = event["event_id"]
        state["resource_accesses"][payload["id"]] = access
    return state


class RegistryService:
    def __init__(self, store: CoordinationStore) -> None:
        self.store = store

    def snapshot(self) -> dict[str, Any]:
        return self.store.reconcile_projection(
            "coordination-registry", registry_reducer,
            {"capabilities": {}, "dependencies": {}, "resource_accesses": {}},
        )["state"]

    def capability(self, name: str) -> dict[str, Any] | None:
        return self.snapshot()["capabilities"].get(validate_capability_name(name))

    def propose_and_claim(
        self, name: str, producer_task: str, implementation: dict[str, Any], *,
        actor: str, lease: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        name = validate_capability_name(name)
        with self.store.lock(f"capability-claim:{name}"):
            current = self.capability(name)
            if current and current.get("status") in ACTIVE_CAPABILITY_STATES:
                if current.get("status") == "FROZEN" and current.get("producer_task") != producer_task:
                    self.register_consumer(name, producer_task, actor=actor)
                    return {"claimed": False, "capability": self.capability(name)}
                claim_alive = False
                if current.get("claim_lease_id") and current.get("claim_fencing_token"):
                    try:
                        self.store.assert_lease(current["claim_lease_id"], current["claim_fencing_token"])
                        claim_alive = True
                    except CoordinationConflict:
                        claim_alive = False
                if claim_alive and current.get("producer_task") != producer_task:
                    self.register_consumer(name, producer_task, actor=actor)
                    return {"claimed": False, "capability": self.capability(name)}
                if claim_alive:
                    return {"claimed": True, "capability": current}
            if lease is None:
                lease = self.store.acquire_lease(
                    f"capability:{name}", producer_task, ttl_seconds=3600, mode="write"
                )
            common = {
                "name": name,
                "type": "code",
                "producer_task": producer_task,
                "implementation": implementation,
                "version": 1,
                "consumers": [],
            }
            self.store.append_event("CAPABILITY_PROPOSED", actor, {**common, "status": "PROPOSED"}, task_id=producer_task, entity_id=name)
            claim = {
                **common,
                "status": "CLAIMED",
                "claim_lease_id": lease.get("lease_id") if lease else None,
                "claim_fencing_token": lease.get("fencing_token") if lease else None,
            }
            self.store.append_event("CAPABILITY_CLAIMED", actor, claim, task_id=producer_task, entity_id=name)
            return {"claimed": True, "capability": self.capability(name)}

    def renew_task_claims(self, task_id: str, *, ttl_seconds: int = 3600) -> list[str]:
        renewed: list[str] = []
        for capability in self.snapshot()["capabilities"].values():
            if capability.get("producer_task") != task_id or capability.get("status") not in ACTIVE_CAPABILITY_STATES:
                continue
            lease_id = capability.get("claim_lease_id")
            token = capability.get("claim_fencing_token")
            try:
                if not lease_id or not token:
                    raise CoordinationConflict("claim has no lease")
                self.store.heartbeat(lease_id, token, ttl_seconds=ttl_seconds)
            except CoordinationConflict:
                lease = self.store.acquire_lease(
                    f"capability:{capability['name']}", task_id, ttl_seconds=ttl_seconds, mode="write"
                )
                self.store.append_event(
                    "CAPABILITY_CLAIMED", "orchestrator",
                    {
                        "name": capability["name"], "status": "CLAIMED",
                        "producer_task": task_id,
                        "claim_lease_id": lease["lease_id"],
                        "claim_fencing_token": lease["fencing_token"],
                    },
                    task_id=task_id, entity_id=capability["name"],
                )
            renewed.append(capability["name"])
        return renewed

    def transition_capability(
        self, name: str, status: str, *, actor: str, task_id: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        name = validate_capability_name(name)
        with self.store.lock(f"capability-claim:{name}"):
            current = self.capability(name)
            if not current:
                raise CoordinationConflict(f"Unknown capability: {name}")
            if current.get("producer_task") != task_id:
                raise CoordinationConflict(f"Only producer {current.get('producer_task')} may transition {name}")
            if status not in CAPABILITY_TRANSITIONS.get(current.get("status"), set()):
                raise CoordinationConflict(f"Invalid capability transition {current.get('status')} -> {status}")
            if status == "AVAILABLE" and not (
                details and details.get("source_sha256") and details.get("validation_evidence")
            ):
                raise CoordinationConflict(
                    "AVAILABLE transition requires verified source snapshot and validation evidence"
                )
            payload = {"name": name, "status": status, **(details or {})}
            self.store.append_event(f"CAPABILITY_{status}", actor, payload, task_id=task_id, entity_id=name)
            if status in {"AVAILABLE", "FROZEN", "DEPRECATED", "INVALID"}:
                snapshot = self.snapshot()
                dependency_status = "RESOLVED" if status in {"AVAILABLE", "FROZEN"} else "STALE"
                for dependency in snapshot["dependencies"].values():
                    if dependency.get("capability") != name:
                        continue
                    self.store.append_event(
                        f"DEPENDENCY_{dependency_status}", actor,
                        {
                            "id": dependency["id"],
                            "status": dependency_status,
                            "producer_task": task_id,
                            "resolved_version": self.capability(name).get("version", 1),
                        },
                        task_id=dependency["consumer_task"], entity_id=dependency["id"],
                    )
                    if dependency_status == "RESOLVED":
                        self.store.append_event(
                            "TASK_DEPENDENCY_READY", actor,
                            {"dependency_id": dependency["id"], "capability": name},
                            task_id=dependency["consumer_task"], entity_id=dependency["id"],
                        )
            return self.capability(name) or {}

    def mark_available(
        self, name: str, *, actor: str, task_id: str, workspace: Path,
        source_sha256: str, validation_evidence: str,
    ) -> dict[str, Any]:
        current = self.capability(name)
        if not current:
            raise CoordinationConflict(f"Unknown capability: {name}")
        implementation = current.get("implementation", {})
        relative = implementation.get("file")
        symbol = implementation.get("symbol")
        if not relative or not symbol or not validation_evidence:
            raise CoordinationConflict("AVAILABLE requires file, symbol and validation evidence")
        source = (workspace / relative).resolve()
        try:
            source.relative_to(workspace.resolve())
        except ValueError as exc:
            raise CoordinationConflict("Capability source escapes its repository workspace") from exc
        if not source.is_file():
            raise CoordinationConflict(f"Capability source does not exist: {relative}")
        actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual_hash != source_sha256:
            raise CoordinationConflict("Capability source snapshot is stale")
        symbol_leaf = symbol.rsplit(".", 1)[-1]
        if symbol_leaf not in source.read_text(encoding="utf-8", errors="ignore"):
            raise CoordinationConflict(f"Capability symbol was not found: {symbol}")
        return self.transition_capability(
            name, "AVAILABLE", actor=actor, task_id=task_id,
            details={"source_sha256": source_sha256, "validation_evidence": validation_evidence},
        )

    def register_consumer(self, name: str, task_id: str, *, actor: str) -> dict[str, Any]:
        name = validate_capability_name(name)
        self.store.append_event(
            "CONSUMER_REGISTERED", actor, {"capability": name, "task": task_id},
            task_id=task_id, entity_id=name,
        )
        return self.capability(name) or {}

    def register_dependency(
        self, consumer_task: str, capability: str, *, actor: str,
        source: str = "runtime_discovered", blocking: bool = True,
        required_version: int | None = None, dependency_id: str | None = None,
    ) -> dict[str, Any]:
        capability = validate_capability_name(capability)
        current = self.capability(capability)
        status = "RESOLVED" if current and current.get("status") in {"AVAILABLE", "FROZEN"} else "WAITING"
        dependency = {
            "id": dependency_id or f"DEP-{uuid4()}",
            "consumer_task": consumer_task,
            "type": "capability",
            "capability": capability,
            "source": source,
            "blocking": blocking,
            "required_version": required_version,
            "producer_task": current.get("producer_task") if current else None,
            "status": status,
        }
        self.store.append_event("DEPENDENCY_REGISTERED", actor, dependency, task_id=consumer_task, entity_id=dependency["id"])
        if current:
            self.register_consumer(capability, consumer_task, actor=actor)
        return self.snapshot()["dependencies"][dependency["id"]]

    def register_resource_access(
        self, task_id: str, repository: str, path: str, access: str, visibility: str, *,
        actor: str, symbol: str | None = None, confirmed: bool = False,
    ) -> dict[str, Any]:
        resource = canonical_resource_id(repository, path, symbol)
        payload = {
            "id": f"ACCESS-{uuid4()}",
            "task": task_id,
            "resource": resource,
            "repository": repository,
            "path": path,
            "symbol": symbol,
            "access": access,
            "visibility": visibility,
            "classification": "confirmed_dependency" if confirmed else "observed",
        }
        event_type = "RESOURCE_WRITE_INTENT" if access == "WRITE" else "RESOURCE_READ_DISCOVERED"
        self.store.append_event(event_type, actor, payload, task_id=task_id, entity_id=resource)
        return self.snapshot()["resource_accesses"][payload["id"]]

    def claim_resource(
        self, task_id: str, repository: str, path: str, *, actor: str,
        symbol: str | None = None, ttl_seconds: int = 3600,
    ) -> dict[str, Any]:
        access = self.register_resource_access(
            task_id, repository, path, "WRITE", "SHARED", actor=actor,
            symbol=symbol, confirmed=True,
        )
        lease = self.store.acquire_lease(
            f"code-resource:{access['resource']}", task_id,
            ttl_seconds=ttl_seconds, mode="write",
        )
        claimed = {
            **access,
            "status": "CLAIMED",
            "lease_id": lease["lease_id"],
            "fencing_token": lease["fencing_token"],
        }
        self.store.append_event(
            "RESOURCE_CLAIMED", actor, claimed, task_id=task_id,
            entity_id=access["resource"],
        )
        return self.snapshot()["resource_accesses"][access["id"]]

    def release_resource(self, access_id: str, task_id: str, *, actor: str) -> dict[str, Any]:
        current = self.snapshot()["resource_accesses"].get(access_id)
        if not current or current.get("task") != task_id:
            raise CoordinationConflict(f"Resource claim is not owned by {task_id}: {access_id}")
        self.store.release_lease(current["lease_id"], current["fencing_token"])
        released = {**current, "status": "RELEASED"}
        self.store.append_event(
            "RESOURCE_RELEASED", actor, released, task_id=task_id,
            entity_id=current["resource"],
        )
        return self.snapshot()["resource_accesses"][access_id]

    def active_resource_claims(self, *, exclude_task: str | None = None) -> list[dict[str, Any]]:
        live = {lease["lease_id"] for lease in self.store.active_leases(resource_prefix="code-resource:")}
        return [
            value for value in self.snapshot()["resource_accesses"].values()
            if value.get("status") == "CLAIMED"
            and value.get("lease_id") in live
            and value.get("task") != exclude_task
        ]

    def renew_task_resource_claims(self, task_id: str, *, ttl_seconds: int = 3600) -> list[str]:
        renewed: list[str] = []
        for access in self.snapshot()["resource_accesses"].values():
            if access.get("task") != task_id or access.get("status") != "CLAIMED":
                continue
            lease_id, token = access.get("lease_id"), access.get("fencing_token")
            try:
                if not lease_id or not token:
                    raise CoordinationConflict("resource claim has no lease")
                self.store.heartbeat(lease_id, token, ttl_seconds=ttl_seconds)
            except CoordinationConflict:
                lease = self.store.acquire_lease(
                    f"code-resource:{access['resource']}", task_id,
                    ttl_seconds=ttl_seconds, mode="write",
                )
                self.store.append_event(
                    "RESOURCE_CLAIMED", "orchestrator",
                    {
                        **access, "status": "CLAIMED",
                        "lease_id": lease["lease_id"],
                        "fencing_token": lease["fencing_token"],
                    },
                    task_id=task_id, entity_id=access["resource"],
                )
            renewed.append(access["id"])
        return renewed

    def complete_task_claims(self, task_id: str) -> None:
        snapshot = self.snapshot()
        for access in list(snapshot["resource_accesses"].values()):
            if access.get("task") == task_id and access.get("status") == "CLAIMED":
                self.release_resource(access["id"], task_id, actor="orchestrator")
        for capability in list(self.snapshot()["capabilities"].values()):
            if capability.get("producer_task") != task_id:
                continue
            if capability.get("status") == "AVAILABLE":
                self.transition_capability(
                    capability["name"], "FROZEN", actor="orchestrator", task_id=task_id
                )
                capability = self.capability(capability["name"]) or capability
            if capability.get("claim_lease_id") and capability.get("claim_fencing_token"):
                try:
                    self.store.release_lease(
                        capability["claim_lease_id"], capability["claim_fencing_token"]
                    )
                except CoordinationConflict:
                    pass

    def change_contract(
        self, name: str, new_contract: dict[str, Any], *, actor: str, task_id: str,
    ) -> dict[str, Any]:
        name = validate_capability_name(name)
        with self.store.lock(f"capability-claim:{name}"):
            current = self.capability(name)
            if not current or current.get("producer_task") != task_id:
                raise CoordinationConflict(f"Only the producer may change capability contract: {name}")
            old_contract = current.get("contract", {})
            classification = classify_contract_change(old_contract, new_contract)
            new_version = int(current.get("version", 1))
            if classification["impact_level"] != LEVEL_0:
                new_version += 1
            payload = {
                "name": name,
                "status": current["status"],
                "version": new_version,
                "contract": new_contract,
                "contract_fingerprint": contract_fingerprint(new_contract),
                **classification,
            }
            self.store.append_event("CAPABILITY_CHANGED", actor, payload, task_id=task_id, entity_id=name)
            affected: list[str] = []
            if classification["impact_level"] not in {LEVEL_0, LEVEL_1}:
                for dependency in self.snapshot()["dependencies"].values():
                    if dependency.get("capability") != name:
                        continue
                    affected.append(dependency["consumer_task"])
                    self.store.append_event(
                        "DEPENDENCY_BECAME_STALE", actor,
                        {
                            "id": dependency["id"], "status": "STALE",
                            "reason": "capability_contract_changed", "required_revalidation": True,
                            "available_version": new_version,
                        },
                        task_id=dependency["consumer_task"], entity_id=dependency["id"],
                    )
            return {
                "capability": self.capability(name),
                "impact_level": classification["impact_level"],
                "compatibility": classification["compatibility"],
                "affected_consumers": sorted(set(affected)),
            }


def verify_task_coordination(task_id: str) -> None:
    from .ai_common import read_json, read_yaml, task_dir
    td = task_dir(task_id)
    plan = read_json(td / "execution-plan.json")
    state = read_yaml(td / "state.yaml")
    snapshot = RegistryService(CoordinationStore()).snapshot()
    errors: list[str] = []
    accesses = list(snapshot["resource_accesses"].values())
    for item in plan.get("slices", []):
        for declared in item.get("resource_accesses", []):
            if declared.get("visibility") != "SHARED" or declared.get("access") != "WRITE":
                continue
            resource = canonical_resource_id(
                declared["repository"], declared["path"], declared.get("symbol")
            )
            if not any(
                access.get("task") == task_id
                and access.get("resource") == resource
                and access.get("access") == "WRITE"
                and access.get("classification") == "confirmed_dependency"
                for access in accesses
            ):
                errors.append(f"slice {item['id']}: shared write has no registered claim: {resource}")
        for reference in item.get("external_dependencies", []):
            dependency = snapshot["dependencies"].get(reference["dependency_id"])
            if not dependency or dependency.get("status") != "RESOLVED":
                errors.append(f"slice {item['id']}: dependency is not resolved: {reference['dependency_id']}")
            elif reference.get("required_version") and dependency.get("resolved_version", 0) < reference["required_version"]:
                errors.append(f"slice {item['id']}: dependency version is stale: {reference['dependency_id']}")
    if state.get("revalidation_state") in {"required", "stale"}:
        errors.append(f"task revalidation_state is {state.get('revalidation_state')}")
    for capability in snapshot["capabilities"].values():
        if capability.get("producer_task") == task_id and capability.get("status") not in {"AVAILABLE", "FROZEN"}:
            errors.append(
                f"produced capability is not available: {capability['name']} ({capability.get('status')})"
            )
    if errors:
        raise SystemExit("Coordination contract gate failed:\n- " + "\n- ".join(errors))
