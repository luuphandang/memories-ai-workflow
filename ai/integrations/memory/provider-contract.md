# MemoryProvider contract

Defined in `ai/bin/lib/memory/provider.py` and `ai/bin/lib/memory/models.py`. This is
the only interface `ai/bin/*` scripts talk to; no script names a vendor directly except
`tencentdb.py` itself.

## Methods

```python
class MemoryProvider(abc.ABC):
    def health(self) -> MemoryHealth: ...
    def recall(self, query: MemoryQuery) -> MemorySnapshot: ...
    def publish(self, request: MemoryPublishRequest) -> MemoryPublishResult: ...
    def search_code(self, ref: RepositoryMemoryRef, query: str) -> list[MemoryItem]: ...
    def sync_repository(self, ref: RepositoryMemoryRef) -> RepositoryMemoryRef: ...
```

Every method must fail soft (return a result describing unavailability) when called in
`optional` mode, and may raise when called in `required` mode — see `mode()`/precedence
below. No method may raise for reasons a caller can't recover from without a stack
trace showing up in a task artifact; wrap transport errors into the result types.

## Data models

- `RepositoryMemoryRef` — `repo`, `path` (workspace-relative, e.g. `apps/backend`),
  `remote_url` (`None` if no usable public HTTPS remote), `supports_code_graph` (bool),
  `reason` (why `supports_code_graph` is `False`, when applicable).
- `MemoryQuery` — `task_id`, `implementation_cycle`, `change_cycle`, `text`
  (deterministic query string), `repositories`, `asset_types`, `max_items`.
- `MemoryItem` — `provider`, `asset_type` (`wiki | code_graph | skill | chat_memory`),
  `asset_id`, `title`, `score` (optional — only populated if the backend actually
  returns one), `source` (evidence pointer), `version` (optional revision string),
  `retrieved_at`.
- `MemorySnapshot` — `task_id`, `implementation_cycle`, `change_cycle`, `provider`,
  `query`, `items`, `generated_at`, `content_sha256`, `available`, `fallback`,
  `error_code`.
- `MemoryPublishEntry` — `category` (one of the 8 durable-knowledge categories, see
  `publish-policy.md`), `target`, `summary`, `content`, `evidence`, `supersedes`.
- `MemoryPublishRequest` / `MemoryPublishResult` — batch publish in/out.
- `MemoryHealth` — `provider`, `available`, `api_version`, `wiki_supported`,
  `skill_supported`, `code_graph_supported`, `recall_supported`, `publish_supported`,
  `reason`.

**No field may be invented beyond what a real backend confirms it supports.** If a
capability is unverified (e.g. a similarity score on recall results), the field stays
optional/`None` rather than being assumed present. `ai/integrations/tencentdb-memory/
upstream-notes.md` records exactly which fields TencentDB's backend actually returns.

## Enable/required precedence

1. `AI_MEMORY_ENABLED` (env, default `false`) is the hard kill switch. `false` always
   means disabled, regardless of any `task.yaml` override.
2. `ai/integrations/tencentdb-memory/config.yaml` (`enabled`, `required`) is the base
   layer once the env switch is on.
3. `task.yaml`'s optional `memory:` block (`ai/schemas/task.schema.json`) can further
   narrow — turn memory off for one task, or mark it `required` — but can never force
   memory on past the env kill switch.

## Required vs optional behavior

- `required: false` (default) + backend unavailable → recall proceeds with
  `available: false`, `fallback: "static_context"`, `error_code: "MEMORY_UNAVAILABLE"`;
  `prepare-context` warns but does not fail the task.
- `required: true` + backend unavailable → `prepare-context` adds a reason to its
  existing `missing` list and raises `SystemExit`, exactly like a missing context file
  or worktree — the task is blocked through the same mechanism already used for those.

## Selecting a provider

`AI_MEMORY_PROVIDER` selects the implementation via `get_provider()`:
`tencentdb` (default, real backend) or `fake` (deterministic, offline — used by
`self-check --smoke` and unit tests, never by a real task run unless explicitly set).
