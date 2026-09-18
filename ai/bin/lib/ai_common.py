from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any
from functools import wraps

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing PyYAML. Run: pip install -r ai/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[3]
AI_ROOT = ROOT / "ai"
TASK_ID_RE = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")
CAPABILITY_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
DEFAULT_BASE_REF = "origin/master"

# Shared with run-codex-review's delta-safety check and request-fixes' correction-scope
# sidecar so both use the identical vocabulary for "this change is too sensitive to
# narrowly scope/delta-review".
SENSITIVE_CORRECTION_TERMS = (
    "auth", "security", "migration", "database", "transaction", "concurrency",
    "public api", "contract",
)


def detect_risk_categories(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({term for term in SENSITIVE_CORRECTION_TERMS if term in lowered})


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
        temp = Path(f.name)
    temp.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def task_dir(task_id: str) -> Path:
    validate_task_id(task_id)
    return AI_ROOT / "tasks" / task_id


def validate_task_id(task_id: str) -> None:
    if not TASK_ID_RE.fullmatch(task_id):
        raise SystemExit(f"Invalid Jira ID: {task_id}")


def task_transactional(function):
    """Serialize a task command even when its internal script is invoked directly."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        import contextlib
        import os
        import sys
        task_id = sys.argv[1] if len(sys.argv) > 1 else ""
        validate_task_id(task_id)
        if os.environ.get("AI_TASK_LOCK_OWNER") == task_id:
            return function(*args, **kwargs)
        from .coordination import CoordinationStore
        previous = os.environ.get("AI_TASK_LOCK_OWNER")
        store = CoordinationStore()
        with store.lock(f"task-state:{task_id}", timeout=30):
            os.environ["AI_TASK_LOCK_OWNER"] = task_id
            try:
                with contextlib.ExitStack() as leases:
                    command = Path(sys.argv[0]).name
                    write_commands = {"run-claude", "run-task", "validate"}
                    read_commands = {"run-codex-review", "finalize-task", "accept-task"}
                    task_path = task_dir(task_id) / "task.yaml"
                    if task_path.exists() and command in write_commands | read_commands:
                        task = read_yaml(task_path)
                        mode = "write" if command in write_commands else "read"
                        for item in sorted(task.get("worktrees", []), key=lambda value: value["path"]):
                            if mode == "write" and not item.get("writable", True):
                                continue
                            canonical = safe_workspace_path(item["path"]).resolve()
                            leases.enter_context(store.lease(
                                f"worktree:{canonical}", f"{task_id}:{command}", mode=mode,
                            ))
                        if mode == "write":
                            from .registries import RegistryService
                            registry = RegistryService(store)
                            registry.renew_task_claims(task_id)
                            registry.renew_task_resource_claims(task_id)
                            snapshot = registry.snapshot()
                            owned = [
                                value for value in snapshot["capabilities"].values()
                                if value.get("producer_task") == task_id and value.get("claim_lease_id")
                            ] + [
                                value for value in snapshot["resource_accesses"].values()
                                if value.get("task") == task_id and value.get("status") == "CLAIMED"
                                and value.get("lease_id")
                            ]
                            for claim in owned:
                                leases.enter_context(store.maintain_lease(
                                    claim.get("claim_lease_id", claim.get("lease_id")),
                                    claim.get("claim_fencing_token", claim.get("fencing_token")),
                                ))
                    return function(*args, **kwargs)
            finally:
                if previous is None:
                    os.environ.pop("AI_TASK_LOCK_OWNER", None)
                else:
                    os.environ["AI_TASK_LOCK_OWNER"] = previous
    return wrapped


def coordination_policy(task: dict[str, Any]) -> dict[str, Any]:
    """Return concurrency defaults without requiring legacy task files to migrate.

    Dynamic producer creation is intentionally opt-in: discovering a missing shared
    capability may always create a proposal, but creating a new task can broaden product
    scope and therefore requires an explicit task policy.
    """
    configured = task.get("coordination", {})
    return {
        "dynamic_producer": configured.get("dynamic_producer", "proposal_only"),
        "target_ref": configured.get("target_ref", DEFAULT_BASE_REF),
    }


def repository_identity(repo: Path, configured_name: str) -> str:
    """Canonical identity shared by all worktrees of one configured repository."""
    common_dir = git_value(repo, ["rev-parse", "--git-common-dir"])
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = repo / common_path
    canonical = common_path.resolve()
    digest = hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()[:16]
    return f"{configured_name}:{digest}"


def canonical_resource_id(repo_name: str, path: str, symbol: str | None = None) -> str:
    """Build a stable logical resource ID; reject absolute or escaping paths."""
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Resource path must be repository-relative: {path}")
    normalized = candidate.as_posix().lstrip("./")
    if not repo_name or not normalized:
        raise ValueError("Resource ID requires repository name and path")
    return f"{repo_name}:{normalized}" + (f"#{symbol}" if symbol else "")


def validate_capability_name(name: str) -> str:
    if not CAPABILITY_NAME_RE.fullmatch(name):
        raise ValueError(
            "Capability name must be a lowercase semantic namespace, for example user.create"
        )
    return name


def ensure_task(task_id: str) -> Path:
    p = task_dir(task_id)
    if not (p / "task.yaml").exists():
        raise SystemExit(f"Task not found: {p}")
    return p


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_status_records(repo: Path) -> list[tuple[str, str]]:
    """Parse `git status --porcelain=v1 -z --untracked-files=all` into (status, path) pairs,
    one per current worktree entry (a rename's original-path field is consumed and dropped,
    keeping only its destination path, matching what `git diff`/the worktree itself show)."""
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo, check=True, stdout=subprocess.PIPE,
    )
    records: list[tuple[str, str]] = []
    raw = result.stdout.split(b"\0")
    index = 0
    while index < len(raw):
        record = raw[index]
        index += 1
        if not record:
            continue
        text = record.decode("utf-8", errors="surrogateescape")
        status, path = text[:2], text[3:]
        if status[0] in {"R", "C"}:
            if index >= len(raw):
                raise ValueError("incomplete renamed-file record from git status")
            index += 1  # original path field; not part of the current worktree inventory
        records.append((status, path))
    return records


def git_worktree_paths(repo: Path) -> set[str]:
    """Every changed path in `repo`: tracked modifications plus untracked files, exactly as
    `git status --porcelain=v1 -z --untracked-files=all` reports them (a rename keeps only
    its destination path). Shared by check_handoff.py and dirty_worktree_hash() so both
    compute over the identical path set instead of two independent implementations that
    could silently drift apart.
    """
    return {path for _, path in _git_status_records(repo)}


def dirty_worktree_hash(repo: Path) -> str:
    """SHA-256 fingerprint of everything currently dirty in `repo`: the tracked diff against
    HEAD plus the content of every untracked file, sorted for a stable digest regardless of
    git's listing order. This task workflow never commits mid-task
    (enforce_global_git_policy blocks every git-write flag), so HEAD alone never moves while
    a task is in progress -- this hash is what actually changes when source does, and is the
    freshness signal validate/review/finalize compare against.
    """
    diff = subprocess.run(
        ["git", "diff", "HEAD"], cwd=repo, check=True, stdout=subprocess.PIPE,
    ).stdout
    untracked = sorted(path for status, path in _git_status_records(repo) if status == "??")
    h = hashlib.sha256()
    h.update(b"diff:\n")
    h.update(diff)
    h.update(b"\nuntracked:\n")
    for path in untracked:
        h.update(path.encode("utf-8", errors="surrogateescape"))
        h.update(b"\0")
        content = (repo / path).read_bytes() if (repo / path).is_file() else b""
        h.update(content)
        h.update(b"\0")
    return h.hexdigest()


def skill_manifest(skill_name: str) -> dict[str, Any]:
    """Hash every durable file in a project skill into one reproducible digest."""
    skill_dir = AI_ROOT / "skills" / skill_name
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"Required skill is missing: {skill_dir / 'SKILL.md'}")
    files: list[dict[str, str]] = []
    for path in sorted(item for item in skill_dir.rglob("*") if item.is_file()):
        if any(part == "__pycache__" for part in path.parts) or path.suffix == ".pyc":
            continue
        files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    aggregate = hashlib.sha256()
    for item in files:
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(item["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "path": f"ai/skills/{skill_name}/SKILL.md",
        "sha256": aggregate.hexdigest(),
        "files": files,
    }


def verify_locked_skills(context_lock: dict[str, Any]) -> None:
    changed = []
    for name, locked in context_lock.get("skills", {}).get("locked", {}).items():
        try:
            current = skill_manifest(name)
        except SystemExit:
            changed.append(name)
            continue
        if current["sha256"] != locked.get("sha256") or current["files"] != locked.get("files"):
            changed.append(name)
    if changed:
        raise SystemExit("Required skills changed after context lock; run prepare-context: " + ", ".join(changed))


def validate_applied_skills(
    task: dict[str, Any],
    context_lock: dict[str, Any],
    artifact: dict[str, Any],
    role: str,
) -> None:
    required = task.get("skills", {}).get(role, [])
    locked = context_lock.get("skills", {}).get("locked", {})
    applied = {item.get("name"): item for item in artifact.get("applied_skills", [])}
    missing = [name for name in required if name not in applied]
    stale = [
        name for name in required
        if name in applied and applied[name].get("sha256") != locked.get(name, {}).get("sha256")
    ]
    if missing or stale:
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if stale:
            details.append("stale=" + ",".join(stale))
        raise SystemExit(f"{role} artifact failed required-skill gate: " + "; ".join(details))


def run_delivery_quality_gates(
    task_id: str,
    implementation: dict[str, Any],
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute non-agent skill/evidence gates so report/accept cannot bypass review."""
    td = ensure_task(task_id)
    task = read_yaml(td / "task.yaml")
    context_lock = read_json(td / "context.lock.json")
    state = read_yaml(td / "state.yaml")
    if not context_lock.get("skills") and state.get("status") == "completed":
        result = {"task_id": task_id, "generated_at": now_iso(), "passed": True, "legacy_grandfathered": True, "checks": [], "failures": []}
        write_json(runtime_dir(task_id) / "validation" / "skills" / "delivery-gates.json", result)
        return result
    verify_locked_skills(context_lock)
    validate_applied_skills(task, context_lock, implementation, "implement")
    if review is not None:
        validate_applied_skills(task, context_lock, review, "review")

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    required = task.get("skills", {}).get("implement", [])
    checker_map = {
        "implement-nestjs-vertical-slice": ["check_port_bindings.py", "check_module_wiring.py"],
        "implement-nextjs-vertical-slice": ["check_frontend_security.py"],
        "implement-auth-security-change": ["check_auth_invariants.py"],
        "verify-openapi-contract": ["check_openapi_contract.py"],
    }
    for skill, script_names in checker_map.items():
        if skill not in required:
            continue
        for script_name in script_names:
            checker = AI_ROOT / "skills" / skill / "scripts" / script_name
            for item in task.get("worktrees", []):
                if skill == "verify-openapi-contract" and item.get("repo") != "backend":
                    continue
                result = run([__import__("sys").executable, str(checker), str(ROOT / item["path"])], cwd=ROOT, timeout=120)
                check = {"name": f"{skill}:{script_name}:{item['repo']}", "passed": result.returncode == 0, "output": result.stdout[-4000:]}
                checks.append(check)
                if not check["passed"]:
                    failures.append(check["name"])

    plan_path = td / "execution-plan.json"
    if task.get("scope", {}).get("execution_plan_required", False):
        plan = read_json(plan_path)
        handoff = {item.get("criterion"): item for item in implementation.get("acceptance_criteria", [])}
        missing = []
        for slice_item in plan.get("slices", []):
            slice_evidence = handoff.get(f"slice:{slice_item['id']}")
            for criterion in slice_item.get("acceptance_criteria", []):
                evidence = handoff.get(criterion) or slice_evidence
                if not evidence or evidence.get("status") != "passed" or not evidence.get("evidence"):
                    missing.append(criterion)
        checks.append({"name": "acceptance-evidence", "passed": not missing, "missing": missing})
        if missing:
            failures.append("acceptance-evidence")

    if "review-frontend-ui-fidelity" in task.get("skills", {}).get("review", []):
        fidelity_matrix = td / "evidence" / "fidelity-matrix.json"
        if fidelity_matrix.is_file():
            checker = AI_ROOT / "skills" / "review-frontend-ui-fidelity" / "scripts" / "check_fidelity_matrix.py"
            result = run(
                [__import__("sys").executable, str(checker), str(fidelity_matrix), "--require-all-passed"],
                cwd=ROOT,
                timeout=120,
            )
            check = {"name": "fidelity-matrix", "passed": result.returncode == 0, "output": result.stdout[-4000:]}
            checks.append(check)
            if not check["passed"]:
                failures.append(check["name"])

    if "review-vertical-slice-completeness" in task.get("skills", {}).get("review", []):
        checker = AI_ROOT / "skills" / "review-vertical-slice-completeness" / "scripts" / "check_evidence_freshness.py"
        backend = next((item for item in task.get("worktrees", []) if item.get("repo") == "backend"), None)
        if backend:
            result = run(
                [
                    __import__("sys").executable,
                    str(checker),
                    str(td / "implementation.json"),
                    str(ROOT / backend["path"]),
                    str(td / "evidence"),
                ],
                cwd=ROOT,
                timeout=120,
            )
            check = {"name": "evidence-freshness", "passed": result.returncode == 0, "output": result.stdout[-4000:]}
            checks.append(check)
            if not check["passed"]:
                failures.append("evidence-freshness")

    result = {"task_id": task_id, "generated_at": now_iso(), "passed": not failures, "checks": checks, "failures": failures}
    write_json(runtime_dir(task_id) / "validation" / "skills" / "delivery-gates.json", result)
    if failures:
        raise SystemExit("Delivery quality gates failed: " + ", ".join(failures))
    return result


def append_agent_metric(task_id: str, event: dict[str, Any]) -> None:
    path = runtime_dir(task_id) / "metrics" / "agent-attempts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def active_execution_slice(task_id: str) -> dict[str, Any] | None:
    """Return exactly one runnable slice, preferring the checkpoint selection."""
    td = ensure_task(task_id)
    task = read_yaml(td / "task.yaml")
    if not task.get("scope", {}).get("execution_plan_required", False):
        return None
    plan_path = td / "execution-plan.json"
    from .plan_reconciler import PlanReconciler
    from .coordination import CoordinationStore
    plan = PlanReconciler(CoordinationStore()).recover(plan_path)
    slices = plan.get("slices", [])
    by_id = {item["id"]: item for item in slices}
    # Import locally to keep the foundational helpers free of coordination import cycles.
    from .registries import RegistryService
    from .scheduler import schedule
    registry = RegistryService(CoordinationStore())
    registry.renew_task_claims(task_id)
    scheduling = schedule(
        plan, registry.snapshot(),
        active_resource_accesses=registry.active_resource_claims(exclude_task=task_id),
    )
    state_path = td / "state.yaml"
    state = read_yaml(state_path)
    state["dependency_state"] = scheduling["dependency_state"]
    state["dependency_blockers"] = scheduling["dependency_blockers"]
    write_yaml(state_path, state)
    runnable = set(scheduling["runnable_slices"])
    progress_path = td / "implementation-progress.json"
    selected = read_json(progress_path).get("current_slice") if progress_path.exists() else None
    if selected and selected in by_id and selected in runnable:
        return by_id[selected]
    for item in slices:
        if item["id"] in runnable:
            return item
    # A post-review correction happens after the plan is complete. The finding can be
    # in any slice, so the caller falls back to a full-plan scope instead of picking one.
    return None


def reconcile_execution_plan_evidence(task_id: str) -> list[str]:
    """Downgrade completed slices whose two required evidence records are absent.

    This repairs legacy/interrupted runs where an agent marked a plan slice completed
    before the orchestrator's quick-validation transition.
    """
    td = ensure_task(task_id)
    task = read_yaml(td / "task.yaml")
    plan_path = td / "execution-plan.json"
    if not task.get("scope", {}).get("execution_plan_required", False) or not plan_path.exists():
        return []
    progress_path = td / "implementation-progress.json"
    handoff_path = td / "implementation.json"
    progress = read_json(progress_path) if progress_path.exists() else {}
    handoff = read_json(handoff_path) if handoff_path.exists() else {}
    progress_keys = set(progress.get("completed_criteria", []))
    handoff_keys = {
        item.get("criterion") for item in handoff.get("acceptance_criteria", [])
        if item.get("status") == "passed" and item.get("evidence")
    }
    current_slice = progress.get("current_slice")
    plan = read_json(plan_path)
    repaired: list[str] = []
    for item in plan.get("slices", []):
        key = f"slice:{item.get('id')}"
        if item.get("status") == "completed" and (key not in progress_keys or key not in handoff_keys):
            item["status"] = "in_progress" if item.get("id") == current_slice else "pending"
            repaired.append(str(item.get("id")))
    if repaired:
        write_json(plan_path, plan)
    return repaired


def task_risk_level(task: dict[str, Any], context_lock: dict[str, Any]) -> str:
    """Choose economical reasoning unless the locked scope has material risk."""
    dimensions = set(context_lock.get("scope_assessment", {}).get("risk_dimensions", []))
    if dimensions & {"security", "database", "api", "background"}:
        return "high"
    if context_lock.get("scope_assessment", {}).get("large"):
        return "medium"
    return "low"


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def safe_workspace_path(raw: str) -> Path:
    p = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"Path escapes workspace: {raw}") from exc
    return p


def run(
    cmd: list[str] | str,
    cwd: Path,
    timeout: int | None = None,
    shell: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """`env`, when given, is merged over (not replacing) the current process environment --
    e.g. per-task allocated infra ports (see docker_infra.py) without touching a shared
    .env file. Omit it and the subprocess inherits the parent environment exactly as before.
    """
    import os

    merged_env = {**os.environ, **env} if env is not None else None
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        shell=shell,
        check=False,
        env=merged_env,
    )


def require_file(path: Path, purpose: str, next_step: str | None = None) -> Path:
    """Fail with an operator-friendly message instead of a raw traceback."""
    if path.is_file():
        return path
    message = f"Missing {purpose}: {path}"
    if next_step:
        message += f"\nNext: {next_step}"
    raise SystemExit(message)


def env_timeout_seconds(name: str, default: int) -> int:
    raw = __import__("os").environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive integer, found: {raw!r}") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be greater than zero, found: {value}")
    return value


def configured_fail_severities(task: dict[str, Any]) -> list[str]:
    allowed = ["blocker", "major", "minor", "note"]
    configured = task.get("review", {}).get("fail_on", ["blocker", "major"])
    if not isinstance(configured, list) or not configured:
        raise SystemExit("task.yaml review.fail_on must be a non-empty list")
    invalid = [value for value in configured if value not in allowed]
    if invalid:
        raise SystemExit(
            "task.yaml review.fail_on contains invalid severities: "
            + ", ".join(map(str, invalid))
        )
    return configured


def enforce_global_git_policy(task: dict[str, Any]) -> None:
    """Git write restrictions are global invariants, never per-task opt-ins."""
    legacy = task.get("git")
    if legacy is None:
        return
    enabled = [key for key, value in legacy.items() if bool(value)]
    if enabled:
        raise SystemExit(
            "Unsafe legacy task.yaml git flags are enabled: "
            + ", ".join(enabled)
            + ". Git writes, branch changes and worktree management cannot be enabled per task."
        )


def report_config(task: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "language": "vi",
        "include_diff_stat": True,
        "include_changed_files": True,
        "include_test_results": True,
        "include_review_findings": True,
        "include_knowledge_updates": True,
    }
    defaults.update(task.get("report", {}))
    if defaults["language"] not in {"vi", "en"}:
        raise SystemExit("task.yaml report.language must be 'vi' or 'en'")
    for key in defaults:
        if key == "language":
            continue
        if not isinstance(defaults[key], bool):
            raise SystemExit(f"task.yaml report.{key} must be true or false")
    return defaults


def git_value(cwd: Path, args: list[str], default: str = "unknown") -> str:
    result = run(["git", *args], cwd=cwd, timeout=30)
    return result.stdout.strip() if result.returncode == 0 else default


def update_state(
    task_id: str,
    status: str | None = None,
    timestamp_key: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    td = ensure_task(task_id)
    path = td / "state.yaml"
    state = read_yaml(path)
    if status:
        state["status"] = status
    if timestamp_key:
        state.setdefault("timestamps", {})[timestamp_key] = now_iso()
    state.update(extra)
    write_yaml(path, state)
    return state


def validate_json(path: Path, schema_path: Path) -> None:
    """Validate a JSON or YAML data file against a JSON Schema.

    The historical function name is retained so existing scripts remain compatible.
    """
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("Missing jsonschema. Run: pip install -r ai/requirements.txt") from exc
    data = read_yaml(path) if path.suffix.lower() in {".yaml", ".yml"} else read_json(path)
    jsonschema.validate(data, read_json(schema_path))


def runtime_dir(task_id: str) -> Path:
    p = ROOT / "worktrees" / task_id / ".ai"
    for name in ("input", "exchange", "validation", "metrics", "infra"):
        (p / name).mkdir(parents=True, exist_ok=True)
    return p


def change_dirs(td: Path) -> list[Path]:
    changes = td / "changes"
    if not changes.exists():
        return []
    return sorted(p for p in changes.glob("cycle-*") if p.is_dir())


def requirement_documents(
    task_id: str,
    include_user_request: bool = True,
    audit: bool = False,
) -> list[str]:
    """Canonical effective-requirements resolver, shared by run-claude, run-codex-review,
    prepare-plan and prepare-context so they always see the same active requirement set.

    Default (audit=False): the ACTIVE/effective set — task.md plus only the addenda from
    cycles strictly after `requirements_consolidated_through_cycle` (state.yaml). Cycles at
    or below that mark are already folded into task.md by apply-requirements-consolidation,
    so their addenda are excluded here to avoid re-reading settled history (and, in
    prepare-plan, to avoid generating duplicate acceptance-criteria slices for content that
    now also exists in task.md).

    audit=True is an explicit opt-in for historical/report views (finalize-task) that must
    always list the complete requirement history regardless of consolidation progress.
    """
    td = ensure_task(task_id)
    docs = [relative_to_root(td / "task.md")]
    consolidated_through = 0
    if not audit:
        state = read_yaml(td / "state.yaml")
        consolidated_through = int(state.get("requirements_consolidated_through_cycle", 0) or 0)
    for cycle in change_dirs(td):
        if not audit and int(cycle.name.rsplit("-", 1)[-1]) <= consolidated_through:
            continue
        addendum = cycle / "requirement-addendum.md"
        request = cycle / "user-request.md"
        if addendum.exists():
            docs.append(relative_to_root(addendum))
        if include_user_request and request.exists():
            docs.append(relative_to_root(request))
    return docs


def verify_registered_worktrees(
    task_id: str,
    require_same_branch: bool = True,
) -> list[dict[str, str]]:
    td = ensure_task(task_id)
    task = read_yaml(td / "task.yaml")
    state = read_yaml(td / "state.yaml")
    known = state.get("repositories", {})
    verified: list[dict[str, str]] = []
    errors: list[str] = []

    for wt in task.get("worktrees", []):
        path = safe_workspace_path(wt["path"])
        if not path.exists():
            errors.append(f"Missing worktree: {wt['path']}")
            continue
        if git_value(path, ["rev-parse", "--is-inside-work-tree"], "false") != "true":
            errors.append(f"Not a Git worktree: {wt['path']}")
            continue

        branch = git_value(path, ["branch", "--show-current"])
        expected = (
            known.get(wt["repo"], {}).get("registered_branch")
            or known.get(wt["repo"], {}).get("branch")
        )
        if (
            require_same_branch
            and expected not in (None, "", "unknown", "missing")
            and branch != expected
        ):
            errors.append(
                f"Branch changed for {wt['repo']}: expected {expected}, found {branch}"
            )
        verified.append(
            {
                "repo": wt["repo"],
                "path": wt["path"],
                "branch": branch,
                "head_sha": git_value(path, ["rev-parse", "HEAD"]),
            }
        )

    if errors:
        raise SystemExit(
            "Registered worktree verification failed:\n- " + "\n- ".join(errors)
        )
    return verified


def archive_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
