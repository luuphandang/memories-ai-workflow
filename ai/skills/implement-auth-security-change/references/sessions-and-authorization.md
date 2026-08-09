# Session and authorization rules

- Reject login and refresh for inactive, locked or deleted accounts.
- Bind refresh sessions to revocable server-side state and rotate/revoke according to the effective contract.
- Keep browser access tokens in memory and refresh tokens in correctly scoped HttpOnly cookies.
- Validate issuer, audience, expiry, signature, token type and token/account version.
- Authorize on backend permissions; frontend checks are presentation only.
- Distinguish public and admin portal access through explicit permission checks.
- Propagate authenticated actor/request context without trusting client-supplied actor metadata.
- Revoke or invalidate active sessions when security-sensitive account state changes.
