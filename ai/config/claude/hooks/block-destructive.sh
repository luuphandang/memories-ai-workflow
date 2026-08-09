#!/usr/bin/env bash
set -euo pipefail

# Claude Code hook input is JSON on stdin. This is a defense-in-depth layer;
# Claude permission deny rules and the orchestrator policy remain authoritative.
INPUT="$(cat)"
COMMAND="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command", ""))' 2>/dev/null || true)"

# Match direct commands, absolute executable paths, and common wrappers such as
# env/command/sudo. Shell indirection can never be parsed perfectly by regex,
# so this hook intentionally complements rather than replaces the deny-list.
PREFIX='(^|[;&|[:space:]])((env|command|sudo)[[:space:]]+)*([^;&|[:space:]]*/)?'
GIT_DENY="${PREFIX}git[[:space:]]+(push|commit|checkout|switch|reset|clean|rebase|merge|cherry-pick|worktree)([;&|[:space:]]|$)"
RM_DENY="${PREFIX}rm[[:space:]]+(-[^;&|[:space:]]*r[^;&|[:space:]]*f|-rf|-fr)([;&|[:space:]]|$)"

if printf '%s' "$COMMAND" | grep -Eiq "${GIT_DENY}|${RM_DENY}"; then
  echo "Blocked destructive command: $COMMAND" >&2
  exit 2
fi
exit 0
