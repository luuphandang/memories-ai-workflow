# Route migration checklist

For each route, record:

- Prototype files and target `page.tsx`/layout.
- Shared shell and feature component ownership.
- Static assets, fonts and metadata.
- Initial, loading, populated, empty, error and relevant edge states.
- Every click, input, keyboard, modal, drawer, carousel, filter and persistence behavior.
- Server/client component boundary and any SSR guard.
- Required mobile, tablet and desktop evidence.
- Behavior tests and deterministic checker results.

Finish one vertical route slice before duplicating page composition across other routes.
