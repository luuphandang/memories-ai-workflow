#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


def main() -> None:
    prompt = sys.argv[-1]
    match = re.search(r"Jira item ([A-Z][A-Z0-9]+-\d+)", prompt)
    if not match:
        raise SystemExit("fake Claude could not find task id")
    task_id = match.group(1)
    root = Path.cwd()
    task_dir = root / "ai" / "tasks" / task_id
    lock = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
    task = __import__("yaml").safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    state = __import__("yaml").safe_load((task_dir / "state.yaml").read_text(encoding="utf-8"))
    session_id = "fake-claude-session"
    print(json.dumps({"type": "system", "subtype": "init", "session_id": session_id}))
    mode = os.environ.get("FAKE_CLAUDE_MODE", "success")
    if mode == "quota":
        print(json.dumps({"type": "error", "session_id": session_id, "message": "You've hit your session limit"}))
        raise SystemExit(1)
    plan = json.loads((task_dir / "execution-plan.json").read_text(encoding="utf-8"))
    required = task["skills"]["implement"]
    applied = [] if mode == "missing-skill" else [
        {"name": name, "sha256": lock["skills"]["locked"][name]["sha256"], "checks_completed": ["fake-agent-e2e"]}
        for name in required
    ]
    artifact = {
        "task_id": task_id,
        "status": "implemented",
        "summary": "Fake Claude implementation for orchestration testing.",
        "applied_skills": applied,
        "repositories": [{"name": item["repo"], "changed_files": []} for item in task.get("worktrees", [])],
        "decisions": [], "assumptions": [], "validation_commands": [],
        "acceptance_criteria": [{"criterion": f"slice:{item['id']}", "status": "passed", "evidence": "fake-agent-e2e"} for item in plan["slices"]],
        "knowledge_updates": [],
        "implementation_cycle": int(state.get("implementation_cycle", 1)),
        "change_cycle": int(state.get("change_cycle", 0)),
    }
    (task_dir / "implementation.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    result = {"type": "result", "session_id": session_id, "result": "fake implementation complete", "usage": {"input_tokens": 120, "output_tokens": 30}, "total_cost_usd": 0, "num_turns": 1}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
