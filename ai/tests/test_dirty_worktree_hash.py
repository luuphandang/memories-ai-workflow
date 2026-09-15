#!/usr/bin/env python3
"""Regression coverage for workflow_issue.md #1: git_worktree_paths()/dirty_worktree_hash()
must give validate/review/finalize a single machine-comparable fingerprint of "has the
worktree changed" that isn't fooled by HEAD staying put -- this task workflow never commits
mid-task, so HEAD alone (what review.json's reviewed_revisions used before this change)
almost never moves while a task is in progress.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

AI_COMMON_PATH = Path(__file__).resolve().parents[1] / "bin" / "lib" / "ai_common.py"


def load_ai_common():
    spec = importlib.util.spec_from_file_location("ai_common_dirty_hash_test", AI_COMMON_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "tracked.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.DEVNULL)


class DirtyWorktreeHashTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ai_common = load_ai_common()

    def test_hash_stable_for_unchanged_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            first = self.ai_common.dirty_worktree_hash(root)
            second = self.ai_common.dirty_worktree_hash(root)
            self.assertEqual(first, second)

    def test_hash_changes_when_tracked_file_is_edited(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            before = self.ai_common.dirty_worktree_hash(root)
            (root / "tracked.txt").write_text("edited\n", encoding="utf-8")
            after = self.ai_common.dirty_worktree_hash(root)
            self.assertNotEqual(before, after)

    def test_hash_changes_when_untracked_file_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            before = self.ai_common.dirty_worktree_hash(root)
            (root / "new-file.txt").write_text("new content\n", encoding="utf-8")
            after = self.ai_common.dirty_worktree_hash(root)
            self.assertNotEqual(before, after)

    def test_head_sha_alone_would_miss_the_edit_this_hash_catches(self) -> None:
        """The exact gap this closes: HEAD never moves mid-task, so a HEAD-only comparison
        (what review.json's reviewed_revisions stored before this change) sees no difference
        even though the worktree content plainly changed."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            head_before = self.ai_common.git_value(root, ["rev-parse", "HEAD"])
            hash_before = self.ai_common.dirty_worktree_hash(root)
            (root / "tracked.txt").write_text("changed after review\n", encoding="utf-8")
            head_after = self.ai_common.git_value(root, ["rev-parse", "HEAD"])
            hash_after = self.ai_common.dirty_worktree_hash(root)
            self.assertEqual(head_before, head_after)
            self.assertNotEqual(hash_before, hash_after)

    def test_worktree_paths_matches_untracked_and_tracked_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            (root / "tracked.txt").write_text("edited\n", encoding="utf-8")
            (root / "new-file.txt").write_text("new content\n", encoding="utf-8")
            paths = self.ai_common.git_worktree_paths(root)
            self.assertEqual(paths, {"tracked.txt", "new-file.txt"})

    def test_rename_keeps_only_destination_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init_repo(root)
            (root / "tracked.txt").rename(root / "renamed.txt")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            paths = self.ai_common.git_worktree_paths(root)
            self.assertEqual(paths, {"renamed.txt"})


if __name__ == "__main__":
    unittest.main()
