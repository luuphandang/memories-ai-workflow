#!/usr/bin/env python3
"""Deterministic end-to-end smoke test for the orchestration layer.

The test copies the workspace to a temporary directory, creates a disposable Git
repository/worktree, and exercises correction plus post-completion reopening.
It never calls Claude or Codex and never modifies the real workspace.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def run_ai_router(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    args = cmd[1:]
    if args[0] == "bootstrap":
        script, rest = "bootstrap", args[1:]
    elif args[:2] == ["indexes", "rebuild"]:
        script, rest = "rebuild-indexes", args[2:]
    elif args[0] == "task" and len(args) >= 2:
        mapping = {
            "create": "create-task",
            "register-worktree": "register-worktree",
            "prepare-context": "prepare-context",
            "prepare-plan": "prepare-plan",
            "implement": "run-claude",
            "validate-code": "validate",
            "review": "run-codex-review",
            "request-fixes": "request-fixes",
            "report": "finalize-task",
            "accept": "accept-task",
            "request-change": "request-change",
            "update-knowledge": "update-knowledge",
        }
        script, rest = mapping[args[1]], args[2:]
    else:
        raise AssertionError(f"Unsupported AI smoke command: {args}")

    script_path = cwd / "ai" / "bin" / script
    previous_argv = sys.argv
    previous_cwd = Path.cwd()
    output = io.StringIO()
    code = 0
    try:
        os.chdir(cwd)
        sys.argv = [str(script_path), *rest]
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                runpy.run_path(str(script_path), run_name="__main__")
            except SystemExit as exc:
                code = int(exc.code or 0) if isinstance(exc.code, (int, type(None))) else 1
                if not isinstance(exc.code, (int, type(None))):
                    print(exc.code, file=output)
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)
    return subprocess.CompletedProcess(cmd, code, output.getvalue())


def run(cmd: list[str], cwd: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    print("RUN:", " ".join(cmd), flush=True)
    if Path(cmd[0]).name == "ai" and Path(cmd[0]).parent.name == "bin":
        result = run_ai_router(cmd, cwd)
    else:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
            timeout=30,
        )
    if result.returncode != expected:
        raise AssertionError(
            f"Command returned {result.returncode}, expected {expected}: {' '.join(cmd)}\n{result.stdout}"
        )
    return result


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_markers(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("[BỔ SUNG THEO DỰ ÁN]", "Smoke-test project context")
    text = text.replace("[BỔ SUNG THEO TÍNH NĂNG]", "Smoke-test requirement")
    path.write_text(text, encoding="utf-8")


def implementation(task_id: str, implementation_cycle: int, change_cycle: int) -> dict:
    return {
        "task_id": task_id,
        "status": "implemented",
        "summary": "Synthetic implementation handoff for orchestration smoke testing.",
        "repositories": [{"name": "example-repo", "changed_files": ["README.md"]}],
        "decisions": [],
        "assumptions": [],
        "validation_commands": [],
        "acceptance_criteria": [
            {"criterion": "Smoke pipeline completes", "status": "passed", "evidence": "deterministic fixture"}
        ],
        "knowledge_updates": [],
        "implementation_cycle": implementation_cycle,
        "change_cycle": change_cycle,
    }


def review(task_id: str, implementation_cycle: int, change_cycle: int, verdict: str = "pass", findings: list | None = None) -> dict:
    return {
        "task_id": task_id,
        "verdict": verdict,
        "applied_skills": [],
        "reviewed_repositories": ["example-repo"],
        "review_coverage": {
            "review_passes": ["requirements", "diff", "architecture", "behavior", "tests", "security", "regression"],
            "changed_files": [{"repo": "example-repo", "file": "README.md", "status": "reviewed", "evidence": "synthetic fixture"}],
            "risk_areas": [{"area": "smoke pipeline", "status": "reviewed", "evidence": "synthetic fixture"}],
            "prior_findings": [],
            "completion_statement": True,
        },
        "findings": findings or [],
        "validation_assessment": {"passed": True, "missing": []},
        "acceptance_criteria": [{"criterion": "Smoke pipeline completes", "status": "passed"}],
        "knowledge_updates": [],
        "summary": "Synthetic Codex review fixture.",
        "implementation_cycle": implementation_cycle,
        "change_cycle": change_cycle,
    }


def set_state_fields(path: Path, **fields) -> None:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(fields)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def with_skill_evidence(task_dir: Path, artifact: dict, role: str) -> dict:
    lock = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
    task = __import__("yaml").safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    artifact["applied_skills"] = [
        {"name": name, "sha256": lock["skills"]["locked"][name]["sha256"], "checks_completed": ["smoke fixture"]}
        for name in task["skills"][role]
    ]
    if role == "implement":
        plan = json.loads((task_dir / "execution-plan.json").read_text(encoding="utf-8"))
        artifact["acceptance_criteria"] = [
            {"criterion": f"slice:{item['id']}", "status": "passed", "evidence": "deterministic smoke fixture"}
            for item in plan["slices"]
        ]
    return artifact


def configure_task(path: Path) -> None:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["review"]["fail_on"] = ["blocker", "major", "minor"]
    data["validation"] = {"example-repo": ["smoke"]}
    data["report"]["language"] = "en"
    data["report"]["include_diff_stat"] = False
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def create_repo(root: Path) -> None:
    repo = root / "apps" / "example-repo"
    repo.mkdir(parents=True)
    run(["git", "init", "-b", "main"], repo)
    run(["git", "config", "user.email", "smoke@example.invalid"], repo)
    run(["git", "config", "user.name", "AI Smoke Test"], repo)
    (repo / "README.md").write_text("# Example\n", encoding="utf-8")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "initial"], repo)
    worktree = root / "worktrees" / "TEST-1002" / "example-repo"
    worktree.parent.mkdir(parents=True)
    run(["git", "worktree", "add", "-b", "feature/TEST-1002-smoke", str(worktree), "HEAD"], repo)

    knowledge = root / "ai" / "repos" / "example-repo"
    shutil.copytree(root / "ai" / "repos" / "backend", knowledge)
    (knowledge / "commands.yaml").write_text(
        """package_manager: none
commands:
  smoke:
    command: python3 -c 'print("smoke ok")'
    required: true
    timeout_seconds: 30
""",
        encoding="utf-8",
    )


def create_hierarchy(root: Path) -> Path:
    ai = root / "ai" / "bin" / "ai"
    run([
        str(ai), "task", "create", "TEST-1002", "--type", "task", "--parent", "TEST-1001", "--epic", "TEST-1000",
        "--repos", "example-repo", "--title", "Smoke task",
    ], root)
    task_dir = root / "ai" / "tasks" / "TEST-1002"
    configure_task(task_dir / "task.yaml")
    assert __import__("yaml").safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))["review"]["max_cycles"] == 5
    import yaml
    context_path = task_dir / "context.yaml"
    context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
    context["domains"] = []
    context_path.write_text(yaml.safe_dump(context, allow_unicode=True, sort_keys=False), encoding="utf-8")
    run([
        str(ai), "task", "register-worktree", "TEST-1002", "--repo", "example-repo",
        "--path", "worktrees/TEST-1002/example-repo", "--base-ref", "main",
    ], root)
    replace_markers(task_dir / "task.md")
    run([str(ai), "task", "prepare-plan", "TEST-1002", "--force"], root)
    run([str(ai), "task", "prepare-context", "TEST-1002"], root)
    return task_dir


def write_validation(root: Path, implementation_cycle: int, change_cycle: int) -> None:
    path = root / "worktrees" / "TEST-1002" / ".ai" / "validation" / "summary.json"
    write_json(path, {
        "task_id": "TEST-1002",
        "generated_at": "smoke",
        "implementation_cycle": implementation_cycle,
        "change_cycle": change_cycle,
        "passed": True,
        "repositories": [],
        "dry_run": False,
    })


def run_cycle(root: Path, task_dir: Path, implementation_cycle: int, change_cycle: int) -> None:
    ai = root / "ai" / "bin" / "ai"
    write_json(task_dir / "implementation.json", with_skill_evidence(task_dir, implementation("TEST-1002", implementation_cycle, change_cycle), "implement"))
    write_validation(root, implementation_cycle, change_cycle)
    write_json(task_dir / "review.json", with_skill_evidence(task_dir, review("TEST-1002", implementation_cycle, change_cycle), "review"))
    # This fixture represents a normal, complete (full) review; only a full review's
    # pass can authorize report/acceptance (delta reviews cannot, by contract).
    set_state_fields(task_dir / "state.yaml", last_review_mode="full")
    run([str(ai), "task", "report", "TEST-1002"], root)
    state = (task_dir / "state.yaml").read_text(encoding="utf-8")
    assert "awaiting_user_acceptance" in state
    report_text = (task_dir / "final-report.md").read_text(encoding="utf-8")
    assert report_text.startswith("# Report TEST-1002")
    assert "## Git diff stat" not in report_text


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ai-workspace-smoke-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        for name in ("README.md", "user_manual.md", "folder_structure_guide.md", ".env.ai.example", ".gitignore"):
            source = SOURCE_ROOT / name
            if source.exists():
                shutil.copy2(source, root / name)
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()
        create_repo(root)
        task_dir = create_hierarchy(root)
        ai = root / "ai" / "bin" / "ai"

        # Handcrafted artifacts cannot bypass required-skill gates at report time.
        write_json(task_dir / "implementation.json", implementation("TEST-1002", 1, 0))
        write_validation(root, 1, 0)
        write_json(task_dir / "review.json", review("TEST-1002", 1, 0))
        bypass = run([str(ai), "task", "report", "TEST-1002"], root, expected=1)
        assert "required-skill gate" in bypass.stdout

        # Verify review.fail_on is actually used by request-fixes.
        minor = {
            "severity": "minor",
            "repo": "example-repo",
            "file": "README.md",
            "line": 1,
            "title": "Configured minor finding",
            "evidence": "Synthetic fixture",
            "expected_fix": "Resolve the fixture",
        }
        write_json(task_dir / "implementation.json", with_skill_evidence(task_dir, implementation("TEST-1002", 1, 0), "implement"))
        run([str(ai), "task", "validate-code", "TEST-1002"], root)
        write_json(task_dir / "review.json", with_skill_evidence(task_dir, review("TEST-1002", 1, 0, "changes_requested", [minor]), "review"))
        set_state_fields(task_dir / "state.yaml", review_cycle=1, status="changes_requested_by_codex")
        fix = run([str(ai), "task", "request-fixes", "TEST-1002"], root)
        assert "fix-request-review-001.md" in fix.stdout
        assert "[minor]" in (root / "worktrees" / "TEST-1002" / ".ai" / "input" / "fix-request-review-001.md").read_text()

        # Complete the initial cycle.
        write_json(task_dir / "review.json", with_skill_evidence(task_dir, review("TEST-1002", 1, 0), "review"))
        set_state_fields(task_dir / "state.yaml", last_review_mode="full")
        run([str(ai), "task", "report", "TEST-1002"], root)

        # Correction before acceptance, same worktree.
        run([str(ai), "task", "request-change", "TEST-1002", "--kind", "correction", "--title", "Smoke correction"], root)
        cycle1 = task_dir / "changes" / "cycle-001"
        replace_markers(cycle1 / "user-request.md")
        replace_markers(cycle1 / "requirement-addendum.md")
        run([str(ai), "task", "prepare-plan", "TEST-1002", "--force"], root)
        run([str(ai), "task", "prepare-context", "TEST-1002"], root)
        run_cycle(root, task_dir, 2, 1)
        run([str(ai), "task", "accept", "TEST-1002", "--accepted-by", "smoke-test"], root)

        # Requirement change after completion, still the same registered worktree.
        run([str(ai), "task", "request-change", "TEST-1002", "--kind", "requirement_change", "--title", "Smoke reopened change"], root)
        cycle2 = task_dir / "changes" / "cycle-002"
        replace_markers(cycle2 / "user-request.md")
        replace_markers(cycle2 / "requirement-addendum.md")
        run([str(ai), "task", "prepare-plan", "TEST-1002", "--force"], root)
        run([str(ai), "task", "prepare-context", "TEST-1002"], root)
        run_cycle(root, task_dir, 3, 2)
        run([str(ai), "task", "accept", "TEST-1002", "--accepted-by", "smoke-test"], root)

        final_state = (task_dir / "state.yaml").read_text(encoding="utf-8")
        assert "status: completed" in final_state
        assert "change_cycle: 2" in final_state
        assert (task_dir / "changes" / "cycle-001" / "baseline").is_dir()
        assert (task_dir / "changes" / "cycle-002" / "baseline").is_dir()
        print("Smoke pipeline PASSED")


if __name__ == "__main__":
    main()
