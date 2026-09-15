---
name: establish-frontend-design-system
description: Establish or extend shared frontend design tokens, app-scoped themes, Tailwind mappings, typography and reusable UI primitives before page implementation. Use for frontend tasks that derive a design system from prototypes, consolidate repeated visual values, add shared components, or must prevent public-site branding from changing another app.
---

# Establish a frontend design system

1. Inventory repeated colors, typography, spacing, radii, shadows, containers and interaction states before changing pages.
2. Apply [token-and-theme-rules.md](references/token-and-theme-rules.md) to separate raw brand values from semantic component tokens and scope app-specific themes.
3. Apply [component-ownership.md](references/component-ownership.md) before placing code in the design-system package, shared UI package or application.
4. Expose tokens through the repository's CSS variables and Tailwind preset. Preserve existing consumers and verify every affected app.
5. Implement only primitives with a stable, cross-feature contract. Keep brand shell and business components inside their owning app.
6. Prefer accessible primitives and complete keyboard, focus, disabled and error states as part of the component API.
7. Run `scripts/check_design_system_usage.py <worktree>` and all configured lint, type-check, test and build commands. Always pass a frontend worktree path, never a monorepo root spanning backend. The checker classifies each raw color literal's AST context (styling vs. token definition vs. typed business/mock data) via `ai/tools/source-analysis` — run `npm install && npm run build` there once if the checker reports a missing `dist/cli.js`. Once an official baseline exists at `ai/repos/<repo>/baselines/design-system.json`, pass `--baseline <path>` so only new or growing violations fail the gate.
8. Record the token inventory, ownership decisions and cross-app regression evidence in the handoff.

Do not copy a prototype `:root` block into each page, encode business data in the design system, or globally replace tokens when a scoped public theme is required.

An official baseline (`ai/repos/<repo>/baselines/design-system.json`) is generated manually
by an operator, never automatically by a task, with
`scripts/generate_baseline.py <repo> <frontend-worktree>` after reviewing the current
violation list — it records each violation's fingerprint and occurrence count so the delta
gate can tell new/growing debt from unchanged debt. A `ruleset_version` mismatch between the
checker and the baseline always fails and asks for regeneration; regenerate deliberately, not
reflexively, since it resets what counts as "already known" debt.
