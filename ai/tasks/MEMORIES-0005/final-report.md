# Báo cáo MEMORIES-0005 — Implement Authorize At Public Website

## Kết quả kỹ thuật

- Trạng thái workflow: `changes_requested_by_codex`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `changes_requested`
- User acceptance: `pending`

Báo cáo được sinh khi cổng kỹ thuật chưa hoàn tất hoặc ở chế độ report-only.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0005/task.md`

## Nội dung triển khai

Public-web user icon now opens an AuthModal (LOCAL phone/password login + register, Google OAuth only — Facebook is deliberately deferred/disabled on the public surface per task.md §11) when signed out and an anchored AccountPopover (Đăng xuất) when signed in, on both desktop header and mobile bottom nav via a single shared UserMenuTrigger. Backend: RegisterDto/RegisterUseCase/CreateAccountUseCase accept and persist an optional address (no migration needed); GoogleOAuthClient + OAuthLoginUseCase + OAuthController implement the full authorization-code flow for Google. FacebookOAuthClient exists as deferred, DI-registered-but-unwired code (task.md explicitly allows keeping unactivated code for a future rollout) — OAuthController.parseSocialProvider excludes `facebook` outright and identity-access.module.ts no longer includes it in the active OAuthClientRegistry, so /auth/oauth/facebook/* fails closed before any provider contact regardless of env/DI state. Fixed a pre-existing AuthProvider.isAuthenticated bug that would have made the whole feature appear permanently signed-out. Ten review cycles of fix passes since (full per-finding detail in `decisions`): cycle 3 (7 findings) moved OAuth secrets out of URLs, validated OAuth payloads at runtime, fixed a forgeable oauth=success param, made self-registration atomic, handled unconfigured providers gracefully; cycle 4 (7 findings) hardened the OAuth-race and registration-rollback e2e tests with real concurrency/table-count proof, added a configured-Facebook e2e path, logout-failure and duplicate-submit UI tests, and fixed an e2e port-flake; cycle 6 (5 findings) made the Facebook Graph API version config-driven (v19.0 was retired), made first-time OAuth provisioning atomic with session issuance, fixed refresh rotation mislabeling social sessions as LOCAL, regenerated a complete provenance manifest, and fixed a real Dialog focus-trap bug; cycle 9 (4 findings) fixed a Dialog panel-positioning bug (DialogClose rendered against the viewport instead of the panel), regenerated stale runtime provenance/summary/database-invariants artifacts, built a Facebook OAuth v26.0 contract harness anchored to Meta's official docs (no real credentials available for a live sandbox) which also surfaced and fixed a malformed-state-cookie 500 bug, and captured new real-browser evidence for the signed-in popover and mobile registration; cycle 10 (3 major findings + 1 missing-evidence item) fixed a real credential-leak bug (OAuth authorization codes/state were still fully readable via `req.url` in every centralized log line despite `req.query` redaction), replaced the self-referential Facebook contract test with one bound to a hash-verified pinned-commit snapshot of Meta's own official open-source Graph API SDK (developers.facebook.com/graph.facebook.com are confirmed DNS-blocked from this sandbox, so GitHub was used instead), fixed the standalone `/login` route which still posted the legacy `{email,password}` shape the backend has never accepted, and added a negative test for a provider error paired with a missing/mismatched state; cycle 13 (2 major findings) resolved a review-cycle-9/10/11 loop that kept re-verifying an unverifiable Facebook transport contract by instead applying task.md's own explicit, always-effective requirement — Facebook must be fully disabled on the public surface, not merely 'best-effort contract-verified' — so `OAuthController.parseSocialProvider` now excludes `facebook` outright (fails closed before any provider contact or `OAuthClientRegistry` resolution, regardless of env/DI state) and `identity-access.module.ts` no longer includes `FacebookOAuthClient` in the active `OAuthClientRegistry`; the self-contradictory contract spec (its own pinned fixture documented GET while the spec asserted POST) and its fixtures were deleted, replaced by e2e tests proving the public Facebook routes fail closed even with a fully working client DI-overridden in; separately, fixed a real focus-management bug in `AuthModal` where switching login&lt;-&gt;register unmounted the focused view-switch button and dropped `document.activeElement` to `&lt;body&gt;`, letting a forward Tab escape the dialog — fixed by focusing the (now ref-forwarding) `DialogTitle`, which persists across the view swap, from the switch handlers; verified via new jsdom tests and real-browser (Playwright) evidence at desktop+mobile. Cycle 15 (2 major findings) fixed a real OAuth CSRF/state-bypass bug — OAuthController.callback checked providerError before validating state/cookieState, so a forged cross-site ?error=access_denied callback with missing/mismatched state was accepted as a clean denial and consumed the victim's state cookie; reordered so state is validated before any callback outcome (success or provider-reported error) is trusted, with a new regression test proving a forged denial cannot be accepted; and recaptured desktop/mobile browser evidence as one current-cycle, provenance-bound Playwright capture (browser-review-015, 24/24 assertions true) that supersedes browser-review-009/013 and is now bound into a regenerated provenance manifest (61 inputs, 19 artifacts). Review-cycle-16 fix pass (fix-request-review-016.md, 3 major findings, full-plan scope): #1 OAuthController.callback now only consumes (reads-and-clears) the state cookie once the callback is proven to belong to the current attempt (provider supported AND state exactly matches the cookie) — closing a SameSite=Lax forged-callback bug where an invalid/mismatched/unsupported callback could evict a different, still-valid in-flight attempt's state cookie out from under it; proven with a real request.agent(...) browser-like cookie jar (built against an explicit http://localhost:<port> base URL, working around supertest's server-object form always targeting 127.0.0.1, which never matches this app's Domain=localhost cookies under real cookie-jar domain matching — see the new knowledge_updates entry). #2 added current-cycle HTTP e2e coverage for Google's provider_unavailable redirect (DI-overridden unconfigured GoogleOAuthClient exercised through the real /auth/oauth/google/start route) plus 3 new frontend oauth-redirect-handler tests (provider_unavailable message mapping, unmapped-reason generic fallback, unrecognized-oauth-status boundary case). #3 provenance.json now records per-repo source_state (HEAD, base_ref, dirty-inventory sha256 fingerprint) and binds the identity-access/user-profiles schema migrations plus the roles/permissions seed use-case as e2e/transaction dependencies (64 inputs, up from 61; 19 artifacts unchanged, all refreshed). Backend unit 310/310, e2e 142/142 (was 140/140); frontend public-web 107/107 (was 104/104), ui 37/37; full validate-code --tier full green for both repos (run twice — once before, once after fixing the new e2e test's cookie-jar/localhost-port issue found during self-review); all workspace-level deterministic checks (check_handoff, check_provenance x2, sync_provenance, build_evidence_matrix, execution-plan validation) PASSED.

Attempt 56 (review cycle 17, fix-request-review-017.md, 2 major findings, full-plan scope, sensitive auth/security correction): #1 fixed — implemented the previously-missing half of task.md §11's 'kiểm tra state/nonce' requirement: GoogleOAuthClient now requests and fully verifies a real OIDC ID token (RS256 signature against Google's live JWKS via Node's built-in crypto, trusted issuer, audience, expiry, and a nonce minted alongside state and bound 1:1 to this exact login attempt through the same state cookie) before trusting any provider identity or issuing a session — no new dependency added. #2 fixed — OAuthController.callback now allowlists only access_denied as user cancellation; every other provider error maps to a stable, safe provider_error reason instead of being misreported as cancellation, and oauth-redirect-handler.tsx now only ever acts on the literal success/error statuses (an unrecognized oauth= value is ignored, never treated as an implicit success). Backend unit 325/325 (was 310/310), e2e 148/148 (was 142/142); frontend public-web 108/108 (was 107/107). Full validate-code --tier full green for both repos plus a real npm run test:e2e run against the shared local-dev stack; all workspace-level deterministic checks (check_handoff, check_provenance, sync_provenance, check_auth_invariants, check_port_bindings, check_module_wiring, check_openapi_contract, check_frontend_security, build_evidence_matrix, execution-plan validation) PASSED — the only non-passing deterministic check remains check_design_system_usage.py's pre-existing, unrelated, already-waived #efe2cf finding. ADDENDUM (2026-08-18, out-of-band user-directed scope change, see decisions[-1]): Google OAuth is no longer exposed on the public surface either — it is now deferred/disabled using the identical mechanism as Facebook (parseSocialProvider rejects every provider; OAUTH_CLIENTS is empty; the only frontend entry point, social-login-buttons.tsx, was deleted). task.md's AC3 was rewritten to match. Facebook's status is unchanged.

## Repository đã thay đổi

### backend

- `.env.example`
- `apps/api/test/auth-flow.e2e-spec.ts`
- `apps/api/test/oauth-flow.e2e-spec.ts`
- `libs/modules/identity-access/src/application/ports/oauth-client.port.ts`
- `libs/modules/identity-access/src/application/use-cases/oauth-login.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/refresh-session.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/register.use-case.ts`
- `libs/modules/identity-access/src/identity-access.module.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-auth-identity.repository.ts`
- `libs/modules/identity-access/src/infrastructure/security/facebook-oauth.client.ts`
- `libs/modules/identity-access/src/infrastructure/security/google-oauth.client.ts`
- `libs/modules/identity-access/src/presentation/http/auth.controller.ts`
- `libs/modules/identity-access/src/presentation/http/oauth-state.helper.ts`
- `libs/modules/identity-access/src/presentation/http/oauth.controller.ts`
- `libs/modules/identity-access/src/presentation/http/register.dto.ts`
- `libs/modules/identity-access/src/public-api.ts`
- `libs/modules/identity-access/test/facebook-oauth.client.spec.ts`
- `libs/modules/identity-access/test/google-oauth.client.spec.ts`
- `libs/modules/identity-access/test/oauth-login.use-case.spec.ts`
- `libs/modules/identity-access/test/oauth-state.helper.spec.ts`
- `libs/modules/identity-access/test/register.use-case.spec.ts`
- `libs/platform/configuration/src/config/auth.config.ts`
- `libs/platform/configuration/src/public-api.ts`
- `libs/platform/configuration/src/schemas/env.schema.ts`
- `libs/platform/database/src/typeorm-unit-of-work.ts`
- `libs/platform/database/test/typeorm-unit-of-work.spec.ts`
- `libs/platform/observability/src/logger.module.ts`
- `libs/platform/observability/test/logger.module.spec.ts`
- `package.json`

### frontend

- `apps/public-web/app/(auth)/login/page.tsx`
- `apps/public-web/app/providers.tsx`
- `apps/public-web/components/auth/account-popover.tsx`
- `apps/public-web/components/auth/auth-modal.tsx`
- `apps/public-web/components/auth/login-form.tsx`
- `apps/public-web/components/auth/oauth-redirect-handler.tsx`
- `apps/public-web/components/auth/register-form.tsx`
- `apps/public-web/components/auth/user-menu-trigger.tsx`
- `apps/public-web/components/icons.tsx`
- `apps/public-web/components/mobile-bottom-nav.tsx`
- `apps/public-web/components/site-header.tsx`
- `apps/public-web/test/auth-modal.spec.tsx`
- `apps/public-web/test/auth-provider.spec.tsx`
- `apps/public-web/test/login-form.spec.tsx`
- `apps/public-web/test/login-page.spec.tsx`
- `apps/public-web/test/mobile-bottom-nav.spec.tsx`
- `apps/public-web/test/oauth-redirect-handler.spec.tsx`
- `apps/public-web/test/register-form.spec.tsx`
- `apps/public-web/test/site-header.spec.tsx`
- `apps/public-web/test/user-menu-trigger.spec.tsx`
- `packages/api-client/src/generated/schema.d.ts`
- `packages/api-client/src/routes.ts`
- `packages/api-client/test/register-dto-contract.spec.ts`
- `packages/auth/src/auth-provider.tsx`
- `packages/ui/src/components/dialog.tsx`
- `packages/ui/src/components/popover.tsx`
- `packages/ui/src/index.ts`
- `packages/ui/test/dialog.spec.tsx`
- `packages/ui/test/popover.spec.tsx`
- `packages/validation/src/auth.ts`
- `packages/validation/test/auth.spec.ts`


## Git diff stat

### backend

```text
.env.example                                       |  10 ++
 apps/api/test/auth-flow.e2e-spec.ts                | 139 +++++++++++++++++++++
 .../use-cases/refresh-session.use-case.ts          |   9 +-
 .../src/application/use-cases/register.use-case.ts |  65 +++++-----
 .../identity-access/src/identity-access.module.ts  |  26 +++-
 .../typeorm-auth-identity.repository.ts            |  23 ++--
 .../src/presentation/http/auth.controller.ts       |   1 +
 .../src/presentation/http/register.dto.ts          |   6 +
 libs/modules/identity-access/src/public-api.ts     |   5 +
 .../identity-access/test/register.use-case.spec.ts |   2 +
 .../configuration/src/config/auth.config.ts        |  49 ++++++++
 libs/platform/configuration/src/public-api.ts      |   2 +-
 .../configuration/src/schemas/env.schema.ts        |  19 +++
 libs/platform/database/src/typeorm-unit-of-work.ts |   9 ++
 .../database/test/typeorm-unit-of-work.spec.ts     |  33 +++++
 libs/platform/observability/src/logger.module.ts   |  51 ++++++++
 package.json                                       |   2 +-
 17 files changed, 409 insertions(+), 42 deletions(-)
```

### frontend

```text
apps/public-web/app/(auth)/login/page.tsx        | 70 ++++++++----------------
 apps/public-web/app/providers.tsx                |  2 +
 apps/public-web/components/icons.tsx             | 22 ++++++++
 apps/public-web/components/mobile-bottom-nav.tsx | 36 ++++++++++--
 apps/public-web/components/site-header.tsx       | 11 ++--
 apps/public-web/test/login-page.spec.tsx         | 58 ++++++++++++++------
 apps/public-web/test/site-header.spec.tsx        | 42 +++++++++++++-
 packages/api-client/src/generated/schema.d.ts    | 21 +++----
 packages/api-client/src/routes.ts                |  6 ++
 packages/auth/src/auth-provider.tsx              | 62 ++++++++++++++++++++-
 packages/ui/src/components/dialog.tsx            | 32 ++++++++---
 packages/ui/src/index.ts                         |  1 +
 packages/ui/test/dialog.spec.tsx                 | 23 +++++++-
 packages/validation/src/auth.ts                  | 27 ++++++++-
 packages/validation/test/auth.spec.ts            | 52 +++++++++++++++++-
 15 files changed, 363 insertions(+), 102 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |
| frontend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

Reviewed as Claude, standing in for Codex on this task by explicit user authorization (state.yaml agents.review=claude) — this is a real, independent review of today's diff, not a fabricated Codex verdict. Scope: an out-of-band, user-directed change deferring Google OAuth on the PUBLIC portal's public surface using the exact mechanism already applied to Facebook (parseSocialProvider rejects every provider; OAUTH_CLIENTS empty; the only frontend Google entry point deleted), plus task.md's AC3/Scope/Out-of-scope/Technical-notes rewritten to match. Full-mode review across all 60 tracked implementation files (29 backend, 31 frontend) plus 3 workspace bookkeeping files: today's 7 touched files got line-level re-examination; the other 53 were confirmed unchanged since their last passing full review and covered by today's fresh full validation run (worktrees/MEMORIES-0005/.ai/validation/summary.json, 2026-08-18T09:25:33+07:00, backend 325 unit tests + frontend 108 tests + both builds + both lints, all green) plus a real e2e run of oauth-flow.e2e-spec.ts against live Postgres (5/5). All 29 pre-cycle-18 prior findings remain resolved/not_applicable; 4 of them had their evidence note that the Google-specific HTTP-level proof they used to cite was retired as dead code, with the underlying logic still unit-tested. Of review-cycle-18's own 3 findings: #2 (Google button seam untested) is now not_applicable (the seam was deleted); #3 (stale handoff metadata, minor) is resolved (fixed in implementation.json today); #1 (stale browser evidence, major) remains open and is in fact more stale than before, since today's edits touched more of the reviewed sources without any new browser capture — this is the sole blocking finding and the reason verdict is changes_requested rather than pass. Everything else this task previously required (LOCAL auth, registration atomicity, CSRF/state/nonce, OAuth security hardening, design-system reuse) is untouched by today's diff and remains verified. One unrelated e2e test (auth-flow.e2e-spec.ts) failed once under full-suite ordering but passed in isolation and after a full stash of all uncommitted work; today's diff has no code path into it (grepped, no oauth/google/facebook reference). Read as pre-existing order/rate-limit flakiness, not caused by this diff, and recorded in test_matrix TM-010 rather than silently ignored, per the user's explicit instruction not to chase MEMORIES-0005's other open issues in this change.

- blocker: 0
- major: 1
- minor: 0
- note: 0

### [major] Current provenance still republishes stale browser evidence as current-cycle proof, and today's edits made it more stale

- Location: `workspace:ai/tasks/MEMORIES-0005/evidence/provenance.json:305`
- Evidence: browser-review-015/results.json and screenshots remain from a 14:55 capture that predates oauth.controller.ts/oauth-redirect-handler.tsx/google-oauth.client.ts edits already flagged in review-cycle-18. Today's out-of-band change (2026-08-18) edited oauth.controller.ts, identity-access.module.ts, login-form.tsx and oauth-flow.e2e-spec.ts again, and deleted social-login-buttons.tsx outright — the provenance manifest still treats the 14:55 browser artifacts as current AC9 proof. `python3 ai/bin/validate MEMORIES-0005 --tier full`, run today, independently confirms this via its own provenance-sync step: 'stale hash' for 5 of today's changed files and 'missing file' for the deleted one. ai/agents/common.md line 26 forbids reusing evidence after source changes.
- Expected fix: Recapture the desktop/mobile browser scenarios (modal open/close/Escape, focus containment, popover anchoring, logout — the login/register modal no longer has a social-button row to capture) against the final current source state and re-bind provenance.

## Knowledge updates

- ai/domains/authorization/INDEX.md — approved — Google and Facebook OAuth are both implemented end to end at the provider-client/use-case level (authorization-code flow, profile exchange, account linking by (provider, providerSubject)) but as of 2026-08-18 BOTH are deliberately deferred/disabled on the PUBLIC portal's public HTTP surface — OAuthController fails every provider closed before contacting OAuthClientRegistry, regardless of env config. Only LOCAL phone/password is live on the public surface today. Link/create rule: an AuthIdentity resolves an Account strictly by (provider, providerSubject) — provider-supplied email is never used to cross-link to an existing LOCAL or other-provider Account. Apple remains contract-only/unimplemented.
- ai/repos/frontend/INDEX.md — approved — packages/auth's AuthContextValue gained loginWithPhone(phone, password, portal)/registerLocal(input) alongside the pre-existing login(email, password) (kept only for apps/admin-web, whose real backend contract mismatch is a separate pre-existing issue out of this task's scope). isAuthenticated is now derived from access-token presence alone, not a `user` object — neither /auth/login, /auth/register nor /auth/refresh's real response includes one.
- ai/repos/frontend/INDEX.md — approved — New packages/ui primitive: Popover/PopoverItem — a lightweight, non-portaled anchored menu (position:relative parent required), for cases like an account menu where <Dialog>'s full-screen portal/overlay is the wrong shape.
- ai/repos/backend/architecture.md — approved — TypeOrmUnitOfWork.withTransaction is now reentrant: if called while a transaction is already active on the current async context (TypeOrmQueryRunnerContext), it joins that transaction (just runs the callback) instead of opening a second, independent connection/transaction. This lets a use case that calls another transactional use case (e.g. RegisterUseCase wrapping CreateAccountUseCase) get one atomic operation for free by wrapping the whole flow in its own outer withTransaction — the inner use case's own withTransaction call needs no change. Every repository already resolves its query runner through the same TypeOrmQueryRunnerContext, so this composes transparently across module boundaries.
- ai/repos/backend/architecture.md — approved — e2e testing gotcha: this backend's cookies (e.g. the OAuth state cookie, the refresh cookie) are issued with an explicit `Domain` attribute (AUTH_REFRESH_COOKIE_DOMAIN, 'localhost' in every local/test env). `supertest`'s server-object request form (`request(app.getHttpServer())`) always issues requests against the literal `127.0.0.1`, regardless of what address the server actually listens on — so a real `request.agent(...)` cookie jar (which does correct domain matching, unlike the common `.set('Cookie', ...)` header-injection pattern used throughout this suite) will silently never resend a `Domain=localhost` cookie back to a `127.0.0.1` request. A cookie-jar-based e2e test that needs real Set-Cookie/domain semantics (e.g. proving one request's response does or doesn't affect a later request's cookie, as opposed to manually forwarding a captured cookie string) must construct the agent against an explicit string base URL — `request.agent(`http://localhost:${port}`)`, with `port` read from the already-listening `httpServer.address()` — not `request.agent(app.getHttpServer())`. See apps/api/test/oauth-flow.e2e-spec.ts's 'rejects forged and unsupported-provider callbacks on the same browser session ...' test (review-cycle-16 #1).
- ai/repos/backend/architecture.md — approved — Verifying a third-party OIDC ID token (signature + issuer/audience/expiry/nonce claims) does not require adding a JWT/JWKS dependency to this backend: Node 20's built-in `node:crypto` already covers it end to end — `crypto.createPublicKey({key: jwk, format:'jwk'})` accepts a provider's published JWKS key object directly (no PEM conversion needed), and the one-shot `crypto.verify(algorithm, data, key, signature)` checks an RS256 signature without `jsonwebtoken`/`jose`/`jwks-rsa`. See GoogleOAuthClient.verifyIdToken (libs/modules/identity-access/src/infrastructure/security/google-oauth.client.ts) for the reference implementation: base64url-decode the three JWT segments, match `kid` against a cached JWKS fetch, verify the signature over `${header}.${payload}`, then check `iss`/`aud`/`exp`/`nonce` as plain claim comparisons.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
