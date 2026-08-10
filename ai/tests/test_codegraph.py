from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from lib.codegraph import (  # noqa: E402
    claude_mcp_config,
    codex_mcp_overrides,
    inspect_repository,
    prompt_guidance,
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

    def test_task_specific_mcp_configuration_uses_locked_worktree(self):
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
        self.assertEqual(server["args"][-1], "/workspace/worktrees/T-1/backend")
        self.assertIn("mcp_servers.codegraph_backend_api.args=", codex[-1])
        self.assertIn("backend-api=worktrees/T-1/backend", guidance)


if __name__ == "__main__":
    unittest.main()
