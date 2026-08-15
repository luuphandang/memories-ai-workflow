# Upstream notes — TencentDB Agent Memory

Findings from reading `services/tencentdb-agent-memory/` directly (already cloned,
never re-cloned, never copied into `ai/`). Not a README copy — only what this
integration relies on.

## Services and ports (local dev)

| Service | Port | Role |
|---|---|---|
| MemoryCore | 8420 | health, recall/search, capture, skill CRUD, `/v3/meta/*` identity |
| MemoryKnowledge | 8424 | Wiki, CodeGraph (`MemoryKnowledge/openapi.yaml`, Swagger at `:8424/docs`) |
| MemoryPanel | 8125 | UI — not integrated |
| MemoryProxy | 8096 | LLM request proxy — not integrated |

Start: `cd services/tencentdb-agent-memory/deploy/global-images && cp .env.example .env
&& ./start-all.sh` (or the per-service `start-memory-core.sh` / `start-memory-hub.sh`
scripts). Stop: `./stop-all.sh [--purge]`.

## Auth

Two layers (`MemoryCore/src/metadata/router/auth.ts`, `server.ts`):
- Gateway key: `Authorization: Bearer <key>`, optional, empty/disabled by default
  locally — maps to `AI_MEMORY_API_KEY`.
- User-identity key: header `x-tdai-user-key: sk-mem-<32char>`, required on `/v3/meta/*`
  endpoints.
- Multi-tenant routing: header `x-tdai-service-id`; `"default"` for local single-instance
  use.

`deploy/global-images/.admin-key` is upstream's own bootstrap file — this integration
never reads, logs, or references it.

## Endpoints actually used by this integration

| Capability | Method + path | Notes |
|---|---|---|
| Health (core) | `GET /health` | `{status, version, uptime, stores, services}`, unauthenticated |
| Health (knowledge) | `GET /health` (port 8424) | `{status, timestamp}` |
| Recall | `POST /v3/atomic/search` | Structured L1 response: `{code,message,data:{items}}` |
| Capture/publish | `POST /v3/conversation/add` | L0 write returns `data.accepted_ids`; L1 extraction is asynchronous |
| Wiki | `POST /wiki/{create,ingest,get,list,search}` | `ingest` is NOT auto-triggered by `create` — must be called explicitly |
| CodeGraph | `POST /code-graph/{create,list,sync,status,get,search}` | sync/search require `code_graph_id`; create is async |

Everything else in the upstream surface (full `/v3/skill/*` CRUD, `/v3/meta/*` org
management, MemoryProxy, MemoryPanel) is not integrated.

## Hard limitation: CodeGraph cannot index a local path

`POST /code-graph/create` requires `{team_id, repo_url, branch?}`, and `repo_url` must
be a public `https://` git remote — `GitSourceFetcher.validate()`
(`MemoryKnowledge/src/source-fetcher/git-fetcher.ts`) throws otherwise, plus an SSRF
blacklist rejects private/loopback hosts. The abstract `SourceType` enum
(`MemoryKnowledge/src/source-fetcher/types.ts`) declares `"local"` and `"ftp"` but both
are commented "未来扩展" (future extension) — **not implemented**.

Consequence: `ai/bin/memory-sync <repo>` can only actually call upstream CodeGraph
create/sync when `apps/<repo>`'s `origin` remote is a public `https://` URL. When it
isn't, `memory-sync` reports `{"supports_code_graph": false, "reason": "..."}` and
never attempts (or fakes) the call. This is the one item from the integration's
acceptance checklist that upstream genuinely cannot satisfy today.

## No asset-supersession API

Neither MemoryCore nor MemoryKnowledge documents a deprecate/archive/update-status
endpoint for any asset type (`wiki`, `code_graph`, `skill`, `chat_memory`). Supersession
(§19 of the integration spec) is therefore tracked as **local** metadata in
`ai/integrations/tencentdb-memory/local-index/superseded-assets.json`, not delegated to
the backend. `recall_for_task()` filters out anything marked `status: "superseded"`
there before writing a snapshot. Automatic supersession detection is scoped to
same-task, same-target republishes only (a `requirement_change` cycle republishing to
the same `ai/shared|repos|domains` target); cross-task supersession requires the
explicit `memory-publish --supersedes <asset_id>` flag, since `knowledge-updates.json`
has no stable cross-task identity to infer it from automatically.

## Unverified: recall response score field

Whether `/recall` / `/search/memories` responses carry a numeric similarity/score field
could not be confirmed from the source read during this survey. `MemoryItem.score` is
therefore optional and only populated if a real response actually includes one;
`config.yaml` intentionally has no `min_score` threshold. Confirm against a running
instance before adding one.

## Identity/asset model

`service_id` (`"default"` locally) → `team_id` → `agent_id`/`task_id` → `user_id`.
Assets are typed by `asset_type: skill | llm_wiki | code_graph | chat_memory`, with
`wiki_id`/`code_graph_id` prefixes `wiki-`/`cg-` from the Knowledge service. Visibility
enum: `private | team | restricted | agent | task`.

## Error envelope

Knowledge service: `{code: 0|nonzero, message, data, request_id?}`. MemoryCore v3 maps
internal error codes to HTTP status (404/403/409/401/400 per an explicit table in
`v3-meta-router.ts`). `tencentdb.py` treats any non-2xx or malformed body as
unavailable rather than raising past the caller.
