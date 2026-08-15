# Recall policy — what Claude and Codex may receive

Both agents only ever read `ai/tasks/<ID>/memory/recall.json` / `recall.md`, produced
once by `prepare-context` and referenced from `context.lock.json`. Neither agent calls
a memory provider live.

## Allowed

Any `MemoryItem` that survived normalization in `recall_for_task()` — because the
snapshot writer only ever serializes typed `MemoryItem` fields (see
`provider-contract.md`), this list is enforced structurally, not by a runtime filter
that could be bypassed:

- Wiki items (accepted architecture/business/convention/known-issue knowledge already
  published from a prior completed+accepted task).
- CodeGraph items (symbol/impact knowledge for `apps/<repo>`, when supported).
- Approved skill entries.
- Accepted architecture decisions, business rules, repository conventions, known
  issues — i.e. anything that made it through `memory-publish`'s durable-knowledge
  extraction (see `publish-policy.md`), which itself only reads *approved* entries.

## Forbidden

Never present in a recall snapshot, by construction:

- Failed or unaccepted implementation output.
- Unaccepted/draft requirement text.
- Temporary assumptions from an in-progress task.
- Raw Claude or Codex reasoning / chain-of-thought.
- Secrets, API keys, credentials.
- Raw terminal/agent logs.
- Superseded memory items (filtered out via
  `ai/integrations/tencentdb-memory/local-index/superseded-assets.json` before the
  snapshot is written).

## Same-provider, different agent

Claude and Codex may read the same factual snapshot (`recall.json`/`recall.md`) — it
contains only normalized, published, non-superseded `MemoryItem`s. Neither agent's own
transient reasoning is ever written into that snapshot, so there is no cross-agent
reasoning leak even though both read the same file.
