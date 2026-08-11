#!/usr/bin/env python3
"""chdir into a worktree, then exec `codegraph serve --mcp` (or similar) from there.

CodeGraph's own MCP setup docs launch `serve --mcp` with no path argument, and the
CLI reference documents no per-command project/path flag. cwd is the only known way
to scope a `serve` process to a specific repository's `.codegraph/` index, and neither
Claude Code's --mcp-config schema (stdio servers: command/args/env) nor Codex's
mcp_servers TOML override support an explicit per-server cwd, so this wrapper is
spawned as the MCP server's "command" instead.

Usage: codegraph_serve.py <worktree-path> <binary> [args...]
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: codegraph_serve.py <worktree-path> <binary> [args...]")
    worktree, binary, *rest = sys.argv[1:]
    os.chdir(worktree)
    os.execvp(binary, [binary, *rest])


if __name__ == "__main__":
    main()
