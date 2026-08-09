# Security verification

Cover at least:

- Valid login/refresh/logout.
- Wrong password and unknown account without account enumeration leaks.
- Locked/inactive account.
- Expired, malformed, wrong-audience and revoked tokens.
- Missing portal permission and privilege escalation attempts.
- Duplicate normalized identifier, including concurrent registration.
- Password/token/credential absence from responses and logs.
- Transaction rollback when account/profile/role provisioning fails.

Use real database constraints and the real authentication guard in integration/E2E tests where required by project policy.
