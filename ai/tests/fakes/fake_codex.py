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
    changes_requested = os.environ.get("FAKE_CODEX_CHANGES_ONCE") == "1" and count == 1
    findings = [{"severity": "major", "repo": task.get("worktrees", [{}])[0].get("repo", "unknown"), "file": "README.md", "line": 1, "title": "Synthetic first-cycle finding", "evidence": "fake-agent-e2e", "expected_fix": "Run the automated fix cycle"}] if changes_requested else []
    artifact = {
        "task_id": task_id, "verdict": "changes_requested" if changes_requested else "pass",
        "applied_skills": [{"name": name, "sha256": lock["skills"]["locked"][name]["sha256"], "checks_completed": ["fake-agent-e2e"]} for name in task["skills"]["review"]],
        "reviewed_repositories": [item["repo"] for item in task.get("worktrees", [])],
        "review_coverage": {
            "review_passes": ["requirements", "diff", "architecture", "behavior", "tests", "security", "regression"],
            "changed_files": [{"repo": item["repo"], "file": "README.md", "status": "reviewed", "evidence": "fake-agent-e2e"} for item in task.get("worktrees", [])],
            "risk_areas": [{"area": "fake end-to-end pipeline", "status": "reviewed", "evidence": "fake-agent-e2e"}],
            "prior_findings": ([{
                "source": "fix-request-review-1.md",
                "title": "Synthetic first-cycle finding",
                "status": "resolved",
                "evidence": "fake-agent-e2e reran the synthetic check",
            }] if count > 1 else []),
            "completion_statement": True,
        },
        "findings": findings, "validation_assessment": {"passed": True, "missing": []},
        "acceptance_criteria": [], "knowledge_updates": [], "summary": "Fake Codex review passed.",
        "implementation_cycle": int(state.get("implementation_cycle", 1)), "change_cycle": int(state.get("change_cycle", 0)),
    }
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print("fake review complete")


if __name__ == "__main__":
    main()
