from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from lib.codegraph import (  # noqa: E402
    SERVE_WRAPPER,
    claude_mcp_config,
    codex_mcp_overrides,
    inspect_repository,
    inspect_task_repositories,
    prompt_guidance,
    runtime_ready_repositories,
)


class CodeGraphIntegrationTests(unittest.TestCase):
    def test_optional_mode_falls_back_when_binary_is_missing(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"AI_CODEGRAPH_MODE": "optional", "CODEGRAPH_COMMAND": "definitely-missing-codegraph"},
            clear=False,
        ):
            result = inspect_repository(Path(directory))
        self.assertFalse(result["ready"])
        self.assertIn("not available", result["reason"])

    def test_required_mode_fails_fast_when_binary_is_missing(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"AI_CODEGRAPH_MODE": "required", "CODEGRAPH_COMMAND": "definitely-missing-codegraph"},
            clear=False,
        ):
            with self.assertRaises(SystemExit):
                inspect_repository(Path(directory))

    def test_status_call_omits_unverified_json_flag_and_survives_non_json_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"AI_CODEGRAPH_MODE": "optional", "CODEGRAPH_COMMAND": "codegraph"},
            clear=False,
        ):
            (Path(directory) / ".codegraph").mkdir()
            calls: list[list[str]] = []

            def fake_run(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command, 0, "12 files indexed\n", "")

            with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
                "subprocess.run", side_effect=fake_run
            ):
                result = inspect_repository(Path(directory))
        status_call = next(call for call in calls if call[1] == "status")
        self.assertNotIn("--json", status_call)
        self.assertTrue(result["ready"])
        self.assertEqual(result["status_text"], "12 files indexed")
        self.assertNotIn("status", result)

    def test_subprocess_timeout_does_not_crash_optional_mode(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"AI_CODEGRAPH_MODE": "optional", "CODEGRAPH_COMMAND": "codegraph"},
            clear=False,
        ):
            (Path(directory) / ".codegraph").mkdir()
            with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["codegraph"], timeout=300),
            ):
                result = inspect_repository(Path(directory))
        self.assertFalse(result["ready"])
        self.assertIn("exited 124", result["reason"])

    def test_inspect_task_repositories_rejects_path_escaping_workspace(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AI_CODEGRAPH_MODE": "off"}, clear=False
        ):
            task = {"worktrees": [{"repo": "backend", "path": "../outside"}]}
            with self.assertRaises(SystemExit):
                inspect_task_repositories(Path(directory), task)

    def test_task_specific_mcp_configuration_scopes_by_cwd_not_a_path_flag(self):
        lock = {
            "repositories": {"backend-api": {"path": "worktrees/T-1/backend"}},
            "codegraph": {"repositories": {"backend-api": {"ready": True}}},
        }
        with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
            "pathlib.Path.is_dir", return_value=True
        ):
            claude = claude_mcp_config(Path("/workspace"), lock)
            codex = codex_mcp_overrides(Path("/workspace"), lock)
            guidance = prompt_guidance(Path("/workspace"), lock)
        server = claude["mcpServers"]["codegraph_backend_api"]
        self.assertEqual(server["command"], sys.executable)
        self.assertEqual(server["args"][0], str(SERVE_WRAPPER))
        self.assertEqual(server["args"][1], "/workspace/worktrees/T-1/backend")
        self.assertEqual(server["args"][2:], ["/usr/local/bin/codegraph", "serve", "--mcp"])
        self.assertNotIn("--path", server["args"])
        self.assertIn("mcp_servers.codegraph_backend_api.args=", codex[-1])
        self.assertNotIn("--path", codex[-1])
        self.assertIn("backend-api=worktrees/T-1/backend", guidance)

    def test_mcp_server_name_collision_raises(self):
        lock = {
            "repositories": {
                "backend-api": {"path": "worktrees/T-1/backend-api"},
                "backend_api": {"path": "worktrees/T-1/backend_api"},
            },
            "codegraph": {
                "repositories": {
                    "backend-api": {"ready": True},
                    "backend_api": {"ready": True},
                }
            },
        }
        with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
            "pathlib.Path.is_dir", return_value=True
        ):
            with self.assertRaises(SystemExit):
                claude_mcp_config(Path("/workspace"), lock)

    def test_stale_index_after_lock_is_excluded_at_runtime(self):
        lock = {
            "repositories": {"backend": {"path": "worktrees/T-1/backend"}},
            "codegraph": {"repositories": {"backend": {"ready": True}}},
        }
        with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
            "pathlib.Path.is_dir", return_value=False
        ), patch.dict(os.environ, {"AI_CODEGRAPH_MODE": "optional"}, clear=False):
            self.assertEqual(runtime_ready_repositories(Path("/workspace"), lock), [])

    def test_off_mode_disconnects_mcp_even_with_stale_ready_lock(self):
        lock = {
            "repositories": {"backend": {"path": "worktrees/T-1/backend"}},
            "codegraph": {"repositories": {"backend": {"ready": True}}},
        }
        with patch("lib.codegraph.executable", return_value="/usr/local/bin/codegraph"), patch(
            "pathlib.Path.is_dir", return_value=True
        ), patch.dict(os.environ, {"AI_CODEGRAPH_MODE": "off"}, clear=False):
            self.assertEqual(runtime_ready_repositories(Path("/workspace"), lock), [])
            self.assertEqual(claude_mcp_config(Path("/workspace"), lock), {"mcpServers": {}})
            self.assertEqual(codex_mcp_overrides(Path("/workspace"), lock), [])


if __name__ == "__main__":
    unittest.main()
