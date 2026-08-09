---
name: implement-nextjs-vertical-slice
description: Implement or modify a Next.js frontend feature as a complete vertical slice including routes, server/client component boundaries, API-client integration, TanStack Query state, React Hook Form and Zod validation, authentication handling, responsive UI, accessibility and tests. Use for public-web, admin-web, shared frontend packages, page implementation and API-driven UI work.
---

# Implement a Next.js vertical slice

1. Select one execution-plan slice and map every UI state before coding.
2. Apply [routing-and-rendering.md](references/routing-and-rendering.md) for route ownership and server/client boundaries.
3. Apply [data-and-forms.md](references/data-and-forms.md) for API clients, query keys, mutation invalidation and validation.
4. Apply [accessibility-and-testing.md](references/accessibility-and-testing.md) for keyboard, semantics, responsive behavior and tests.
5. Preserve in-memory access-token handling; never persist credentials in browser storage.
6. Run `scripts/check_frontend_security.py <worktree>` and configured frontend validation.
7. Record loading, empty, error, unauthorized and success evidence in the handoff.

Reuse the established design system and generated API client. Do not duplicate cross-app internals or bypass backend authorization with presentation-only checks.
