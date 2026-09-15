#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #9: a known-issue file for a required skill
(ai/shared/quality/known-issues/<skill>.md) must be picked up by prepare-context and
recorded in context.lock.json, so a new task reusing the same skill loads the known
limitation without anyone having to remember to say so.

Reuses smoke_pipeline's task/worktree setup (single-repo TEST-1002 fixture) since building
that from scratch here would duplicate a lot of orchestration plumbing.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline_known_issues", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    smoke = load_smoke()
    with tempfile.TemporaryDirectory(prefix="ai-known-issues-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()
        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)

        lock_before = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
        assert lock_before["skills"]["known_issues"] == {}, lock_before["skills"]["known_issues"]

        import yaml

        task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
        required_skill = (task["skills"]["implement"] + task["skills"]["review"])[0]
        issue_dir = root / "ai" / "shared" / "quality" / "known-issues"
        issue_dir.mkdir(parents=True, exist_ok=True)
        issue_path = issue_dir / f"{required_skill}.md"
        issue_content = (
            f"# Known issue: {required_skill}\n\n"
            "Description of how to recognize the defect.\n\n"
            "Fixture: ai/tests/fixtures/skill-checks/fidelity-pass/matrix.json\n"
        )
        issue_path.write_text(issue_content, encoding="utf-8")

        ai = root / "ai" / "bin" / "ai"
        subprocess.run(
            [str(ai), "task", "prepare-context", "TEST-1002"],
            cwd=root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

        lock_after = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
        entry = lock_after["skills"]["known_issues"].get(required_skill)
        assert entry is not None, lock_after["skills"]["known_issues"]
        assert entry["path"] == f"ai/shared/quality/known-issues/{required_skill}.md", entry
        expected_hash = hashlib.sha256(issue_path.read_bytes()).hexdigest()
        assert entry["sha256"] == expected_hash, entry

        matching_files = [
            item for item in lock_after["files"]
            if item.get("category") == "known-issues" and item.get("path") == entry["path"]
        ]
        assert len(matching_files) == 1, lock_after["files"]

        print("Known-issues context-lock wiring PASSED")


if __name__ == "__main__":
    main()
