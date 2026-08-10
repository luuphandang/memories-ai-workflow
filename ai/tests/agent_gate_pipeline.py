#!/usr/bin/env python3
"""Exercise real implement/review wrappers with deterministic fake CLIs."""
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


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def command(root: Path, args: list[str], env: dict, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=root, env={**os.environ, **env}, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {' '.join(args)}\n{result.stdout}")
    return result


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-agent-gates-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir(); (root / "worktrees").mkdir()
        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)
        ai = root / "ai" / "bin" / "ai"
        fake_claude = root / "ai" / "tests" / "fakes" / "fake_claude.py"
        fake_codex = root / "ai" / "tests" / "fakes" / "fake_codex.py"
        fake_claude.chmod(0o755); fake_codex.chmod(0o755)
        env = {"CLAUDE_COMMAND": str(fake_claude), "CODEX_COMMAND": str(fake_codex), "CLAUDE_TIMEOUT_SECONDS": "30", "CODEX_TIMEOUT_SECONDS": "30"}

        before_dry_run = (task_dir / "state.yaml").read_text(encoding="utf-8")
        dry_run = command(root, [str(ai), "task", "run", "TEST-1002", "--dry-run"], env)
        assert "never runs accept" in dry_run.stdout and (task_dir / "state.yaml").read_text(encoding="utf-8") == before_dry_run

        command(root, [str(ai), "task", "implement", "TEST-1002"], {**env, "FAKE_CLAUDE_MODE": "quota"}, expected=1)
        state = yaml.safe_load((task_dir / "state.yaml").read_text())
        assert state["status"] == "interrupted" and state["claude_session_id"] == "fake-claude-session"
        command(root, [str(ai), "task", "run", "TEST-1002", "--resume-interrupted", "--max-attempts", "3"], {**env, "FAKE_CLAUDE_MODE": "success", "FAKE_CODEX_CHANGES_ONCE": "1"})
        prompt = (root / "worktrees" / "TEST-1002" / ".ai" / "input" / "claude-prompt.md").read_text()
        assert "fix-request-review-001.md" in prompt
        state = yaml.safe_load((task_dir / "state.yaml").read_text())
        assert state["status"] == "awaiting_user_acceptance" and state["automation"]["attempts"] == 2
        command(root, [str(ai), "task", "accept", "TEST-1002", "--accepted-by", "fake-e2e"], env)

        metrics = command(root, [str(ai), "metrics", "TEST-1002"], env)
        data = json.loads(metrics.stdout)
        assert data["implement_attempts"] == 3 and data["review_attempts"] == 3 and data["resumed_attempts"] == 1

        # A changed reference invalidates the aggregate skill hash, not only SKILL.md changes.
        reference = root / "ai" / "skills" / "decompose-implementation-task" / "references" / "scope-thresholds.md"
        reference.write_text(reference.read_text() + "\nchanged after lock\n", encoding="utf-8")
        changed = command(root, [str(ai), "task", "implement", "TEST-1002", "--dry-run"], env, expected=1)
        assert "changed after context lock" in changed.stdout
        print("Agent gate pipeline PASSED")


if __name__ == "__main__":
    main()
