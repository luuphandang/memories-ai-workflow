#!/usr/bin/env python3
"""End-to-end coverage that request-fixes' correction-scope sidecar actually narrows
run-claude's post-review-correction scope, preserves unaffected slice evidence, and
that a sensitive finding escalates to full-plan scope despite being mappable.

See smoke_pipeline.py's docstring/create_hierarchy note on why this only creates one
task hierarchy per process (in-process runpy caches lib.ai_common's ROOT/AI_ROOT).
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TEST-1002"

SLICES = [
    {
        "id": "slice-a", "title": "Slice A", "depends_on": [],
        "acceptance_criteria": ["AC-A"], "requirement_details": {"AC-A": ["Do A"]},
        "deliverables": ["libs/foo/a.ts"], "tests": ["a tests"], "validation": ["a validation"],
        "status": "pending",
    },
    {
        "id": "slice-b", "title": "Slice B", "depends_on": [],
        "acceptance_criteria": ["AC-B"], "requirement_details": {"AC-B": ["Do B"]},
        "deliverables": ["libs/bar/b.ts"], "tests": ["b tests"], "validation": ["b validation"],
        "status": "pending",
    },
]


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline_correction_scope", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def command(root: Path, args: list[str], env: dict, expected: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=root, env={**os.environ, **env}, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60,
    )
    if expected is not None and result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {' '.join(args)}\n{result.stdout}")
    return result


def snapshot(task_dir: Path, worktree_ai_dir: Path, backup_root: Path) -> None:
    shutil.copytree(task_dir, backup_root / "task")
    shutil.copytree(worktree_ai_dir, backup_root / "worktree_ai")


def restore(task_dir: Path, worktree_ai_dir: Path, backup_root: Path) -> None:
    shutil.rmtree(task_dir)
    shutil.copytree(backup_root / "task", task_dir)
    shutil.rmtree(worktree_ai_dir)
    shutil.copytree(backup_root / "worktree_ai", worktree_ai_dir)


def write_two_slice_plan(task_dir: Path) -> None:
    plan = json.loads((task_dir / "execution-plan.json").read_text(encoding="utf-8"))
    plan["status"] = "ready"
    plan["slices"] = [dict(item) for item in SLICES]
    (task_dir / "execution-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-correction-scope-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()
        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)
        write_two_slice_plan(task_dir)
        worktree_ai_dir = root / "worktrees" / TASK_ID / ".ai"

        ai = root / "ai" / "bin" / "ai"
        fake_claude = root / "ai" / "tests" / "fakes" / "fake_claude.py"
        fake_codex = root / "ai" / "tests" / "fakes" / "fake_codex.py"
        fake_claude.chmod(0o755)
        fake_codex.chmod(0o755)
        base_env = {
            "CLAUDE_COMMAND": str(fake_claude),
            "CODEX_COMMAND": str(fake_codex),
            "CLAUDE_TIMEOUT_SECONDS": "30",
            "CODEX_TIMEOUT_SECONDS": "30",
            "FAKE_CLAUDE_MODE": "success",
            "FAKE_CODEX_CHANGES_ONCE": "1",
        }

        backup_root = Path(tmp) / "backup"
        backup_root.mkdir()
        snapshot(task_dir, worktree_ai_dir, backup_root)

        # --- Scenario: finding maps cleanly to slice-a; slice-b's evidence must survive.
        env = {**base_env, "FAKE_CODEX_FINDING_FILE": "libs/foo/a.ts", "FAKE_CODEX_FINDING_TITLE": "Bug in A"}
        command(root, [str(ai), "task", "run", TASK_ID, "--max-attempts", "6"], env, expected=0)

        sidecar = json.loads((worktree_ai_dir / "input" / "correction-scope-review-001.json").read_text(encoding="utf-8"))
        assert sidecar["impacted_slices"] == ["slice-a"], sidecar
        assert sidecar["full_plan_fallback_required"] is False, sidecar

        state = yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
        assert state["last_correction_implementation_scope"]["mode"] == "slices", state["last_correction_implementation_scope"]
        assert state["last_correction_implementation_scope"]["slices"] == ["slice-a"]

        implementation = json.loads((task_dir / "implementation.json").read_text(encoding="utf-8"))
        by_criterion = {item["criterion"]: item for item in implementation["acceptance_criteria"]}
        assert by_criterion["slice:slice-a"]["status"] == "passed"
        assert by_criterion["slice:slice-b"]["status"] == "passed"  # preserved, untouched by the correction
        print("Scenario 1 (mapped scope narrows correction, unaffected slice preserved) PASSED")
        restore(task_dir, worktree_ai_dir, backup_root)
        write_two_slice_plan(task_dir)  # restore() brings back the original 1-slice plan; reapply

        # --- Scenario: same file mapping, but the finding text is sensitive -> escalate.
        env = {
            **base_env,
            "FAKE_CODEX_FINDING_FILE": "libs/foo/a.ts",
            "FAKE_CODEX_FINDING_TITLE": "Auth bypass in A",
        }
        command(root, [str(ai), "task", "run", TASK_ID, "--max-attempts", "6"], env, expected=0)

        sidecar = json.loads((worktree_ai_dir / "input" / "correction-scope-review-001.json").read_text(encoding="utf-8"))
        assert sidecar["impacted_slices"] == ["slice-a"], sidecar  # still mappable...
        assert "auth" in sidecar["risk_categories"], sidecar
        assert sidecar["full_plan_fallback_required"] is True, sidecar  # ...but escalates anyway

        state = yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
        assert state["last_correction_implementation_scope"]["mode"] == "full_plan", state["last_correction_implementation_scope"]
        assert "sensitive" in state["last_correction_implementation_scope"]["full_plan_fallback_reason"]
        print("Scenario 2 (sensitive finding escalates to full-plan scope) PASSED")
        restore(task_dir, worktree_ai_dir, backup_root)

        print("Correction scope integration tests PASSED")


if __name__ == "__main__":
    main()
