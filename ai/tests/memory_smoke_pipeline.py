#!/usr/bin/env python3
"""Deterministic end-to-end smoke test for the memory integration layer.

Reuses smoke_pipeline.py's task/repo fixtures but drives AI_MEMORY_ENABLED=true with
AI_MEMORY_PROVIDER=fake, so the whole flow (recall -> accept -> publish -> requirement
change -> republish/supersede) is offline and deterministic. Never calls a real
TencentDB instance and never touches the real workspace's ai/tasks/ or
ai/integrations/tencentdb-memory/local-index/.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def load_smoke():
    path = SOURCE_ROOT / "ai" / "tests" / "smoke_pipeline.py"
    spec = importlib.util.spec_from_file_location("smoke_pipeline", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def write_knowledge_update(task_dir: Path, summary: str) -> None:
    payload = {
        "task_id": "TEST-1002",
        "updates": [
            {
                "target": "ai/repos/example-repo/known-issues.md",
                "type": "append",
                "summary": summary,
                "content": f"## {summary}\n\nDeterministic smoke content.",
                "approved": True,
                "category": "known_issue",
            }
        ],
    }
    (task_dir / "knowledge-updates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_direct(script: Path, args: list[str], root: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=root,
        env={**os.environ},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"expected {expected}, got {result.returncode}: {script.name} {' '.join(args)}\n{result.stdout}"
        )
    return result


def main() -> None:
    smoke = load_smoke()
    os.environ["AI_MEMORY_ENABLED"] = "true"
    os.environ["AI_MEMORY_PROVIDER"] = "fake"

    with tempfile.TemporaryDirectory(prefix="ai-memory-smoke-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", root / "ai")
        (root / "apps").mkdir()
        (root / "worktrees").mkdir()

        # config.yaml's own default is enabled:false (memory is off unless a task opts
        # in); flip the *copied* config to enabled:true so this smoke task's default
        # recall/publish path is exercised without needing a per-task override.
        config_path = root / "ai" / "integrations" / "tencentdb-memory" / "config.yaml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace("enabled: false", "enabled: true", 1),
            encoding="utf-8",
        )

        smoke.create_repo(root)
        task_dir = smoke.create_hierarchy(root)
        ai = root / "ai" / "bin" / "ai"

        recall_path = task_dir / "memory" / "recall.json"
        assert recall_path.is_file(), "memory recall.json was not written by prepare-context"
        recall = json.loads(recall_path.read_text(encoding="utf-8"))
        assert recall["available"] is True
        assert recall["content_sha256"]

        lock = json.loads((task_dir / "context.lock.json").read_text(encoding="utf-8"))
        assert lock["memory"]["enabled"] is True
        assert lock["memory"]["available"] is True
        assert lock["memory"]["sha256"] == recall["content_sha256"]

        rejected = run_direct(root / "ai" / "bin" / "memory-publish", ["TEST-1002"], root, expected=1)
        assert "state.status == completed" in rejected.stdout

        smoke.run_cycle(root, task_dir, 1, 0)
        smoke.run([str(ai), "task", "accept", "TEST-1002", "--accepted-by", "smoke-test"], root)
        # accept-task's report-only regenerates knowledge-updates.json from
        # implementation.json/review.json, overwriting any earlier write -- so the
        # fixture entry is written after accept, not before.
        write_knowledge_update(task_dir, "First known issue")

        first_publish = run_direct(root / "ai" / "bin" / "memory-publish", ["TEST-1002"], root)
        first_result = json.loads(first_publish.stdout)
        assert len(first_result["published"]) == 1
        assert first_result["published"][0]["category"] == "known_issue"
        first_asset_id = first_result["published"][0]["asset_id"]

        smoke.run(
            [str(ai), "task", "request-change", "TEST-1002", "--kind", "requirement_change", "--title", "Smoke reopened change"],
            root,
        )
        cycle_dir = task_dir / "changes" / "cycle-001"
        smoke.replace_markers(cycle_dir / "user-request.md")
        smoke.replace_markers(cycle_dir / "requirement-addendum.md")

        archived_recall = cycle_dir / "baseline" / "memory" / "recall.json"
        assert archived_recall.is_file(), "prior memory snapshot was not archived into the change cycle baseline"

        smoke.run([str(ai), "task", "prepare-plan", "TEST-1002", "--force"], root)
        smoke.run([str(ai), "task", "prepare-context", "TEST-1002"], root)
        smoke.run_cycle(root, task_dir, 2, 1)
        smoke.run([str(ai), "task", "accept", "TEST-1002", "--accepted-by", "smoke-test"], root)
        write_knowledge_update(task_dir, "Updated known issue")

        second_publish = run_direct(root / "ai" / "bin" / "memory-publish", ["TEST-1002"], root)
        second_result = json.loads(second_publish.stdout)
        assert len(second_result["published"]) == 1
        second_asset_id = second_result["published"][0]["asset_id"]
        assert second_asset_id != first_asset_id, "republish must not reuse the prior asset_id"
        superseded_ids = {item["asset_id"] for item in second_result["superseded"]}
        assert first_asset_id in superseded_ids, "republish to the same target did not supersede the prior entry"

        ledger = json.loads(
            (root / "ai" / "integrations" / "tencentdb-memory" / "local-index" / "superseded-assets.json").read_text(
                encoding="utf-8"
            )
        )
        statuses = {entry["asset_id"]: entry["status"] for entry in ledger["entries"]}
        assert statuses[first_asset_id] == "superseded"
        assert statuses[second_asset_id] == "active"

        assert not (SOURCE_ROOT / "ai" / "tasks" / "TEST-1002").exists(), "smoke test leaked into the real workspace"
        real_ledger = (
            SOURCE_ROOT / "ai" / "integrations" / "tencentdb-memory" / "local-index" / "superseded-assets.json"
        )
        real_ledger_data = json.loads(real_ledger.read_text(encoding="utf-8"))
        assert real_ledger_data == {"version": 1, "entries": []}, "smoke test wrote into the real supersession ledger"

        print("Memory smoke pipeline PASSED")


if __name__ == "__main__":
    main()
