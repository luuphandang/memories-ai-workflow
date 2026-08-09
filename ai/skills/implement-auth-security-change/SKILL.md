---
name: implement-auth-security-change
description: Implement and review authentication, authorization, identity, password, JWT, refresh-session, permission, portal-access or credential-handling changes securely. Use whenever work touches login, registration, account status, auth identities, roles, permissions, request context or sensitive security boundaries.
---

# Implement an auth security change

1. Model protected assets, actors, trust boundaries and abuse cases before coding.
2. Preserve existing security invariants and public contracts unless an effective requirement changes them.
3. Apply [identity-and-credentials.md](references/identity-and-credentials.md) for identifiers, passwords and provider identities.
4. Apply [sessions-and-authorization.md](references/sessions-and-authorization.md) for JWT, refresh sessions, account status and permissions.
5. Apply [security-verification.md](references/security-verification.md) and add negative/concurrency tests.
6. Record security decisions, database constraints and residual risks in the checkpoint and handoff.
7. Run `scripts/check_auth_invariants.py <worktree>` before completion.

Treat application-level existence checks as usability checks only. Enforce uniqueness and authorization at the authoritative boundary as well.
