---
name: review-frontend-ui-fidelity
description: Review implemented frontend routes against prototype, screenshot or design references across required viewports and UI states, including visual fidelity, responsive behavior, accessibility and component architecture. Use when reviewing a prototype-to-Next.js migration or any task whose acceptance requires reproducible UI comparison evidence.
---

# Review frontend UI fidelity

1. Build the required route × viewport × state matrix from the task using [evidence-matrix.md](references/evidence-matrix.md).
2. Inspect the reference and implementation at the same viewport. Do not infer fidelity from source code alone.
3. Apply [severity-and-review-gates.md](references/severity-and-review-gates.md) to classify visual, responsive, accessibility and architecture findings.
4. Verify shared shell consistency, theme scope, asset identity, typography, spacing, control states and content hierarchy.
5. Exercise keyboard navigation and state transitions for menus, dialogs, filters, forms, cart and editors where applicable.
6. Verify implementation tests and deterministic implementation-skill evidence; distinguish missing evidence from confirmed failure.
7. Run `scripts/check_fidelity_matrix.py <matrix.json> --root <repo-root>` and attach reproducible evidence paths to the review. Every `passed` entry must carry `reference`/`actual` paths, their sha256 and a `comparison` record (`tool`, `tool_version`, `algorithm`, `threshold`, `score`) that a real comparison tool produced — never hand-write a `passed` status without one. If evidence is incomplete, use `not_verified` or `failed`, not `passed`.

Do not pass a route based only on desktop happy-path screenshots. Do not require pixel identity when a documented accessibility or responsive adaptation preserves the intended design.

Acceptance evidence (durable `ai/tasks/<id>/evidence/fidelity-matrix.json`) is additionally re-checked at finalize time with `--require-all-passed`, which refuses any entry that isn't `passed` — a matrix built only far enough to scaffold the route list can never authorize acceptance.
