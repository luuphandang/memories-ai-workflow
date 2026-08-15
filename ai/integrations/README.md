# Integrations

Adapter layer for external systems the AI control plane can optionally use. Nothing
under `ai/integrations/` is a source of truth: canonical knowledge stays in
`ai/shared/`, `ai/repos/`, `ai/domains/`; task state stays in `ai/tasks/<ID>/`.

## Subdirectories

| Path | Purpose |
|---|---|
| `memory/` | Vendor-neutral `MemoryProvider` contract and Claude/Codex recall/publish policy. Read this first — it defines what any memory backend may and may not do. |
| `tencentdb-memory/` | Configuration and upstream notes for the concrete TencentDB Agent Memory adapter (`ai/bin/lib/memory/tencentdb.py`). |

## Design invariant

```text
Claude / Codex
      │
      ▼
ai/bin (orchestrator: prepare-context, memory-recall, memory-publish, memory-sync)
      │
      ▼
MemoryProvider (ai/bin/lib/memory/provider.py — vendor-neutral contract)
      │
      ▼
TencentDBMemoryProvider (ai/bin/lib/memory/tencentdb.py — vendor adapter)
      │
      ▼
TencentDB Agent Memory (services/tencentdb-agent-memory/, cloned separately)
```

Swapping the backend (e.g. to Mem0 or a custom service) means adding one more
`MemoryProvider` implementation and changing `AI_MEMORY_PROVIDER`; nothing in
`ai/bin/prepare-context`, `run-claude`, or `run-codex-review` names TencentDB directly.

See `memory/README.md` for the runtime contract and `tencentdb-memory/README.md` for
how to run and configure the TencentDB backend.
