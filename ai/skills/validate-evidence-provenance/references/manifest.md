# Provenance manifest

Use this minimal JSON shape:

```json
{
  "task_id": "PROJ-1000",
  "implementation_cycle": 1,
  "change_cycle": 0,
  "generated_at": "2026-01-01T00:00:00Z",
  "command": "exact command",
  "preconditions": [{"name": "API reachable", "passed": true}],
  "inputs": [{"path": "relative/input", "sha256": "..."}],
  "artifacts": [{"path": "relative/output", "sha256": "..."}]
}
```

Resolve paths relative to the manifest. Include migration and seed files for database evidence; include capture scripts, fixtures, route source and seed/API precondition output for UI evidence.

The durable copy lives under `ai/tasks/<TASK-ID>/evidence/`. Publish it to
`worktrees/<TASK-ID>/.ai/validation/` with `scripts/sync_provenance.py`; do not maintain two
manifests manually. The published copy may use absolute paths so the same evidence resolves from
the runtime directory.
