from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

import yaml

from lib.ai_common import AI_ROOT, ROOT, now_iso, read_json, read_yaml, sha256_file, write_json

REGISTRY_PATH = AI_ROOT / "runtime" / "locks" / "docker-infra-registry.json"
LOCKS_DIR = AI_ROOT / "runtime" / "locks"

# Service names as declared in apps/backend/docker/docker-compose.yml's `infrastructure`
# profile. Kept explicit (not derived generically) since the health checks below are
# specific to what each of these three actually is.
REQUIRED_INFRA_SERVICES = ("postgres", "redis", "minio", "minio-init")
EXPECTED_MINIO_BUCKETS = ("temporary-uploads", "private-originals", "processed-assets", "public-assets")

# `minio/mc:latest` was removed from Docker Hub ("repository does not exist" on pull as of
# 2026-09) -- minio now publishes the same client under quay.io. Patched only in ai/'s
# generated per-task compose file; apps/backend/docker/docker-compose.yml itself is untouched
# since fixing the app's own compose file is outside this workflow's scope, but it has the
# same dead reference and will hit this identically if that stack is ever rebuilt from
# scratch (it happened to still be running from before the image disappeared upstream).
DEAD_IMAGE_REPLACEMENTS = {
    "minio/mc:latest": "quay.io/minio/mc:latest",
}


# ---------------------------------------------------------------------------
# Port allocation
# ---------------------------------------------------------------------------

def allocate_free_ports(count: int) -> list[int]:
    """Real free ports on 127.0.0.1, scanned at call time (never derived from a formula) so
    this never collides with whatever else happens to be running on the machine -- including
    processes entirely unrelated to this workflow. All sockets are held open until every port
    in the batch is chosen, then closed together, to shrink (not eliminate) the release/reuse
    race against a concurrent allocator.
    """
    sockets = []
    try:
        for _ in range(count):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", 0))
            sockets.append(s)
        return [s.getsockname()[1] for s in sockets]
    finally:
        for s in sockets:
            s.close()


# ---------------------------------------------------------------------------
# Compose generation
# ---------------------------------------------------------------------------

def _infra_dir(task_id: str) -> Path:
    """Path only -- no mkdir side effect. Use ai_common.runtime_dir() instead when actively
    provisioning; this is for read/teardown paths that must not resurrect a torn-down task's
    worktree directory structure."""
    return ROOT / "worktrees" / task_id / ".ai" / "infra"


def generate_compose(task_id: str, source_compose: Path, output_path: Path) -> dict:
    """Derive a standalone, task-scoped compose file from the real
    apps/backend/docker/docker-compose.yml's `infrastructure` profile: unique project name,
    unique volume names, freshly allocated host ports (container ports unchanged). A
    standalone file, not a layered override (see memories-docker-infra-port-conflicts) --
    each task's stack is fully independent, nothing to merge.
    """
    data = yaml.safe_load(source_compose.read_text(encoding="utf-8"))
    all_services = data.get("services", {})
    infra_names = [
        name for name, spec in all_services.items()
        if "infrastructure" in (spec.get("profiles") or [])
    ]
    missing = [name for name in REQUIRED_INFRA_SERVICES if name not in infra_names]
    if missing:
        raise SystemExit(
            f"{source_compose} infrastructure profile is missing expected service(s): {missing} "
            "-- docker_infra.py's generator assumes this exact shape and needs updating if it changed."
        )

    safe_task = task_id.lower().replace("_", "-")
    project_name = f"memories-backend-{safe_task}"

    declared_volumes = set(data.get("volumes") or {})
    kept_volume_names: set[str] = set()
    services_out: dict[str, dict] = {}
    for name in infra_names:
        spec = json.loads(json.dumps(all_services[name]))  # cheap deep copy
        spec.pop("profiles", None)
        if spec.get("image") in DEAD_IMAGE_REPLACEMENTS:
            spec["image"] = DEAD_IMAGE_REPLACEMENTS[spec["image"]]
        for vol in spec.get("volumes") or []:
            if isinstance(vol, str) and ":" in vol and vol.split(":", 1)[0] in declared_volumes:
                kept_volume_names.add(vol.split(":", 1)[0])
        services_out[name] = spec

    volume_rename = {name: f"{safe_task}_{name}" for name in kept_volume_names}
    for spec in services_out.values():
        if "volumes" not in spec:
            continue
        renamed = []
        for vol in spec["volumes"]:
            if isinstance(vol, str) and ":" in vol:
                source, rest = vol.split(":", 1)
                vol = f"{volume_rename[source]}:{rest}" if source in volume_rename else vol
            renamed.append(vol)
        spec["volumes"] = renamed

    ports_needed = {"postgres": 1, "redis": 1, "minio": 2}
    allocated = iter(allocate_free_ports(sum(ports_needed.values())))
    port_map = {
        "postgres": next(allocated),
        "redis": next(allocated),
        "minio_api": next(allocated),
        "minio_console": next(allocated),
    }

    def remap(service_name: str, new_ports: list[int]) -> None:
        spec = services_out[service_name]
        original = spec.get("ports") or []
        spec["ports"] = [
            f"{new_port}:{str(entry).split(':')[-1]}"
            for entry, new_port in zip(original, new_ports)
        ]

    remap("postgres", [port_map["postgres"]])
    remap("redis", [port_map["redis"]])
    remap("minio", [port_map["minio_api"], port_map["minio_console"]])

    output_data = {
        "name": project_name,
        "services": services_out,
        "volumes": {volume_rename[name]: {} for name in kept_volume_names},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(output_data, sort_keys=False), encoding="utf-8")

    return {
        "task_id": task_id,
        "project_name": project_name,
        "compose_path": str(output_path),
        "ports": port_map,
        "volumes": sorted(volume_rename.values()),
        "source_compose_sha256": sha256_file(source_compose),
        "generated_at": now_iso(),
    }


def infra_env_for_manifest(manifest: dict) -> dict[str, str]:
    """Process-environment overrides that make the backend connect to this task's isolated
    stack -- never written to apps/backend/.env (dotenv doesn't override already-set
    process.env keys, so this alone is sufficient; see configuration.module.ts)."""
    ports = manifest["ports"]
    return {
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": str(ports["postgres"]),
        "REDIS_HOST": "localhost",
        "REDIS_PORT": str(ports["redis"]),
        "BULLMQ_REDIS_HOST": "localhost",
        "BULLMQ_REDIS_PORT": str(ports["redis"]),
        "S3_ENDPOINT": f"http://localhost:{ports['minio_api']}",
    }


# ---------------------------------------------------------------------------
# docker compose invocation helpers
# ---------------------------------------------------------------------------

def _compose_base_cmd(compose_path: Path, project_name: str) -> list[str]:
    return ["docker", "compose", "-f", str(compose_path), "-p", project_name]


def _parse_compose_ps(output: str) -> list[dict]:
    output = output.strip()
    if not output:
        return []
    try:
        data = json.loads(output)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [json.loads(line) for line in output.splitlines() if line.strip()]


def _wait_healthy(compose_path: Path, project_name: str, service_names: list[str], timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    states: dict[str, str] = {}
    while time.monotonic() < deadline:
        result = subprocess.run(
            [*_compose_base_cmd(compose_path, project_name), "ps", "--format", "json"],
            capture_output=True, text=True, check=False,
        )
        rows = _parse_compose_ps(result.stdout)
        states = {row.get("Service"): row.get("Health", "") for row in rows}
        if all(states.get(name) == "healthy" for name in service_names):
            return
        time.sleep(2)
    raise SystemExit(f"Infra containers did not become healthy within {timeout}s: {states}")


def _health_check(manifest: dict) -> list[str]:
    """Beyond "container running": migrations actually applied, Redis actually answers,
    every required MinIO bucket actually exists."""
    problems: list[str] = []
    compose_path = Path(manifest["compose_path"])
    base = _compose_base_cmd(compose_path, manifest["project_name"])

    pg = subprocess.run(
        [*base, "exec", "-T", "postgres", "psql", "-U", "memories", "-d", "memories", "-tAc", "SELECT count(*) FROM migrations"],
        capture_output=True, text=True,
    )
    if pg.returncode != 0:
        problems.append(f"postgres: migrations query failed: {(pg.stdout + pg.stderr).strip()}")
    else:
        try:
            if int(pg.stdout.strip()) <= 0:
                problems.append("postgres: migrations table has no applied migrations")
        except ValueError:
            problems.append(f"postgres: unexpected migrations-count output: {pg.stdout.strip()!r}")

    redis_check = subprocess.run([*base, "exec", "-T", "redis", "redis-cli", "ping"], capture_output=True, text=True)
    if redis_check.returncode != 0 or "PONG" not in redis_check.stdout:
        problems.append(f"redis: ping failed: {(redis_check.stdout + redis_check.stderr).strip()}")

    minio_check = subprocess.run(
        [*base, "run", "--rm", "minio-init", "sh", "-c",
         "mc alias set local http://minio:9000 minioadmin minioadmin >/dev/null && mc ls local"],
        capture_output=True, text=True,
    )
    found = {bucket for bucket in EXPECTED_MINIO_BUCKETS if bucket in minio_check.stdout}
    if minio_check.returncode != 0 or found != set(EXPECTED_MINIO_BUCKETS):
        missing = sorted(set(EXPECTED_MINIO_BUCKETS) - found)
        problems.append(f"minio: missing bucket(s) {missing}: {(minio_check.stdout + minio_check.stderr).strip()}")

    return problems


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def _registry_read() -> dict:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        return read_json(REGISTRY_PATH)
    except (json.JSONDecodeError, OSError):
        return {}


def _registry_write(registry: dict) -> None:
    write_json(REGISTRY_PATH, registry)


# ---------------------------------------------------------------------------
# Public lifecycle: up / status / down / gc
# ---------------------------------------------------------------------------

def ensure_infra_up(task_id: str, repo_path: Path) -> dict:
    """Idempotent: reuses an existing healthy per-task stack; regenerates (fresh ports) if
    missing or unhealthy. Runs `migration:run` once right after containers become healthy --
    each task's database is a fresh empty volume now, not a shared already-migrated
    throwaway, so this can no longer be left to the caller to remember."""
    from lib.ai_common import runtime_dir  # local import: avoid import cycle at module load

    infra_dir = runtime_dir(task_id) / "infra"
    manifest_path = infra_dir / "manifest.json"
    compose_path = infra_dir / "docker-compose.generated.yml"

    registry = _registry_read()
    if task_id in registry and manifest_path.is_file() and compose_path.is_file():
        manifest = read_json(manifest_path)
        if not _health_check(manifest):
            registry[task_id]["last_used_at"] = now_iso()
            _registry_write(registry)
            return manifest
        teardown_infra(task_id, quiet=True)
        registry = _registry_read()

    source_compose = repo_path / "docker" / "docker-compose.yml"
    manifest = generate_compose(task_id, source_compose, compose_path)
    write_json(manifest_path, manifest)

    up = subprocess.run(
        [*_compose_base_cmd(compose_path, manifest["project_name"]), "up", "-d"],
        cwd=repo_path, capture_output=True, text=True,
    )
    if up.returncode != 0:
        raise SystemExit(f"docker compose up failed for task {task_id}:\n{up.stdout}\n{up.stderr}")

    _wait_healthy(compose_path, manifest["project_name"], ["postgres", "redis", "minio"])

    migration = subprocess.run(
        ["npm", "run", "migration:run"], cwd=repo_path,
        env={**os.environ, **infra_env_for_manifest(manifest)},
        capture_output=True, text=True,
    )
    if migration.returncode != 0:
        raise SystemExit(
            f"Initial migration:run failed for task {task_id} against its fresh infra:\n"
            f"{migration.stdout[-4000:]}\n{migration.stderr[-2000:]}"
        )

    problems = _health_check(manifest)
    if problems:
        raise SystemExit("Infra health check failed after startup:\n- " + "\n- ".join(problems))

    registry[task_id] = {
        "project_name": manifest["project_name"],
        "compose_path": str(compose_path),
        "ports": manifest["ports"],
        "created_at": manifest["generated_at"],
        "last_used_at": now_iso(),
    }
    _registry_write(registry)
    return manifest


def status_infra(task_id: str) -> dict:
    registry = _registry_read()
    entry = registry.get(task_id)
    if not entry:
        return {"task_id": task_id, "running": False}
    manifest_path = _infra_dir(task_id) / "manifest.json"
    if not manifest_path.is_file():
        return {"task_id": task_id, "running": True, "healthy": False, "problems": ["manifest.json missing"]}
    manifest = read_json(manifest_path)
    problems = _health_check(manifest)
    return {"task_id": task_id, "running": True, "healthy": not problems, "problems": problems, "manifest": manifest}


def teardown_infra(task_id: str, quiet: bool = False) -> None:
    registry = _registry_read()
    entry = registry.get(task_id)
    infra_dir = _infra_dir(task_id)
    compose_path = infra_dir / "docker-compose.generated.yml"
    project_name = (entry or {}).get("project_name")
    if project_name and compose_path.is_file():
        result = subprocess.run(
            [*_compose_base_cmd(compose_path, project_name), "down", "-v"],
            capture_output=True, text=True,
        )
        if result.returncode != 0 and not quiet:
            print(f"Warning: docker compose down failed for {task_id}: {result.stdout}\n{result.stderr}")
    if task_id in registry:
        del registry[task_id]
        _registry_write(registry)
    if infra_dir.exists():
        shutil.rmtree(infra_dir, ignore_errors=True)


def _should_reclaim(task_id: str, entry: dict, max_age_hours: int) -> bool:
    state_path = AI_ROOT / "tasks" / task_id / "state.yaml"
    if not state_path.is_file():
        return True
    state = read_yaml(state_path)
    if state.get("status") == "completed":
        return True
    last_used = entry.get("last_used_at")
    if not last_used:
        return True
    try:
        last_used_dt = datetime.fromisoformat(last_used)
    except ValueError:
        return True
    age_hours = (datetime.now(timezone.utc).astimezone() - last_used_dt).total_seconds() / 3600
    return age_hours > max_age_hours


def infra_gc(max_age_hours: int = 48, best_effort: bool = False) -> list[str]:
    cleaned: list[str] = []
    registry = _registry_read()
    for task_id in list(registry.keys()):
        try:
            if _should_reclaim(task_id, registry[task_id], max_age_hours):
                teardown_infra(task_id, quiet=True)
                cleaned.append(task_id)
        except Exception:
            if not best_effort:
                raise
    return cleaned


# ---------------------------------------------------------------------------
# Resource scheduler: cap concurrent heavy (infra-dependent) validation runs within ai/
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def acquire_heavy_validation_slot(timeout: int = 600):
    """Simple counting semaphore over N fixed lock files -- caps how many ai/-managed tasks
    run e2e/migration validation at once, so they don't starve each other's I/O/CPU. Makes
    no claim about, and cannot control, unrelated processes on the same machine."""
    max_slots = int(os.environ.get("AI_MAX_CONCURRENT_HEAVY_VALIDATION", "2"))
    deadline = time.monotonic() + timeout
    handle = None
    slot = None
    while time.monotonic() < deadline and handle is None:
        for index in range(max_slots):
            path = LOCKS_DIR / f"heavy-validation-{index}.lock"
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = path.open("w")
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle, slot = fh, index
                break
            except OSError:
                fh.close()
        if handle is None:
            time.sleep(5)
    if handle is None:
        raise SystemExit(f"Timed out after {timeout}s waiting for a heavy-validation slot (max {max_slots} concurrent)")
    try:
        yield slot
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
