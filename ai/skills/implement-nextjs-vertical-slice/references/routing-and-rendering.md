# Routing and rendering

- Put routes in the owning application and shared primitives in public packages.
- Prefer server components until browser state/effects require a client boundary.
- Keep client boundaries small; avoid passing secrets or server-only configuration to them.
- Implement loading, empty, error, unauthorized and not-found states.
- Preserve URL state for pagination/filter/search when users must share or restore it.
- Verify responsive layout at mobile, tablet and desktop breakpoints.
