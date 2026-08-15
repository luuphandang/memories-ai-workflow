# Memory (vendor-neutral)

An optional persistent memory / retrieval layer that helps Claude and Codex avoid
re-reading context they've already seen, and lets accepted implementation/review
experience survive across tasks and sessions.

Memory is **never** the source of truth. Priority order on any conflict:

```text
1. ai/shared/, ai/repos/, ai/domains/   (canonical, human-curated)
2. ai/tasks/<ID>/                        (task-level source of truth)
3. Recalled memory (ai/tasks/<ID>/memory/recall.json)
```

`ai/bin/update-knowledge` (canonical knowledge) and `ai/bin/memory-publish` (long-term
memory) are separate, sequential steps after a task is `completed` and accepted —
memory-publish never replaces update-knowledge, and reading agents must treat any
recalled item that conflicts with canonical knowledge as stale.

## Contract

See `provider-contract.md` for the `MemoryProvider` interface and data models.

## Runtime flow

```text
prepare-context
    │
    ├── memory recall (ai/bin/lib/memory:recall_for_task)
    │       ↓
    │   ai/tasks/<ID>/memory/recall.json + recall.md
    │
    ├── hash recall.json
    ▼
context.lock.json (memory: {enabled, provider, snapshot, sha256, ...})
    │
    ▼
Claude / Codex read the snapshot files only — never call the provider live.
```

Claude and Codex never import `ai/bin/lib/memory` or call a memory provider directly;
only `ai/bin/prepare-context`, `memory-health`, `memory-recall`, `memory-publish`, and
`memory-sync` do. To refresh memory mid-task, re-run `prepare-context` — it always
regenerates the snapshot.

## Enable/disable

Memory defaults to **off** (`AI_MEMORY_ENABLED=false` in `.env.ai.example`). This is a
hard global kill switch: no `task.yaml` `memory:` override can turn memory on if the
operator hasn't enabled it locally. A task can only narrow further (disable itself, or
mark itself `required` on top of an already-enabled environment). See
`provider-contract.md` for the full precedence rule.

When disabled, every existing `ai/bin/ai task ...` command behaves exactly as before
this integration was added — `prepare-context` writes `context.lock.json.memory =
{"enabled": false}` and nothing else changes.

## Policies

- `policies/recall-policy.md` — what Claude may/may not receive from recall.
- `policies/publish-policy.md` — what Codex/the operator may publish, and when.
