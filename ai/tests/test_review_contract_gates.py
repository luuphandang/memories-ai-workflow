#!/usr/bin/env python3
"""Regression coverage for the full-vs-delta review contract:

- Delta mode is only ever auto-selected immediately after a passing... no, after a
  FULL review's correction request (never delta-after-delta); consecutive corrections
  must alternate back to full.
- A delta review's own "pass" verdict can never directly authorize finalize-task/
  accept-task, even via a direct/manual call that bypasses run-task's orchestration.

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


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline_review_contract", path)
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


def set_state_fields(task_dir: Path, **fields) -> None:
    state = read_state(task_dir)
    state.update(fields)
    (task_dir / "state.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-review-contract-") as tmp:
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
        }

        backup_root = Path(tmp) / "backup"
        backup_root.mkdir()
        snapshot(task_dir, worktree_ai_dir, backup_root)

        # --- Scenario 1: two consecutive correction rounds must alternate full/delta/full,
        # never delta directly after delta, even though both corrections avoid sensitive terms.
        env = {**base_env, "FAKE_CODEX_CHANGES_REQUESTED_COUNT": "2"}
        result = command(root, [str(ai), "task", "run", TASK_ID, "--max-attempts", "6"], env, expected=0)
        state = read_state(task_dir)
        assert state["status"] == "awaiting_user_acceptance", state
        assert state["last_review_mode"] == "full", state

        metrics = command(root, [str(ai), "metrics", TASK_ID], base_env, expected=0)
        data = json.loads(metrics.stdout)
        review_modes = [e["review_mode"] for e in data["events"] if e.get("agent") == "codex"]
        assert review_modes == ["full", "delta", "full"], review_modes
        print("Scenario 1 (full/delta/full alternation) PASSED")
        restore(task_dir, worktree_ai_dir, backup_root)

        # --- Scenario 2: a hand-crafted delta "pass" cannot directly authorize report,
        # even via a direct finalize-task call that bypasses run-task's orchestration.
        write_json = lambda p, d: p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")  # noqa: E731
        write_json(
            task_dir / "implementation.json",
            smoke.with_skill_evidence(task_dir, smoke.implementation(TASK_ID, 1, 0), "implement"),
        )
        smoke.write_validation(root, 1, 0)
        write_json(
            task_dir / "review.json",
            smoke.with_skill_evidence(task_dir, smoke.review(TASK_ID, root, 1, 0), "review"),
        )
        # This is the crux: a review that returned "pass" but was itself only a delta
        # review (e.g. produced by a direct manual `--mode delta` call).
        set_state_fields(task_dir, last_review_mode="delta")
        report = command(root, [str(ai), "task", "report", TASK_ID], base_env)
        assert report.returncode != 0, report.stdout
        assert "not a passing full review" in report.stdout, report.stdout
        state = read_state(task_dir)
        assert state["status"] != "awaiting_user_acceptance", state
        print("Scenario 2a (finalize-task refuses delta-pass) PASSED")

        # And accept-task refuses even if status were somehow forced to awaiting_user_acceptance.
        set_state_fields(task_dir, last_review_mode="delta", status="awaiting_user_acceptance")
        accept = command(root, [str(ai), "task", "accept", TASK_ID, "--accepted-by", "tester"], base_env)
        assert accept.returncode != 0, accept.stdout
        assert "not a passing full review" in accept.stdout, accept.stdout
        state = read_state(task_dir)
        assert state["status"] != "completed", state
        print("Scenario 2b (accept-task refuses delta-pass) PASSED")
        restore(task_dir, worktree_ai_dir, backup_root)

        print("Review contract gate tests PASSED")


if __name__ == "__main__":
    main()
