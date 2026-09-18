# Concurrency Coordination Architecture

## Scope

This document fixes the semantics used by future concurrency phases. It does not make
agent prompts an authority boundary: scripts and deterministic gates must enforce every
safety invariant.

## Reused components

- `ai_common.atomic_write`, `write_json` and `write_yaml` are the atomic file-publication base.
- `docker_infra.acquire_heavy_validation_slot` is the existing local `flock` pattern.
- `execution-plan.json` remains the orchestrator-owned slice plan.
- `state.yaml` remains the task lifecycle source of truth.
- Context lock, validation summary, dirty-worktree hash and provenance remain freshness inputs.
- `run-task`, `run-claude`, validation, review and finalize remain lifecycle checkpoints.

## Safety invariants

1. A canonical writable worktree has at most one active writer.
2. A task-state mutation is serialized and cannot silently overwrite a newer revision.
3. The coordination event log is append-only; registries and graphs are rebuildable projections.
4. A resource lock answers who may mutate a resource. A capability claim answers who owns
   delivery of a semantic function. Neither implies the other.
5. Agents never merge, cherry-pick, rebase, checkout another branch or manage worktrees.
6. A review pass does not imply merge readiness. Integration uses an exact target SHA and a
   combined-tree validation result.

## Canonical identities

- Task: existing validated Jira-style task ID.
- Repository: configured repository name plus a digest of Git's canonical common directory;
  all worktrees of one repository therefore share the same identity.
- Resource: `repository:path` with optional `#symbol`. Paths are repository-relative and may
  not escape using `..`.
- Capability: lowercase semantic namespace such as `user.create` or `notification.send`.
- Run/session/lease/event: UUID. Later phases add persistence and fencing semantics.

## Authoritative state ownership

| State | Authority |
|---|---|
| Task lifecycle | `state.yaml`, mutated by orchestrator scripts |
| Slice plan | versioned `execution-plan.json`, mutated only by the plan reconciler |
| Source | registered Git worktree snapshot |
| Validation freshness | validation summary plus HEAD and dirty snapshot |
| Artifact provenance | provenance manifest |
| Coordination history | append-only event log introduced in Phase 1 |
| Capability/dependency graph | rebuildable projections introduced in Phase 3 |

Narrative handoff/progress files may explain state but never override these authorities.

## Compatibility and authority policy

Legacy tasks without `coordination` fields use:

```yaml
dynamic_producer: proposal_only
target_ref: origin/master
```

A missing capability may always create a proposal. Automatic producer-task creation is only
allowed when `dynamic_producer: auto_create_in_scope` and the new work stays inside existing
requirements, repositories and authority. Product/architecture/scope expansion transitions
the consumer to `needs_input`; it is never inferred from an agent request.

New worktree registrations store both legacy `base_ref` and explicit `target_ref`. Existing
records containing only `base_ref` remain valid.
