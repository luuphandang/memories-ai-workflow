#!/usr/bin/env python3
"""Regression coverage: automation must terminate cleanly (never left `running`)
when the mandatory final full review after a delta pass fails, is blocked, or
returns an invalid verdict.

Note: this only creates one task hierarchy (via smoke_pipeline's in-process
runpy-based `ai/bin/ai` router) for the whole process, then resets the task's
runtime state between scenarios via snapshot/restore. Calling
smoke.create_hierarchy() more than once per process is unsafe: it runs
ai/bin/* scripts in-process via runpy, and Python caches `lib.ai_common` (and
its ROOT/AI_ROOT constants) in sys.modules across calls, so a second call
against a different temp workspace would silently reuse the first
workspace's paths.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TEST-1002"


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline_ffrf", path)
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


def read_state(task_dir: Path) -> dict:
    return yaml.safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))


def assert_automation_terminated_cleanly(state: dict) -> None:
    automation = state.get("automation") or {}
    assert automation.get("status") in {"stopped", "blocked"}, (
        f"automation.status must be terminal, found {automation.get('status')!r}"
    )
    assert automation.get("finished_at") is not None, "automation.finished_at must be set"


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-final-full-review-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()
        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)
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
            # Force a delta correction on the first review, so run-task reaches the
            # mandatory final-full-review step after the delta pass.
            "FAKE_CODEX_CHANGES_ONCE": "1",
        }

        backup_root = Path(tmp) / "backup"
        backup_root.mkdir()
        snapshot(task_dir, worktree_ai_dir, backup_root)

        def run_scenario(final_full_mode: str) -> subprocess.CompletedProcess[str]:
            env = {**base_env, "FAKE_CODEX_FINAL_FULL_MODE": final_full_mode}
            return command(root, [str(ai), "task", "run", TASK_ID, "--max-attempts", "3"], env)

        # 1. Codex exec exits non-zero on the mandatory final full review.
        result = run_scenario("exit_nonzero")
        assert result.returncode != 0, result.stdout
        state = read_state(task_dir)
        assert_automation_terminated_cleanly(state)
        assert state["status"] == "failed", state
        assert "Codex exited" in (state.get("last_error") or ""), state
        restore(task_dir, worktree_ai_dir, backup_root)

        # 2. Codex returns a valid but `blocked` verdict on the final full review.
        result = run_scenario("blocked")
        assert result.returncode != 0, result.stdout
        state = read_state(task_dir)
        assert_automation_terminated_cleanly(state)
        assert state["status"] == "blocked", state
        assert "Simulated blocked final full review" in (state.get("last_error") or ""), state
        restore(task_dir, worktree_ai_dir, backup_root)

        # 3. Codex returns schema-invalid output (bad verdict enum) on the final full review.
        result = run_scenario("invalid_verdict")
        assert result.returncode != 0, result.stdout
        state = read_state(task_dir)
        assert_automation_terminated_cleanly(state)
        assert state["status"] == "failed", state
        assert "invalid/unparseable" in (state.get("last_error") or ""), state
        restore(task_dir, worktree_ai_dir, backup_root)

        # 4. Control: an actually passing final full review still completes normally.
        result = run_scenario("")
        assert result.returncode == 0, result.stdout
        state = read_state(task_dir)
        assert state["status"] == "awaiting_user_acceptance", state
        assert state["automation"]["status"] == "awaiting_user_acceptance", state
        assert state["automation"].get("finished_at") is not None, state
        restore(task_dir, worktree_ai_dir, backup_root)

        print("Final full-review failure handling PASSED")


if __name__ == "__main__":
    main()
