"""Dependency- and resource-aware execution-plan scheduler."""
from __future__ import annotations

from typing import Any

from .resources import Access, ResourceAccess, Visibility, conflicts


class SchedulingError(RuntimeError):
    pass


def _assert_acyclic(slices: list[dict[str, Any]]) -> None:
    graph = {item["id"]: item.get("depends_on", []) for item in slices}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise SchedulingError(f"Execution-plan dependency cycle detected at {node}")
        if node in visited:
            return
        if node not in graph:
            raise SchedulingError(f"Unknown slice dependency: {node}")
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _access(item: dict[str, Any]) -> ResourceAccess:
    return ResourceAccess(
        repository=item["repository"], path=item["path"], access=Access(item["access"]),
        visibility=Visibility(item["visibility"]), symbol=item.get("symbol"),
        whole_file_writer=item.get("whole_file_writer", True),
    )


def schedule(
    plan: dict[str, Any], registry: dict[str, Any], *, active_resource_accesses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    slices = plan.get("slices", [])
    _assert_acyclic(slices)
    by_id = {item["id"]: item for item in slices}
    dependencies = registry.get("dependencies", {})
    active = [_access(item) for item in (active_resource_accesses or [])]
    runnable: list[str] = []
    blocked: dict[str, list[dict[str, str]]] = {}

    for item in slices:
        if item.get("status") == "completed":
            continue
        reasons: list[dict[str, str]] = []
        for predecessor in item.get("depends_on", []):
            if by_id[predecessor].get("status") != "completed":
                reasons.append({"type": "slice", "id": predecessor, "reason": "predecessor_not_completed"})
        for reference in item.get("external_dependencies", []):
            dependency = dependencies.get(reference["dependency_id"])
            if not dependency or dependency.get("status") != "RESOLVED":
                reasons.append({
                    "type": "dependency", "id": reference["dependency_id"],
                    "reason": "dependency_not_ready" if dependency else "dependency_missing",
                })
            elif reference.get("required_version") and dependency.get("resolved_version", 0) < reference["required_version"]:
                reasons.append({"type": "dependency", "id": reference["dependency_id"], "reason": "dependency_version_too_old"})
        requested = [_access(value) for value in item.get("resource_accesses", [])]
        if any(conflicts(left, right) for left in requested for right in active):
            reasons.append({"type": "resource", "id": item["id"], "reason": "resource_conflict"})
        if reasons:
            blocked[item["id"]] = reasons
        else:
            runnable.append(item["id"])

    pending_count = len(runnable) + len(blocked)
    dependency_state = "ready"
    if blocked and runnable:
        dependency_state = "partially_blocked"
    elif blocked and pending_count == len(blocked):
        dependency_state = "blocked"
    return {
        "runnable_slices": runnable,
        "blocked_slices": blocked,
        "dependency_state": dependency_state,
        "dependency_blockers": [
            {"slice_id": slice_id, **reason}
            for slice_id, reasons in blocked.items() for reason in reasons
        ],
    }
