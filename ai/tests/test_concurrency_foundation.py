#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai" / "bin"))

from lib.ai_common import (  # noqa: E402
    DEFAULT_BASE_REF,
    canonical_resource_id,
    coordination_policy,
    repository_identity,
    validate_capability_name,
)


class ConcurrencyFoundationTest(unittest.TestCase):
    def test_legacy_task_gets_safe_defaults(self) -> None:
        policy = coordination_policy({"id": "OLD-1"})
        self.assertEqual(policy["dynamic_producer"], "proposal_only")
        self.assertEqual(policy["target_ref"], "origin/master")
        self.assertEqual(DEFAULT_BASE_REF, "origin/master")

    def test_explicit_policy_overrides_defaults(self) -> None:
        policy = coordination_policy({
            "coordination": {
                "dynamic_producer": "auto_create_in_scope",
                "target_ref": "origin/release",
            }
        })
        self.assertEqual(policy["dynamic_producer"], "auto_create_in_scope")
        self.assertEqual(policy["target_ref"], "origin/release")

    def test_resource_and_capability_identities(self) -> None:
        self.assertEqual(
            canonical_resource_id("backend", "src/user/user.service.ts", "UserService.createUser"),
            "backend:src/user/user.service.ts#UserService.createUser",
        )
        with self.assertRaises(ValueError):
            canonical_resource_id("backend", "../outside")
        self.assertEqual(validate_capability_name("user.create"), "user.create")
        with self.assertRaises(ValueError):
            validate_capability_name("User Create")

    def test_repository_identity_is_shared_by_worktrees_and_distinct_for_repos(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            repo_a = temp / "repo-a"
            repo_b = temp / "repo-b"
            for repo in (repo_a, repo_b):
                repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
                subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
                (repo / "README.md").write_text("test\n", encoding="utf-8")
                subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
                subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
            worktree = temp / "repo-a-worktree"
            subprocess.run(["git", "worktree", "add", "-q", "-b", "feature/test", str(worktree)], cwd=repo_a, check=True)

            self.assertEqual(
                repository_identity(repo_a, "backend"),
                repository_identity(worktree, "backend"),
            )
            self.assertNotEqual(
                repository_identity(repo_a, "backend"),
                repository_identity(repo_b, "backend"),
            )


if __name__ == "__main__":
    unittest.main()
