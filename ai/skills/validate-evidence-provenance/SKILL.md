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
6. Run `scripts/check_provenance.py <manifest.json>` immediately before handoff and review.

Do not reuse a prior cycle's evidence merely because its filename or command is unchanged.
