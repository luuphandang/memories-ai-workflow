from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


class CreateTaskFlowIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="create-task-flow-")
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        shutil.copytree(SOURCE_ROOT / "ai", self.root / "ai")
        (self.root / "apps").mkdir()
        (self.root / "worktrees").mkdir()
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for repo in ("backend", "frontend"):
            self._create_repository(repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create_repository(self, name: str) -> None:
        remote = self.root / "remotes" / f"{name}.git"
        remote.parent.mkdir(exist_ok=True)
        run(["git", "init", "--bare", str(remote)], self.root)
        repository = self.root / "apps" / name
        run(["git", "clone", str(remote), str(repository)], self.root)
        run(["git", "config", "user.email", "workflow-test@example.invalid"], repository)
        run(["git", "config", "user.name", "Workflow Test"], repository)
        run(["git", "checkout", "-b", "master"], repository)
        (repository / "package.json").write_text(
            '{"name":"' + name + '-fixture","version":"1.0.0","private":true}\n',
            encoding="utf-8",
        )
        (repository / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
        (repository / ".env").write_text(f"FIXTURE_REPO={name}\n", encoding="utf-8")
        run(["git", "add", "package.json", ".gitignore"], repository)
        run(["git", "commit", "-m", "fixture"], repository)
        run(["git", "push", "-u", "origin", "master"], repository)

    def _create(self, task_id: str, task_type: str, title: str, *hierarchy: str) -> None:
        run([
            str(self.root / "ai" / "bin" / "ai"), "task", "create", task_id,
            "--type", task_type, "--title", title, "--repos", "backend,frontend",
            *hierarchy,
        ], self.root, self.env)

    def _publish(self, task_id: str) -> None:
        task = yaml.safe_load((self.root / "ai" / "tasks" / task_id / "task.yaml").read_text())
        for item in task["worktrees"]:
            worktree = self.root / item["path"]
            run(["git", "push", "-u", "origin", "HEAD"], worktree)

    def _assert_task(self, task_id: str, branch: str, base_ref: str) -> None:
        task_dir = self.root / "ai" / "tasks" / task_id
        task = yaml.safe_load((task_dir / "task.yaml").read_text())
        state = yaml.safe_load((task_dir / "state.yaml").read_text())
        self.assertEqual({item["repo"] for item in task["worktrees"]}, {"backend", "frontend"})
        self.assertEqual(task["coordination"]["target_ref"], base_ref)
        self.assertTrue((self.root / "worktrees" / task_id / "docs" / "README.md").is_file())
        for repo in ("backend", "frontend"):
            worktree = self.root / "worktrees" / task_id / repo
            self.assertEqual(run(["git", "branch", "--show-current"], worktree).stdout.strip(), branch)
            self.assertEqual((worktree / ".env").read_text(), f"FIXTURE_REPO={repo}\n")
            self.assertTrue((worktree / "package-lock.json").is_file())
            self.assertEqual(state["repositories"][repo]["registered_branch"], branch)
            self.assertEqual(state["repositories"][repo]["base_ref"], base_ref)
            self.assertTrue((self.root / "apps" / repo / ".env").is_file())

    def test_epic_story_task_flow(self) -> None:
        self._create("MEMORIES-9000", "epic", "Ký ức gia đình")
        epic_branch = "epic/MEMORIES-9000-ky-uc-gia-dinh"
        self._assert_task("MEMORIES-9000", epic_branch, "origin/master")
        self._publish("MEMORIES-9000")

        self._create("MEMORIES-9001", "story", "Album mùa hè", "--parent", "MEMORIES-9000")
        story_branch = "story/MEMORIES-9001-album-mua-he"
        self._assert_task("MEMORIES-9001", story_branch, f"origin/{epic_branch}")
        self._publish("MEMORIES-9001")

        self._create(
            "MEMORIES-9002", "task", "Tải ảnh lên",
            "--parent", "MEMORIES-9001", "--epic", "MEMORIES-9000",
        )
        self._assert_task(
            "MEMORIES-9002",
            "task/MEMORIES-9002-tai-anh-len",
            f"origin/{story_branch}",
        )


if __name__ == "__main__":
    unittest.main()
