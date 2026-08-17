---
name: validate-evidence-provenance
description: Prove that screenshots, migration runs, generated contracts, test logs, and other validation evidence were produced from the current source and data state. Use whenever a task creates reusable evidence, reruns validation after code, migration, seed, fixture, or capture changes, or relies on artifacts from an earlier correction cycle.
---

# Validate evidence provenance

1. Treat evidence as stale after any relevant source, migration, seed, fixture, capture-script, or configuration change.
2. Record a manifest using [manifest.md](references/manifest.md) beside the evidence.
3. Hash every evidence artifact and every input that can change its meaning.
4. Record the exact command, worktree HEAD, dirty-diff fingerprint, cycle, timestamp, and required runtime preconditions.
5. Fail capture or validation when a precondition is false; never save an error page as successful evidence.
6. Store the canonical manifest at `ai/tasks/<TASK-ID>/evidence/provenance.json`.
7. Run `scripts/sync_provenance.py <task-dir> <runtime-validation-dir>` after the final
   meaning-changing edit and immediately before handoff or review. The script validates the
   canonical manifest before atomically publishing a path-rebased runtime copy.
8. Run `scripts/check_provenance.py <runtime-validation-dir>/provenance.json` after sync.

Never repair stale evidence by recomputing hashes alone. Rerun the evidence-producing command,
update the durable manifest, then sync it. A sync failure is a real handoff failure.

Do not reuse a prior cycle's evidence merely because its filename or command is unchanged.
