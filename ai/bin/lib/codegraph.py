from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


VALID_MODES = {"off", "optional", "required"}


def mode() -> str:
    value = os.environ.get("AI_CODEGRAPH_MODE", "optional").strip().lower()
    if value not in VALID_MODES:
        raise SystemExit(
            f"Invalid AI_CODEGRAPH_MODE={value!r}; expected off, optional, or required"
        )
    return value


def executable() -> str | None:
    return shutil.which(os.environ.get("CODEGRAPH_COMMAND", "codegraph"))


def _run(command: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def inspect_repository(path: Path, *, sync: bool = False, initialize: bool = False) -> dict[str, Any]:
    configured_mode = mode()
    result: dict[str, Any] = {
        "mode": configured_mode,
        "path": str(path),
        "available": False,
        "indexed": (path / ".codegraph").is_dir(),
        "ready": False,
    }
    if configured_mode == "off":
        result["reason"] = "disabled"
        return result
    if not path.is_dir():
        result["reason"] = "repository path does not exist"
        if configured_mode == "required":
            raise SystemExit(f"CodeGraph repository path does not exist: {path}")
        return result

    binary = executable()
    if not binary:
        result["reason"] = "codegraph command is not available on PATH"
        if configured_mode == "required":
            raise SystemExit(result["reason"])
        return result
    result["available"] = True
    result["command"] = binary

    if initialize and not result["indexed"]:
        init = _run([binary, "init", str(path)], cwd=path, timeout=1800)
        result["init_output"] = init.stdout.strip()
        if init.returncode != 0:
            result["reason"] = f"codegraph init exited {init.returncode}"
            if configured_mode == "required":
                raise SystemExit(f"{result['reason']} for {path}:\n{init.stdout}")
            return result
        result["indexed"] = (path / ".codegraph").is_dir()

    if not result["indexed"]:
        result["reason"] = "index is missing; run ai task codegraph <ID> --init"
        if configured_mode == "required":
            raise SystemExit(f"CodeGraph index is required for {path}; {result['reason']}")
        return result

    if sync:
        synced = _run([binary, "sync", str(path), "--quiet"], cwd=path, timeout=1800)
        if synced.returncode != 0:
            result["reason"] = f"codegraph sync exited {synced.returncode}"
            if configured_mode == "required":
                raise SystemExit(f"{result['reason']} for {path}:\n{synced.stdout}")
            return result

    status = _run([binary, "status", str(path), "--json"], cwd=path)
    if status.returncode != 0:
        result["reason"] = f"codegraph status exited {status.returncode}"
        if configured_mode == "required":
            raise SystemExit(f"{result['reason']} for {path}:\n{status.stdout}")
        return result
    try:
        result["status"] = json.loads(status.stdout)
    except json.JSONDecodeError:
        result["status_text"] = status.stdout.strip()
    result["ready"] = True
    result.pop("reason", None)
    return result


def inspect_task_repositories(root: Path, task: dict, *, sync: bool = False, initialize: bool = False) -> dict[str, dict[str, Any]]:
    return {
        item["repo"]: inspect_repository(
            root / item["path"], sync=sync, initialize=initialize
        )
        for item in task.get("worktrees", [])
    }


def ready_repositories(context_lock: dict) -> list[tuple[str, str]]:
    graph = context_lock.get("codegraph", {}).get("repositories", {})
    repositories = context_lock.get("repositories", {})
    return [
        (name, repositories[name]["path"])
        for name, details in graph.items()
        if details.get("ready") and name in repositories
    ]


def runtime_ready_repositories(root: Path, context_lock: dict) -> list[tuple[str, str]]:
    ready = ready_repositories(context_lock)
    binary = executable()
    live = [item for item in ready if (root / item[1] / ".codegraph").is_dir()]
    expected_count = len(context_lock.get("repositories", {}))
    if mode() == "required" and (
        not binary or len(ready) != expected_count or len(live) != len(ready)
    ):
        raise SystemExit(
            "CodeGraph became unavailable after context locking; restore the CLI/index "
            "and run prepare-context again"
        )
    return live if binary else []


def claude_mcp_config(root: Path, context_lock: dict) -> dict[str, Any]:
    binary = executable() or os.environ.get("CODEGRAPH_COMMAND", "codegraph")
    servers = {}
    for name, relative_path in runtime_ready_repositories(root, context_lock):
        safe_name = "codegraph_" + "".join(ch if ch.isalnum() else "_" for ch in name)
        servers[safe_name] = {
            "type": "stdio",
            "command": binary,
            "args": ["serve", "--mcp", "--path", str(root / relative_path)],
        }
    return {"mcpServers": servers}


def codex_mcp_overrides(root: Path, context_lock: dict) -> list[str]:
    binary = executable() or os.environ.get("CODEGRAPH_COMMAND", "codegraph")
    overrides: list[str] = []
    for name, relative_path in runtime_ready_repositories(root, context_lock):
        safe_name = "codegraph_" + "".join(ch if ch.isalnum() else "_" for ch in name)
        args = json.dumps(["serve", "--mcp", "--path", str(root / relative_path)])
        overrides.extend(["-c", f"mcp_servers.{safe_name}.command={json.dumps(binary)}"])
        overrides.extend(["-c", f"mcp_servers.{safe_name}.args={args}"])
    return overrides


def prompt_guidance(root: Path, context_lock: dict) -> str:
    ready = runtime_ready_repositories(root, context_lock)
    if not ready:
        return "CodeGraph is unavailable for this task; use normal repository discovery tools."
    mapping = ", ".join(f"{name}={path}" for name, path in ready)
    return (
        "CodeGraph is ready (" + mapping + "). For architecture, symbol flow, callers, "
        "callees, and impact analysis, query the matching codegraph_<repo> MCP server first. "
        "Use grep/read only to verify live edits, non-code files, or gaps reported by CodeGraph."
    )
