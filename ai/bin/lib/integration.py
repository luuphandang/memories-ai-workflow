"""Non-agent integration gate over an isolated temporary Git clone."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from typing import Any
import contextlib

from .ai_common import (
    atomic_write, dirty_worktree_hash, git_value, now_iso, read_json, read_yaml,
    runtime_dir, safe_workspace_path, task_dir,
)
from .coordination import CoordinationStore


class IntegrationError(RuntimeError):
    pass


def _run(command: list[str], cwd: Path, *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=cwd, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=input_bytes is None, check=False,
    )


def integration_fingerprint(
    source: Path, target_ref: str, *, plan_version: int,
    dependency_versions: dict[str, Any],
) -> dict[str, Any]:
    target_sha = git_value(source, ["rev-parse", target_ref])
    return {
        "source_head": git_value(source, ["rev-parse", "HEAD"]),
        "source_dirty_snapshot": dirty_worktree_hash(source),
        "target_ref": target_ref,
        "target_sha": target_sha,
        "plan_version": plan_version,
        "dependency_versions": dependency_versions,
    }


def manifest_fresh(manifest: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "source_head", "source_dirty_snapshot", "target_ref", "target_sha",
        "plan_version", "dependency_versions",
    )
    changed = [field for field in fields if manifest.get(field) != current.get(field)]
    return {"fresh": not changed, "changed": changed}


class IntegrationGate:
    def validate(
        self, *, task_id: str, repository: str, source: Path, base_sha: str,
        target_ref: str, plan_version: int, dependency_versions: dict[str, Any],
        validation_commands: list[str], manifest_path: Path | None = None,
        merge_order: int = 1,
    ) -> dict[str, Any]:
        if not validation_commands:
            raise IntegrationError("Integration validation requires at least one command")
        unavailable = {
            name: value for name, value in dependency_versions.items()
            if value.get("status") not in {None, "AVAILABLE", "FROZEN"}
        }
        if unavailable:
            raise IntegrationError(
                "Integration dependencies are not ready: " + ", ".join(sorted(unavailable))
            )
        fingerprint = integration_fingerprint(
            source, target_ref, plan_version=plan_version,
            dependency_versions=dependency_versions,
        )
        with tempfile.TemporaryDirectory(prefix=f"ai-integration-{task_id}-") as raw:
            tree = Path(raw) / repository
            clone = _run(["git", "clone", "-q", "--no-hardlinks", str(source), str(tree)], source.parent)
            if clone.returncode:
                raise IntegrationError(str(clone.stdout))
            checkout = _run(["git", "checkout", "-q", "--detach", fingerprint["target_sha"]], tree)
            if checkout.returncode:
                raise IntegrationError(str(checkout.stdout))
            diff = subprocess.run(
                ["git", "diff", "--binary", base_sha], cwd=source,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            if diff.returncode:
                raise IntegrationError(diff.stderr.decode("utf-8", errors="replace"))
            if diff.stdout:
                check = _run(["git", "apply", "--check", "--binary", "-"], tree, input_bytes=diff.stdout)
                if check.returncode:
                    conflict_output = check.stdout.decode("utf-8", errors="replace")
                    manifest = {
                        **fingerprint, "schema_version": 1, "task_id": task_id,
                        "repository": repository, "base_sha": base_sha,
                        "integration_tree_sha": "unavailable", "merge_order": merge_order,
                        "validation_snapshot_sha256": hashlib.sha256(conflict_output.encode()).hexdigest(),
                        "validation": [], "status": "CONFLICTED",
                        "conflict_output": conflict_output, "generated_at": now_iso(),
                    }
                    if manifest_path:
                        atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
                    return manifest
                apply_result = _run(["git", "apply", "--binary", "-"], tree, input_bytes=diff.stdout)
                if apply_result.returncode:
                    raise IntegrationError(apply_result.stdout.decode("utf-8", errors="replace"))
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=source,
                stdout=subprocess.PIPE, check=True,
            ).stdout.split(b"\0")
            for encoded in untracked:
                if not encoded:
                    continue
                relative = encoded.decode("utf-8", errors="surrogateescape")
                destination = tree / relative
                if destination.exists() and destination.read_bytes() != (source / relative).read_bytes():
                    conflict_output = f"Untracked source file conflicts with target path: {relative}"
                    manifest = {
                        **fingerprint, "schema_version": 1, "task_id": task_id,
                        "repository": repository, "base_sha": base_sha,
                        "integration_tree_sha": "unavailable", "merge_order": merge_order,
                        "validation_snapshot_sha256": hashlib.sha256(conflict_output.encode()).hexdigest(),
                        "validation": [], "status": "CONFLICTED",
                        "conflict_output": conflict_output, "generated_at": now_iso(),
                    }
                    if manifest_path:
                        atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
                    return manifest
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, destination)
            command_results = []
            for command in validation_commands:
                result = _run(shlex.split(command), tree)
                command_results.append({
                    "command": command, "exit_code": result.returncode,
                    "output_tail": str(result.stdout)[-4000:],
                })
                if result.returncode:
                    break
            _run(["git", "add", "-A"], tree)
            integration_tree_sha = git_value(tree, ["write-tree"])
            status = "MERGE_READY" if all(item["exit_code"] == 0 for item in command_results) else "CONFLICTED"
            validation_hash = hashlib.sha256(
                json.dumps(command_results, sort_keys=True).encode("utf-8")
            ).hexdigest()
            manifest = {
                **fingerprint,
                "schema_version": 1,
                "task_id": task_id,
                "repository": repository,
                "base_sha": base_sha,
                "integration_tree_sha": integration_tree_sha,
                "merge_order": merge_order,
                "validation_snapshot_sha256": validation_hash,
                "validation": command_results,
                "status": status,
                "generated_at": now_iso(),
            }
            if manifest_path:
                atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            return manifest


class IntegrationQueue:
    """Serialize overlapping integration resources while allowing independent jobs."""
    def __init__(self, store: CoordinationStore) -> None:
        self.store = store

    @contextlib.contextmanager
    def claim(self, owner: str, exclusive_resources: list[str]):
        with contextlib.ExitStack() as stack:
            leases = [
                stack.enter_context(self.store.lease(
                    f"integration:{resource}", owner, mode="write",
                    ttl_seconds=3600, heartbeat_seconds=30,
                ))
                for resource in sorted(set(exclusive_resources))
            ]
            yield leases


def coordination_required(task_id: str) -> bool:
    td = task_dir(task_id)
    plan_path = td / "execution-plan.json"
    if plan_path.exists():
        plan = read_json(plan_path)
        if any(
            item.get("external_dependencies") or item.get("resource_accesses")
            for item in plan.get("slices", [])
        ):
            return True
    from .registries import RegistryService
    snapshot = RegistryService(CoordinationStore()).snapshot()
    if any(value.get("producer_task") == task_id or task_id in value.get("consumers", [])
           for value in snapshot["capabilities"].values()):
        return True
    return any(value.get("consumer_task") == task_id for value in snapshot["dependencies"].values())


def dependency_snapshot(task_id: str) -> dict[str, Any]:
    from .registries import RegistryService
    snapshot = RegistryService(CoordinationStore()).snapshot()
    return {
        name: {
            "version": value.get("version"),
            "fingerprint": value.get("contract_fingerprint"),
            "status": value.get("status"),
        }
        for name, value in snapshot["capabilities"].items()
        if task_id in value.get("consumers", [])
    }


def verify_integration_ready(task_id: str) -> None:
    if not coordination_required(task_id):
        return
    td = task_dir(task_id)
    task = read_yaml(td / "task.yaml")
    plan = read_json(td / "execution-plan.json")
    dependencies = dependency_snapshot(task_id)
    errors: list[str] = []
    for worktree in task.get("worktrees", []):
        if not worktree.get("writable", True):
            continue
        manifest_path = runtime_dir(task_id) / "integration" / f"{worktree['repo']}.json"
        if not manifest_path.exists():
            errors.append(f"{worktree['repo']}: integration manifest missing")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = safe_workspace_path(worktree["path"])
        current = integration_fingerprint(
            source, worktree.get("target_ref", worktree["base_ref"]),
            plan_version=int(plan.get("plan_version", 1)), dependency_versions=dependencies,
        )
        freshness = manifest_fresh(manifest, current)
        if manifest.get("status") != "MERGE_READY":
            errors.append(f"{worktree['repo']}: integration status is {manifest.get('status')}")
        elif not freshness["fresh"]:
            errors.append(f"{worktree['repo']}: integration manifest stale ({', '.join(freshness['changed'])})")
    if errors:
        raise SystemExit("Integration readiness gate failed:\n- " + "\n- ".join(errors))
