#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #1: run-codex-review must refuse to review when
the worktree has changed since validate-code last ran, using the dirty-worktree snapshot
hash (not head/diff_stat) as the freshness signal -- editing a file after a successful
validate-code run, without re-validating, must make the next review call fail instead of
silently reviewing stale-relative-to-validation source.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


SOURCE_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TEST-1002"


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline_freshness_gate", path)
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


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-freshness-gate-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()
        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)
        worktree = root / "worktrees" / TASK_ID / "example-repo"

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

        command(root, [str(ai), "task", "implement", TASK_ID], base_env, expected=0)
        command(root, [str(ai), "task", "validate-code", TASK_ID], base_env, expected=0)

        # Edit the worktree after validate-code ran, without re-validating.
        (worktree / "README.md").write_text("# Example\n\nEdited after validation.\n", encoding="utf-8")

        review = command(root, [str(ai), "task", "review", TASK_ID], base_env)
        assert review.returncode != 0, review.stdout
        assert "changed since validate-code" in review.stdout, review.stdout
        assert "re-run" in review.stdout.lower(), review.stdout
        print("Scenario 1 (dirty edit after validate-code blocks review) PASSED")

        # Re-validate against the edited source, then review must proceed normally.
        command(root, [str(ai), "task", "validate-code", TASK_ID], base_env, expected=0)
        review_after_revalidate = command(root, [str(ai), "task", "review", TASK_ID], base_env)
        assert review_after_revalidate.returncode == 0, review_after_revalidate.stdout
        print("Scenario 2 (re-validate then review succeeds) PASSED")

        # Edit the worktree again after this passing review, without re-reviewing: HEAD never
        # moves in this workflow, so only the dirty-snapshot hash catches this.
        (worktree / "README.md").write_text("# Example\n\nEdited after review.\n", encoding="utf-8")
        report = command(root, [str(ai), "task", "report", TASK_ID], base_env)
        assert report.returncode != 0, report.stdout
        assert "source changed since the reviewed revision" in report.stdout, report.stdout
        print("Scenario 3 (dirty edit after review blocks finalize) PASSED")

        print("Validation freshness gate tests PASSED")


if __name__ == "__main__":
    main()
