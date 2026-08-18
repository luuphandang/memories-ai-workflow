# Proposed update

Target: `ai/repos/backend/architecture.md`

e2e testing gotcha: this backend's cookies (e.g. the OAuth state cookie, the refresh cookie) are issued with an explicit `Domain` attribute (AUTH_REFRESH_COOKIE_DOMAIN, 'localhost' in every local/test env). `supertest`'s server-object request form (`request(app.getHttpServer())`) always issues requests against the literal `127.0.0.1`, regardless of what address the server actually listens on — so a real `request.agent(...)` cookie jar (which does correct domain matching, unlike the common `.set('Cookie', ...)` header-injection pattern used throughout this suite) will silently never resend a `Domain=localhost` cookie back to a `127.0.0.1` request. A cookie-jar-based e2e test that needs real Set-Cookie/domain semantics (e.g. proving one request's response does or doesn't affect a later request's cookie, as opposed to manually forwarding a captured cookie string) must construct the agent against an explicit string base URL — `request.agent(`http://localhost:${port}`)`, with `port` read from the already-listening `httpServer.address()` — not `request.agent(app.getHttpServer())`. See apps/api/test/oauth-flow.e2e-spec.ts's 'rejects forged and unsupported-provider callbacks on the same browser session ...' test (review-cycle-16 #1).


