---
name: migrate-prototype-nextjs-page
description: Convert HTML, CSS and JavaScript prototypes into maintainable Next.js App Router pages with reusable components, typed mock data, React interactions, migrated assets, responsive behavior, accessibility and tests. Use when implementing one or more frontend routes from prototype folders, static mockups or legacy browser scripts.
---

# Migrate a prototype to a Next.js page

1. Select one route slice and create a route inventory using [route-migration-checklist.md](references/route-migration-checklist.md).
2. Reuse established tokens and primitives. Resolve missing shared foundations before composing page-specific UI.
3. Keep the page as composition and metadata; split stable feature components and typed mock models at their owning application layer.
4. Apply [dom-to-react.md](references/dom-to-react.md) to replace browser scripts with state, reducers, refs, effects, event handlers and framework APIs.
5. Prefer Server Components. Add a client boundary only around the interactive subtree that requires it.
6. Move required assets into the target application's public asset tree, deduplicate them and use framework image/font facilities when appropriate.
7. Implement loading, empty, error and edge states relevant to the route. Preserve keyboard use, focus visibility, labels and announcements.
8. Test user-visible behavior with the repository test stack. Compare the implemented route against the reference at required viewports.
9. Run `scripts/check_prototype_migration.py <frontend-worktree>` plus configured frontend validation. The checker uses `ai/tools/source-analysis` (ts-morph AST) so a `prototype/` mention in a traceability comment is never confused with a real import, and JSX `onClick` is never confused with a raw HTML `onclick=` attribute — run `npm install && npm run build` there once if it reports a missing `dist/cli.js`.
10. Record route, state and viewport evidence in the handoff before starting the next route.

Never embed the original HTML as one component, execute legacy scripts, reference prototype assets at runtime or rename the source prototype to disguise an incomplete migration.
