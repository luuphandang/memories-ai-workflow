---
name: verify-implementation-handoff
description: Reconcile an AI implementation handoff with the exact tracked and untracked files in every declared task worktree. Use before implementation completion, validation, review, or retry whenever implementation.json records changed files, validation claims, migrations, counts, or knowledge updates.
---

# Verify the implementation handoff

1. Generate `repositories[].changed_files` from Git, never from memory or prose.
2. Store bare repository-relative paths only. Put cycle labels and explanations in evidence fields, not path strings.
3. Recompute migration, test, and operation counts from current files and current validation output.
4. Remove decisions and knowledge proposals that describe code no longer present.
5. Run `scripts/check_handoff.py <task-dir>` and resolve every missing, extra, malformed, or duplicate path.
6. Run the task schema and evidence-matrix validators after the exact-path check.

Do not copy a previous cycle's handoff forward without regenerating its inventory and claims.
