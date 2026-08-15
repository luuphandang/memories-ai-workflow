from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from lib.ai_common import (
    AI_ROOT,
    ROOT,
    ensure_task,
    git_value,
    now_iso,
    read_json,
    read_yaml,
    requirement_documents,
    write_json,
)

from .models import MemoryPublishEntry, MemoryPublishRequest, MemoryQuery, RepositoryMemoryRef
from .provider import get_provider, provider_name

INTEGRATION_ROOT = AI_ROOT / "integrations" / "tencentdb-memory"
CONFIG_PATH = INTEGRATION_ROOT / "config.yaml"
SUPERSESSION_PATH = INTEGRATION_ROOT / "local-index" / "superseded-assets.json"
PUBLISH_POLICY_PATH = INTEGRATION_ROOT / "publish-policy.yaml"

_DEFAULT_CONFIG = {
    "enabled": False,
    "required": False,
    "timeout_seconds": 10,
    "recall": {"max_items": 8},
    "fallback": {"use_static_context": True},
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return dict(_DEFAULT_CONFIG)
    return read_yaml(CONFIG_PATH)


def env_enabled() -> bool:
    """AI_MEMORY_ENABLED is the hard global kill switch (default false).

    No task.yaml or config.yaml value can turn memory on when this is false; see
    effective_settings() and ai/integrations/memory/provider-contract.md.
    """
    return os.environ.get("AI_MEMORY_ENABLED", "false").strip().lower() == "true"


def effective_settings(task: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    task_memory = task.get("memory") or {}

    base_enabled = bool(task_memory["enabled"]) if "enabled" in task_memory else bool(config.get("enabled", False))
    enabled = env_enabled() and base_enabled

    base_required = bool(task_memory["required"]) if "required" in task_memory else bool(config.get("required", False))
    required = base_required and enabled

    max_items = (
        task_memory.get("recall", {}).get("max_items")
        or config.get("recall", {}).get("max_items")
        or _DEFAULT_CONFIG["recall"]["max_items"]
    )
    timeout_seconds = int(
        os.environ.get(
            "AI_MEMORY_TIMEOUT_SECONDS",
            str(config.get("timeout_seconds", _DEFAULT_CONFIG["timeout_seconds"])),
        )
    )
    return {
        "enabled": enabled,
        "required": required,
        "max_items": int(max_items),
        "timeout_seconds": timeout_seconds,
    }


def _first_excerpt(text: str, limit: int = 400) -> str:
    """Deterministic bounded excerpt: the first paragraph after the first heading."""
    collected: list[str] = []
    started = False
    for line in text.splitlines():
        stripped = line.strip()
        if not started:
            if stripped.startswith("#"):
                started = True
            continue
        if stripped.startswith("#") and collected:
            break
        if stripped:
            collected.append(stripped)
        if sum(len(part) for part in collected) >= limit:
            break
    return " ".join(collected)[:limit]


def _query_text(task_id: str, task: dict[str, Any]) -> str:
    td = ensure_task(task_id)
    parts = [str(task.get("title", "")).strip()]
    task_md = td / "task.md"
    if task_md.is_file():
        excerpt = _first_excerpt(task_md.read_text(encoding="utf-8"))
        if excerpt:
            parts.append(excerpt)
    for doc in requirement_documents(task_id, include_user_request=True):
        path = ROOT / doc
        if not path.is_file():
            continue
        headers = [
            line.lstrip("#").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("#")
        ]
        parts.extend(headers[:5])
    return " \n".join(part for part in parts if part)[:2000]


def _load_supersession() -> dict[str, Any]:
    if not SUPERSESSION_PATH.is_file():
        return {"version": 1, "entries": []}
    return read_json(SUPERSESSION_PATH)


def _save_supersession(data: dict[str, Any]) -> None:
    write_json(SUPERSESSION_PATH, data)


def _superseded_asset_ids() -> set[str]:
    data = _load_supersession()
    return {entry["asset_id"] for entry in data.get("entries", []) if entry.get("status") == "superseded"}


def record_publish(
    task_id: str,
    change_cycle: int,
    published: list[dict[str, Any]],
    explicit_supersedes: str | None = None,
) -> list[dict[str, Any]]:
    """Update the local supersession ledger after a publish; return newly-superseded entries.

    Automatic supersession is scoped to same-task, same-target republishes only (a
    requirement_change cycle republishing to the same ai/shared|repos|domains target).
    Cross-task supersession requires the explicit `--supersedes <asset_id>` flag, since
    knowledge-updates.json has no stable cross-task identity to infer it from. See
    ai/integrations/tencentdb-memory/upstream-notes.md.
    """
    data = _load_supersession()
    entries = data.setdefault("entries", [])
    superseded_now: list[dict[str, Any]] = []
    for item in published:
        target = item.get("target")
        asset_id = item.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            continue
        matches = (
            [entry for entry in entries if entry.get("asset_id") == explicit_supersedes and entry.get("status") == "active"]
            if explicit_supersedes
            else [
                entry
                for entry in entries
                if entry.get("status") == "active"
                and entry.get("target") == target
                and entry.get("source_task") == task_id
                and entry.get("asset_id") != asset_id
            ]
        )
        for entry in matches:
            entry["status"] = "superseded"
            entry["superseded_by"] = asset_id
            superseded_now.append({"asset_id": entry["asset_id"], "target": entry.get("target")})
        entries.append(
            {
                "asset_id": asset_id,
                "asset_type": item.get("category"),
                "target": target,
                "status": "active",
                "source_task": task_id,
                "change_cycle": change_cycle,
                "supersedes": explicit_supersedes,
                "superseded_by": None,
                "recorded_at": now_iso(),
            }
        )
    _save_supersession(data)
    return superseded_now


def _write_recall_markdown(path: Path, snapshot_dict: dict[str, Any]) -> None:
    lines = [
        f"# Memory recall — {snapshot_dict['task_id']}",
        "",
        f"Provider: {snapshot_dict['provider']}",
        f"Generated: {snapshot_dict['generated_at']}",
        f"Available: {snapshot_dict['available']}",
        "",
    ]
    if not snapshot_dict["available"]:
        lines.append(f"Fallback: {snapshot_dict.get('fallback')} (error_code={snapshot_dict.get('error_code')})")
        lines.append("")
    items = snapshot_dict.get("items", [])
    if items:
        lines.append("| Title | Asset type | Source |")
        lines.append("|---|---|---|")
        for item in items:
            lines.append(f"| {item.get('title', '')} | {item.get('asset_type', '')} | {item.get('source') or ''} |")
    else:
        lines.append("No memory items recalled.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def recall_for_task(task_id: str) -> tuple[dict[str, Any], list[str]]:
    """Run (or skip) a memory recall for a task; return (context.lock.json memory
    block, missing_reasons). `missing_reasons` is empty unless memory is enabled,
    required, and unavailable -- callers (prepare-context) fold it into their own
    `missing` accumulator instead of this function raising SystemExit itself, so a
    required-memory failure is reported through the same single gate as every other
    prepare-context failure (see ai/integrations/memory/provider-contract.md)."""
    td = ensure_task(task_id)
    task = read_yaml(td / "task.yaml")
    state = read_yaml(td / "state.yaml")
    settings = effective_settings(task)
    memory_dir = td / "memory"

    if not settings["enabled"]:
        return {"enabled": False}, []

    query = MemoryQuery(
        task_id=task_id,
        implementation_cycle=int(state.get("implementation_cycle", 1)),
        change_cycle=int(state.get("change_cycle", 0)),
        text=_query_text(task_id, task),
        repositories=[item["repo"] for item in task.get("worktrees", [])],
        asset_types=["wiki", "code_graph", "skill", "chat_memory"],
        max_items=settings["max_items"],
    )

    snapshot_obj = get_provider().recall(query)
    superseded_ids = _superseded_asset_ids()
    snapshot_obj.items = [item for item in snapshot_obj.items if item.asset_id not in superseded_ids]

    content = json.dumps([asdict(item) for item in snapshot_obj.items], sort_keys=True, ensure_ascii=False)
    snapshot_obj.content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    snapshot_dict = asdict(snapshot_obj)
    memory_dir.mkdir(parents=True, exist_ok=True)
    write_json(memory_dir / "recall.json", snapshot_dict)
    _write_recall_markdown(memory_dir / "recall.md", snapshot_dict)

    memory_block = {
        "enabled": True,
        "provider": snapshot_obj.provider,
        "available": snapshot_obj.available,
        "snapshot": f"ai/tasks/{task_id}/memory/recall.json",
        "sha256": snapshot_obj.content_sha256,
        "fallback": snapshot_obj.fallback,
        "error_code": snapshot_obj.error_code,
    }

    missing: list[str] = []
    if not snapshot_obj.available:
        if settings["required"]:
            missing.append(
                f"memory recall unavailable: {snapshot_obj.error_code or 'unknown error'} "
                "(memory.required is true via task.yaml/config.yaml)"
            )
        else:
            print(
                f"[memory] WARNING: backend unavailable, falling back to static context "
                f"({snapshot_obj.error_code})"
            )
    return memory_block, missing


def _category_for(target: str) -> str:
    policy = read_yaml(PUBLISH_POLICY_PATH) if PUBLISH_POLICY_PATH.is_file() else {}
    table = policy.get("category_by_filename", {})
    return table.get(Path(target).name, policy.get("default_category", "implementation_pattern"))


def publish_for_task(task_id: str, supersedes: str | None = None) -> dict[str, Any]:
    """Publish approved knowledge-updates.json entries as durable memory.

    Gated on state.status == completed AND acceptance.status == accepted, checked the
    same way accept-task/update-knowledge already check those files. Never invoked
    automatically by accept-task -- remains an explicit, separate step."""
    td = ensure_task(task_id)
    state = read_yaml(td / "state.yaml")
    if state.get("status") != "completed":
        raise SystemExit(
            f"memory publish requires state.status == completed, found {state.get('status')!r}"
        )
    acceptance_path = td / "acceptance.yaml"
    if not acceptance_path.is_file():
        raise SystemExit("memory publish requires acceptance.yaml; task was never accepted")
    acceptance = read_yaml(acceptance_path)
    if acceptance.get("status") != "accepted":
        raise SystemExit(
            f"memory publish requires acceptance.status == accepted, found {acceptance.get('status')!r}"
        )

    task = read_yaml(td / "task.yaml")
    settings = effective_settings(task)
    if not settings["enabled"]:
        raise SystemExit(
            "memory is disabled (AI_MEMORY_ENABLED=false or task.yaml memory.enabled=false); nothing to publish"
        )

    updates_path = td / "knowledge-updates.json"
    updates = read_json(updates_path) if updates_path.is_file() else {"updates": []}
    approved = [item for item in updates.get("updates", []) if item.get("approved")]
    change_cycle = int(state.get("change_cycle", 0))

    entries = [
        MemoryPublishEntry(
            category=item.get("category") or _category_for(item["target"]),
            target=item["target"],
            summary=item.get("summary", ""),
            content=item.get("content", ""),
            evidence={"task_id": task_id, "change_cycle": change_cycle, "source_update_index": index},
            supersedes=supersedes,
        )
        for index, item in enumerate(approved, start=1)
    ]

    result = get_provider().publish(
        MemoryPublishRequest(task_id=task_id, change_cycle=change_cycle, entries=entries)
    )
    superseded = record_publish(task_id, change_cycle, result.published, supersedes)
    return {
        "published": result.published,
        "superseded": superseded,
        "errors": result.errors,
        "generated_at": result.generated_at,
    }


def probe_repository(repo: str) -> RepositoryMemoryRef:
    """Local-git-only capability probe: apps/<repo> only, never worktrees/<TICKET>/<repo>."""
    path = ROOT / "apps" / repo
    if not path.is_dir():
        return RepositoryMemoryRef(
            repo=repo, path=f"apps/{repo}", supports_code_graph=False, reason="apps/<repo> does not exist"
        )
    remote = git_value(path, ["remote", "get-url", "origin"], "")
    if not remote.startswith("https://"):
        return RepositoryMemoryRef(
            repo=repo,
            path=f"apps/{repo}",
            remote_url=None,
            supports_code_graph=False,
            reason=(
                "origin remote is not a public https:// URL; upstream CodeGraph only "
                "accepts a clonable https remote (see upstream-notes.md)"
            ),
        )
    return RepositoryMemoryRef(repo=repo, path=f"apps/{repo}", remote_url=remote, supports_code_graph=True)


def sync_repository_for(repo: str) -> dict[str, Any]:
    ref = probe_repository(repo)
    if not env_enabled() or not bool(load_config().get("enabled", False)):
        result = asdict(ref)
        result["supports_code_graph"] = False
        result["reason"] = "memory is disabled (AI_MEMORY_ENABLED=false)"
        return result
    if not ref.supports_code_graph:
        return asdict(ref)
    return asdict(get_provider().sync_repository(ref))


def prompt_guidance(context_lock: dict[str, Any]) -> str:
    """One-line guidance for run-claude/run-codex-review prompts, mirroring
    lib.codegraph.prompt_guidance's shape. Never called by an agent directly -- only
    read here, from the already-locked context.lock.json, at prompt-build time."""
    memory = context_lock.get("memory") or {}
    if not memory.get("enabled"):
        return "Persistent memory is disabled for this task; use normal repository discovery."
    if not memory.get("available", True):
        return (
            f"Persistent memory is enabled but currently unavailable ({memory.get('error_code')}); "
            "falling back to static context."
        )
    return (
        f"Persistent memory is ready ({memory.get('snapshot')}). Read it before re-deriving "
        "context that may already be captured there; ai/shared|repos|domains still win on conflict."
    )


def health_probe() -> dict[str, Any]:
    enabled = env_enabled() and bool(load_config().get("enabled", False))
    service_root = os.environ.get("AI_MEMORY_SERVICE_ROOT", "").strip()
    result: dict[str, Any] = {
        "provider": provider_name(),
        "enabled": enabled,
        "service_root_exists": Path(service_root).is_dir() if service_root else False,
        "auth_configured": bool(os.environ.get("AI_MEMORY_API_KEY", "").strip()),
    }
    if not enabled:
        return result
    health = get_provider().health()
    result.update(
        {
            "service_available": health.available,
            "api_version": health.api_version,
            "wiki_supported": health.wiki_supported,
            "skill_supported": health.skill_supported,
            "code_graph_supported": health.code_graph_supported,
            "recall_supported": health.recall_supported,
            "publish_supported": health.publish_supported,
        }
    )
    if health.reason:
        result["reason"] = health.reason
    return result
