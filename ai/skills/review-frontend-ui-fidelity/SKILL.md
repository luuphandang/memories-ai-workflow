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
7. Run `scripts/check_fidelity_matrix.py <matrix.json>` and attach reproducible evidence paths to the review.

Do not pass a route based only on desktop happy-path screenshots. Do not require pixel identity when a documented accessibility or responsive adaptation preserves the intended design.
