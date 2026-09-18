from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "register-worktree"
SPEC = importlib.util.spec_from_loader(
    "register_worktree_script", SourceFileLoader("register_worktree_script", str(SCRIPT))
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorktreeRegistrationGuardTest(unittest.TestCase):
    def test_active_task_cannot_share_writable_canonical_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tasks = root / "tasks"
            existing = tasks / "TASK-A"
            existing.mkdir(parents=True)
            worktree = root / "worktree"
            worktree.mkdir()
            (existing / "task.yaml").write_text(yaml.safe_dump({
                "worktrees": [{"path": str(worktree), "writable": True}]
            }))
            (existing / "state.yaml").write_text(yaml.safe_dump({"status": "implementing"}))
            with patch.object(MODULE, "AI_ROOT", root), patch.object(
                MODULE, "safe_workspace_path", side_effect=lambda value: Path(value)
            ):
                with self.assertRaises(SystemExit):
                    MODULE.ensure_unique_writable_path("TASK-B", worktree, True)

    def test_failed_or_read_only_registration_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tasks = root / "tasks"
            existing = tasks / "TASK-A"
            existing.mkdir(parents=True)
            worktree = root / "worktree"
            worktree.mkdir()
            (existing / "task.yaml").write_text(yaml.safe_dump({
                "worktrees": [{"path": str(worktree), "writable": True}]
            }))
            (existing / "state.yaml").write_text(yaml.safe_dump({"status": "failed"}))
            with patch.object(MODULE, "AI_ROOT", root), patch.object(
                MODULE, "safe_workspace_path", side_effect=lambda value: Path(value)
            ):
                MODULE.ensure_unique_writable_path("TASK-B", worktree, True)
                MODULE.ensure_unique_writable_path("TASK-B", worktree, False)

    def test_completed_task_retains_worktree_for_reopening(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            existing = root / "tasks" / "TASK-A"
            existing.mkdir(parents=True)
            worktree = root / "worktree"
            worktree.mkdir()
            (existing / "task.yaml").write_text(yaml.safe_dump({
                "worktrees": [{"path": str(worktree), "writable": True}]
            }))
            (existing / "state.yaml").write_text(yaml.safe_dump({"status": "completed"}))
            with patch.object(MODULE, "AI_ROOT", root), patch.object(
                MODULE, "safe_workspace_path", side_effect=lambda value: Path(value)
            ):
                with self.assertRaises(SystemExit):
                    MODULE.ensure_unique_writable_path("TASK-B", worktree, True)


if __name__ == "__main__":
    unittest.main()
