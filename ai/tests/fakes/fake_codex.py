#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


def main() -> None:
    output_index = sys.argv.index("--output-last-message") + 1
    output = Path(sys.argv[output_index])
    prompt = sys.argv[-1]
    task_id = re.search(r"Jira item ([A-Z][A-Z0-9]+-\d+)", prompt).group(1)
    root = Path.cwd()
    task_dir = root / "ai" / "tasks" / task_id
    lock = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
    task = __import__("yaml").safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    state = __import__("yaml").safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
    counter = root / "worktrees" / task_id / ".ai" / "fake-codex-count"
    count = int(counter.read_text() if counter.exists() else "0") + 1
    counter.write_text(str(count), encoding="utf-8")

    # run-codex-review consumes --mode itself; it never forwards it to the underlying
    # `codex` CLI. The mode is only visible to us via the prompt's "Review mode: X."
    # line. The mandatory final full review (after a delta pass) is the first "full"
    # mode call that isn't the very first review of the cycle.
    is_final_full = count > 1 and "Review mode: full." in prompt
    final_full_mode = os.environ.get("FAKE_CODEX_FINAL_FULL_MODE") if is_final_full else None
    if final_full_mode == "exit_nonzero":
        print("simulated codex crash during final full review", file=sys.stderr)
        sys.exit(1)

    changes_requested_count = int(os.environ.get("FAKE_CODEX_CHANGES_REQUESTED_COUNT", "0") or 0)
    changes_requested = (
        (os.environ.get("FAKE_CODEX_CHANGES_ONCE") == "1" and count == 1)
        or (changes_requested_count > 0 and count <= changes_requested_count)
    )
    finding_file = os.environ.get("FAKE_CODEX_FINDING_FILE", "README.md")
    finding_title = os.environ.get("FAKE_CODEX_FINDING_TITLE", "Synthetic first-cycle finding")
    finding_repo = task.get("worktrees", [{}])[0].get("repo", "unknown")
    finding_slug = re.sub(r"[^a-z0-9]+", "-", finding_title.lower()).strip("-")
    finding_id = f"{finding_repo}:{finding_file}:major:{finding_slug}"
    findings = [{"finding_id": finding_id, "severity": "major", "repo": finding_repo, "file": finding_file, "line": 1, "title": finding_title, "evidence": "fake-agent-e2e", "expected_fix": "Run the automated fix cycle", "implementation_guidance": {"approach": "Apply the synthetic correction", "code_locations": [finding_file], "tests": ["Rerun fake-agent-e2e"], "done_when": ["The synthetic regression passes"]}}] if changes_requested else []

    if final_full_mode == "blocked":
        artifact = {
            "task_id": task_id, "verdict": "blocked",
            "applied_skills": [{"name": name, "sha256": lock["skills"]["locked"][name]["sha256"], "checks_completed": ["fake-agent-e2e"]} for name in task["skills"]["review"]],
            "reviewed_repositories": [item["repo"] for item in task.get("worktrees", [])],
            "review_coverage": {
                "review_passes": ["diff"],
                "changed_files": [],
                "risk_areas": [],
                "prior_findings": [],
                "completion_statement": False,
            },
            "findings": [], "validation_assessment": {"passed": True, "missing": []},
            "test_matrix": [],
            "acceptance_criteria": [], "knowledge_updates": [],
            "summary": "Simulated blocked final full review: could not complete coverage.",
            "implementation_cycle": int(state.get("implementation_cycle", 1)), "change_cycle": int(state.get("change_cycle", 0)),
        }
        output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"type": "thread.started", "thread_id": "fake-codex-thread"}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 10, "reasoning_output_tokens": 0}}))
        return

    if final_full_mode == "invalid_verdict":
        # Deliberately violates review.schema.json's verdict enum to exercise the
        # invalid/unparseable-output path in run-codex-review.
        output.write_text(json.dumps({"task_id": task_id, "verdict": "not-a-real-verdict"}) + "\n", encoding="utf-8")
        print(json.dumps({"type": "thread.started", "thread_id": "fake-codex-thread"}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 10, "reasoning_output_tokens": 0}}))
        return

    artifact = {
        "task_id": task_id, "verdict": "changes_requested" if changes_requested else "pass",
        "applied_skills": [{"name": name, "sha256": lock["skills"]["locked"][name]["sha256"], "checks_completed": ["fake-agent-e2e"]} for name in task["skills"]["review"]],
        "reviewed_repositories": [item["repo"] for item in task.get("worktrees", [])],
        "review_coverage": {
            "review_passes": ["requirements", "diff", "architecture", "behavior", "tests", "security", "regression"],
            "changed_files": [{"repo": item["repo"], "file": "README.md", "status": "reviewed", "evidence": "fake-agent-e2e"} for item in task.get("worktrees", [])],
            "risk_areas": [{"area": "fake end-to-end pipeline", "status": "reviewed", "evidence": "fake-agent-e2e"}],
            "prior_findings": ([{
                "finding_id": finding_id,
                "source": "fix-request-review-1.md",
                "title": finding_title,
                "status": "resolved",
                "evidence": "fake-agent-e2e reran the synthetic check",
            }] if count > 1 else []),
            "completion_statement": True,
        },
        "findings": findings, "validation_assessment": {"passed": True, "missing": []},
        "test_matrix": [{"id": "TM-1", "sources": ["requirement: synthetic acceptance", "diff-impact: README.md"], "target": "README.md", "test_level": "static", "scenario": "Synthetic pipeline review", "expected_result": "Pipeline fixture is valid", "status": "passed", "evidence": "fake-agent-e2e"}],
        "acceptance_criteria": [], "knowledge_updates": [], "summary": "Fake Codex review passed.",
        "implementation_cycle": int(state.get("implementation_cycle", 1)), "change_cycle": int(state.get("change_cycle", 0)),
    }
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"type": "thread.started", "thread_id": "fake-codex-thread"}))
    print(json.dumps({"type": "turn.started"}))
    print(json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "fake review complete"}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 400, "cache_write_input_tokens": 0, "output_tokens": 50, "reasoning_output_tokens": 5}}))


if __name__ == "__main__":
    main()
