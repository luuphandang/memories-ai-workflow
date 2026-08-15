# TencentDB Agent Memory adapter

Concrete `MemoryProvider` implementation (`ai/bin/lib/memory/tencentdb.py`) for the
already-cloned `services/tencentdb-agent-memory/`. See `upstream-notes.md` for what was
verified directly from upstream source, and `../memory/provider-contract.md` for the
vendor-neutral contract this adapter implements.

## Running the service locally

```bash
cd services/tencentdb-agent-memory/deploy/global-images
cp .env.example .env
$EDITOR .env
./start-all.sh
```

This starts MemoryCore (port 8420) and MemoryKnowledge (port 8424) among others. See
`upstream-notes.md` for the full port table.

## Configuring this integration

Copy the `AI_MEMORY_*` block from `.env.ai.example` into `.env.ai` and adjust:

```bash
export AI_MEMORY_ENABLED="true"          # off by default; must be explicitly turned on
export AI_MEMORY_PROVIDER="tencentdb"
export AI_MEMORY_SERVICE_ROOT="$AI_WORKSPACE_ROOT/services/tencentdb-agent-memory"
export AI_MEMORY_BASE_URL="http://127.0.0.1:8420"
export AI_MEMORY_KNOWLEDGE_BASE_URL="http://127.0.0.1:8424"
export AI_MEMORY_TIMEOUT_SECONDS="10"
export AI_MEMORY_API_KEY=""              # set a real key locally only; never commit one
export AI_MEMORY_SERVICE_ID="default"     # tenant/instance routing key
export AI_MEMORY_TEAM_ID="default"        # workspace team namespace
export AI_MEMORY_AGENT_ID="claude"        # agent namespace
export AI_MEMORY_USER_ID="workspace"      # workspace identity
```

Then:

```bash
source .env.ai
./ai/bin/ai memory health
```

The Core v3 and Knowledge data-plane endpoints require a bearer API key. A health
endpoint may still be reachable without one, but `memory health` reports recall,
publish, skill, and CodeGraph capabilities as unavailable until the key is configured.

## Files here

| Path | Purpose |
|---|---|
| `upstream-notes.md` | Verified upstream facts (ports, auth, endpoints, limitations) |
| `config.yaml` | Provider defaults: enabled/required/timeout/recall size/fallback |
| `asset-mapping.yaml` | Which local paths map to which TencentDB asset type |
| `recall-policy.yaml` | Machine form of `../memory/policies/recall-policy.md` |
| `publish-policy.yaml` | Category-inference fallback table for publish |
| `local-index/superseded-assets.json` | Local supersession ledger (upstream has no deprecate API) |
| `prompts/recall.md` | Short guidance fragment surfaced to agents when memory is ready |
| `prompts/publish.md` | Operator-facing summary fragment for `memory-publish` output |

## Known limitation

CodeGraph sync only works for `apps/<repo>` when that repository has a public `https://`
origin remote — upstream cannot index an arbitrary local path. See "Hard limitation" in
`upstream-notes.md`.
