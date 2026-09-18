"""Contract fingerprinting, impact classification and checkpoint freshness."""
from __future__ import annotations

import hashlib
import json
from typing import Any


LEVEL_0 = "LEVEL_0"
LEVEL_1 = "LEVEL_1"
LEVEL_2 = "LEVEL_2"
LEVEL_3 = "LEVEL_3"


def contract_fingerprint(contract: dict[str, Any]) -> str:
    canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def classify_contract_change(old: dict[str, Any], new: dict[str, Any]) -> dict[str, str]:
    if contract_fingerprint(old) == contract_fingerprint(new):
        return {"compatibility": "implementation_only", "impact_level": LEVEL_0}
    hint = new.get("compatibility_hint")
    if hint == "additive":
        return {"compatibility": "compatible", "impact_level": LEVEL_1}
    if hint == "revalidate":
        return {"compatibility": "compatible", "impact_level": LEVEL_2}
    return {"compatibility": "breaking", "impact_level": LEVEL_3}


def make_checkpoint(
    *, phase: str, plan_version: int, context_version: int | str,
    dependencies: dict[str, dict[str, Any]], source_snapshots: dict[str, str],
    fencing_tokens: dict[str, int] | None = None, target_sha: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": phase,
        "plan_version": plan_version,
        "context_version": context_version,
        "dependencies": dependencies,
        "source_snapshots": source_snapshots,
        "fencing_tokens": fencing_tokens or {},
        "target_sha": target_sha,
    }


def compare_checkpoint(recorded: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    impact = LEVEL_0
    if recorded.get("plan_version") != current.get("plan_version"):
        reasons.append("plan_version_changed")
        impact = LEVEL_2
    if recorded.get("context_version") != current.get("context_version"):
        reasons.append("context_version_changed")
        impact = max((impact, LEVEL_2), key=lambda value: int(value[-1]))
    for name, dependency in recorded.get("dependencies", {}).items():
        latest = current.get("dependencies", {}).get(name)
        if latest is None:
            reasons.append(f"dependency_missing:{name}")
            impact = LEVEL_3
        elif (
            dependency.get("version") != latest.get("version")
            or dependency.get("fingerprint") != latest.get("fingerprint")
            or dependency.get("status") != latest.get("status")
        ):
            reasons.append(f"dependency_changed:{name}")
            declared = latest.get("impact_level", LEVEL_3)
            impact = max((impact, declared), key=lambda value: int(value[-1]))
    if recorded.get("source_snapshots") != current.get("source_snapshots"):
        reasons.append("source_snapshot_changed")
        impact = max((impact, LEVEL_2), key=lambda value: int(value[-1]))
    if recorded.get("target_sha") and recorded.get("target_sha") != current.get("target_sha"):
        reasons.append("target_sha_changed")
        impact = LEVEL_3
    if recorded.get("fencing_tokens") != current.get("fencing_tokens"):
        reasons.append("lease_fencing_changed")
        impact = LEVEL_3
    return {"fresh": not reasons, "impact_level": impact, "reasons": reasons}
