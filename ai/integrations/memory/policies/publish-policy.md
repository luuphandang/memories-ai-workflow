# Publish policy — what may become long-term memory

`memory-publish` runs only when `state.status == "completed" AND acceptance.status ==
"accepted"` (checked the same way `accept-task`/`update-knowledge` already check those
files). It is never invoked automatically by `accept-task` — it is an explicit,
separate operator step, exactly like `update-knowledge`.

## Source of publishable content

Only approved entries from `ai/tasks/<ID>/knowledge-updates.json` (the same file
`update-knowledge` already applies to `ai/shared/`, `ai/repos/`, `ai/domains/`, and
validated against the same `ai/schemas/knowledge-update.schema.json`). Never:

- Raw `task.md` / `implementation.json` / `review.json`.
- Git diffs.
- Terminal logs.
- Raw conversation transcripts.
- Claude's or Codex's internal reasoning.

## Durable-knowledge categories

Each published entry is tagged with one of:
`architecture_decision`, `business_rule`, `repository_convention`, `known_issue`,
`implementation_pattern`, `review_pattern`, `api_contract`, `source_map_knowledge`.

Category comes from `knowledge-updates.json`'s optional `category` field when present;
for older entries that predate this field, a filename-basename heuristic in
`ai/integrations/tencentdb-memory/publish-policy.yaml` is used as a fallback only.

Every published entry carries `evidence: {task_id, change_cycle, source_update_index}`
— a pointer back to its origin, never the full origin content.

## Canonical knowledge always wins

`ai/shared/`, `ai/repos/`, `ai/domains/` are authoritative. `memory-publish` runs
logically after `update-knowledge` in the completed-task workflow (see
`ai/shared/workflows/knowledge-update.md`) but never replaces it. A recalled memory
item that conflicts with canonical knowledge must be treated by the reading agent as
stale — canonical files are not overwritten from memory in either direction.

## Timing rules

- Never before user acceptance.
- Never for a correction cycle (state moves to `changes_requested_by_user`, which
  fails the `completed` precondition by construction).
- A `requirement_change` cycle after a prior acceptance produces a *new* recall and,
  on republish, marks the prior same-task/same-target entry as superseded (see
  `ai/integrations/tencentdb-memory/upstream-notes.md` for the supersession mechanism
  and its limits).
