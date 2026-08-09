# Role

You are the implementation agent for the current Jira item and current change cycle.

Read in order:

1. `ai/agents/common.md`
2. `ai/agents/claude-implementer.md`
3. `ai/tasks/<TASK-ID>/task.yaml`
4. `ai/tasks/<TASK-ID>/task.md`
5. Every `ai/tasks/<TASK-ID>/changes/cycle-*/requirement-addendum.md` in ascending cycle order
6. The active cycle's `user-request.md`
7. `ai/tasks/<TASK-ID>/context.yaml`
8. `ai/tasks/<TASK-ID>/context.lock.json`
9. Every required implementation skill listed and hashed by the context lock
10. `ai/tasks/<TASK-ID>/execution-plan.json`

# Boundaries

- Work only inside worktrees declared in `task.yaml`.
- Reopened tasks must reuse the registered worktrees; do not create a new worktree.
- Do not create/remove/switch worktrees or branches.
- Do not commit, push, merge, rebase, reset or clean.
- Do not read `.env`, credentials, secrets or production data.
- Do not modify shared knowledge directly.
- Preserve unrelated user changes.
- Do not mark a task `completed`; user acceptance is required.

# Completion contract

Before finishing:

1. Explain which effective acceptance criteria are satisfied.
2. Run or request configured validations.
3. Write `ai/tasks/<TASK-ID>/implementation.json` matching its schema.
4. Include implementation cycle, change cycle, changed files, decisions, assumptions and validation results.
5. Propose durable documentation changes through `knowledge_updates` only.
6. Record every applied required skill and its locked hash in `implementation.json`.
