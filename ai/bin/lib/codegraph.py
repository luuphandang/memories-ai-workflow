from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


VALID_MODES = {"off", "optional", "required"}

# codegraph's own MCP setup docs wire `serve --mcp` with no path-like argument
# (README's manual-config example is `{"command":"codegraph","args":["serve","--mcp"]}`),
# and the CLI reference has no documented `--path`/project flag for any command.
# The only way to scope a `serve --mcp` process to one worktree is therefore its
# process cwd, so per-repository servers are launched through this tiny wrapper
# instead of a `--path` flag that may not exist.
SERVE_WRAPPER = Path(__file__).resolve().parent / "codegraph_serve.py"


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
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        # subprocess.run raises this regardless of check=False, so without this
        # catch a slow/hung `codegraph` call crashes prepare-context/manage-codegraph
        # even in optional mode, which must never fail the workflow on its own.
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        output += f"\n[codegraph] timed out after {timeout}s"
        return subprocess.CompletedProcess(command, returncode=124, stdout=output)


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

    # The official CLI reference only documents `codegraph status [path]`, with no
    # `--json` flag, so this must not depend on `--json` being supported: request
    # plain output and best-effort parse it as JSON in case the CLI does emit it.
    status = _run([binary, "status", str(path)], cwd=path)
    if status.returncode != 0:
        result["reason"] = f"codegraph status exited {status.returncode}"
        if configured_mode == "required":
            raise SystemExit(f"{result['reason']} for {path}:\n{status.stdout}")
        return result
    result["status_text"] = status.stdout.strip()
    try:
        result["status"] = json.loads(status.stdout)
    except json.JSONDecodeError:
        pass
    result["ready"] = True
    result.pop("reason", None)
    return result


def inspect_task_repositories(root: Path, task: dict, *, sync: bool = False, initialize: bool = False) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    resolved_root = root.resolve()
    for item in task.get("worktrees", []):
        path = (root / item["path"]).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError:
            raise SystemExit(f"CodeGraph repository path escapes workspace: {item['path']}")
        result[item["repo"]] = inspect_repository(path, sync=sync, initialize=initialize)
    return result


def ready_repositories(context_lock: dict) -> list[tuple[str, str]]:
    graph = context_lock.get("codegraph", {}).get("repositories", {})
    repositories = context_lock.get("repositories", {})
    return [
        (name, repositories[name]["path"])
        for name, details in graph.items()
        if details.get("ready") and name in repositories
    ]


def runtime_ready_repositories(root: Path, context_lock: dict) -> list[tuple[str, str]]:
    # Re-check the *current* mode, not just the mode recorded at lock time: if an
    # operator sets AI_CODEGRAPH_MODE=off after prepare-context without re-locking,
    # a stale lock with ready:true repositories must not still connect MCP servers.
    if mode() == "off":
        return []
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


def _safe_repo_name(name: str) -> str:
    return "codegraph_" + "".join(ch if ch.isalnum() else "_" for ch in name)


def _named_ready_repositories(root: Path, context_lock: dict) -> list[tuple[str, str, str]]:
    """Ready repositories paired with their sanitized MCP server name.

    Raises if two distinct repository names normalize to the same server name
    (e.g. "backend-api" and "backend_api"), which would otherwise silently drop
    or overwrite one repository's MCP server.
    """
    seen: dict[str, str] = {}
    named: list[tuple[str, str, str]] = []
    for name, relative_path in runtime_ready_repositories(root, context_lock):
        safe_name = _safe_repo_name(name)
        if safe_name in seen and seen[safe_name] != name:
            raise SystemExit(
                f"CodeGraph repository names {seen[safe_name]!r} and {name!r} both "
                f"normalize to MCP server {safe_name!r}; rename one repository to "
                "avoid a silent MCP server collision"
            )
        seen[safe_name] = name
        named.append((safe_name, name, relative_path))
    return named


def _serve_command_args(root: Path, binary: str, relative_path: str) -> tuple[str, list[str]]:
    """Build the (command, args) that scope `codegraph serve --mcp` to one worktree.

    Neither Claude Code's --mcp-config schema (stdio servers: command/args/env
    only) nor the CodeGraph CLI reference document a way to pass a project path
    to `serve`; its own manual-setup example is `serve --mcp` with no path
    argument. The only documented scoping mechanism for CodeGraph in general is
    running commands with the worktree as cwd, so the server is spawned through
    a wrapper that chdirs into the worktree before exec'ing `codegraph`.
    """
    return sys.executable, [str(SERVE_WRAPPER), str(root / relative_path), binary, "serve", "--mcp"]


def claude_mcp_config(root: Path, context_lock: dict) -> dict[str, Any]:
    binary = executable() or os.environ.get("CODEGRAPH_COMMAND", "codegraph")
    servers = {}
    for safe_name, _name, relative_path in _named_ready_repositories(root, context_lock):
        command, args = _serve_command_args(root, binary, relative_path)
        servers[safe_name] = {"type": "stdio", "command": command, "args": args}
    return {"mcpServers": servers}


def codex_mcp_overrides(root: Path, context_lock: dict) -> list[str]:
    binary = executable() or os.environ.get("CODEGRAPH_COMMAND", "codegraph")
    overrides: list[str] = []
    for safe_name, _name, relative_path in _named_ready_repositories(root, context_lock):
        command, args = _serve_command_args(root, binary, relative_path)
        overrides.extend(["-c", f"mcp_servers.{safe_name}.command={json.dumps(command)}"])
        overrides.extend(["-c", f"mcp_servers.{safe_name}.args={json.dumps(args)}"])
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
