---
name: decompose-implementation-task
description: Decompose large or cross-layer Jira work into ordered, independently verifiable vertical slices. Use before implementing epics, tasks spanning multiple modules/repositories, or work involving database, API, security, and UI changes; also use when an implementation must resume safely across sessions.
---

# Decompose implementation task

1. Read the effective requirements and locked context.
2. Inventory affected repositories, bounded contexts, external contracts and risky invariants.
3. Map every acceptance criterion to exactly one primary vertical slice; record shared criteria explicitly.
4. Order slices by dependency and risk. Complete one slice before opening the next.
5. For every slice, list code deliverables, tests, validation commands and completion evidence.
6. Write or update `ai/tasks/<TASK-ID>/execution-plan.json` using `ai/schemas/execution-plan.schema.json`.
7. Keep `implementation-progress.json.current_slice` aligned with the plan.
8. Run `scripts/validate_execution_plan.py` before implementation and after requirement changes.

Use [scope-thresholds.md](references/scope-thresholds.md) when deciding whether work must be split. Do not duplicate full task requirements in the plan; reference stable criterion identifiers or exact concise criterion text.
