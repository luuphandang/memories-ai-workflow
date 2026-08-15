# Proposed update

Target: `ai/repos/frontend/testing.md`

Document three pitfalls found while rebuilding the UI-fidelity capture tooling: (1) always verify dev-server liveness with a real content check, not just an HTTP status code (a stale Next.js dev server can return 200 with a broken webpack runtime); (2) CDP's `Page.captureScreenshot` without `captureBeyondViewport`+`clip` only grabs the viewport rect, so full-page mobile/tablet states must request the full `scrollHeight` or every state clips identically; (3) a hardcoded default target URL silently drifts stale once the app's real configured port changes — even a content-based capture precondition never exercises the real target if the default points elsewhere, so pass `FRONTEND_URL`/`API_URL` explicitly.


