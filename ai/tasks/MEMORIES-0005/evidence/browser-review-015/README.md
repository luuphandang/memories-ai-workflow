# Browser evidence — fix-request-review-015 #2

Captured 2026-08-17 with headless Chromium (system Google Chrome via Playwright) against the
**final, current-cycle** sources: a real NestJS API from this worktree's backend (scratch port
23000, migrated shared local-dev Postgres/Redis/MinIO at :15432/:16379/:19000, no pending
migrations) and a real `apps/public-web` `next dev` server (scratch port 23100) pointed at that
API via `NEXT_PUBLIC_API_BASE_URL`. All accounts were created and signed in through the live UI
(`RegisterForm`/real `POST /auth/register`), never token injection. Assertions are captured
programmatically (`document.activeElement`, Playwright `boundingBox()`/viewport checks), not
visual inspection alone — see `results.json` for the exact values; screenshots corroborate
visually.

This capture supersedes the desktop/mobile scenarios previously split across
`browser-review-009/` and `browser-review-013/` (both now stale relative to this cycle's sources
per fix-request-review-015 #2) — it re-proves fix-request-review-006 #5, 009 #4, and 013 #2 in one
provenance-bound pass, plus adds explicit modal open/close/Escape coverage that no prior capture
recorded on its own.

## Scenarios and results (`results.json`)

For both `desktop` (1280×800) and `mobile` (390×844) viewports:

- **Modal open/close** — `{viewport}_modal_open_visible`: clicking the account trigger (header
  icon on desktop, bottom-nav "Tài khoản" on mobile) opens `[role="dialog"]`.
  `{viewport}_modal_closes_on_escape`: `Escape` closes it. `{viewport}_modal_closes_on_close_button`:
  the explicit × control closes it too.
- **Login↔register focus containment** (fix-request-review-006 #5 / 013 #2 retest) —
  `{viewport}_after_to_register`/`_after_to_login`: `document.activeElement` lands on the dialog's
  `<h2>` title, inside `[role="dialog"]`, never `<body>`, after each direction of the view switch.
  `{viewport}_after_forward_tab_from_register_title`: a forward Tab from the title lands on an
  `<input>` still inside the dialog. `{viewport}_after_shift_tab_wraps`: two Shift+Tab presses
  wrap back to a focusable element still inside the dialog rather than escaping.
- **Mobile registration reachability** (fix-request-review-009 #4 retest) —
  `mobile_register_top_visible_full_name` and `mobile_register_submit_reachable`: every field
  (Họ và tên, Số điện thoại, Mật khẩu, Xác nhận mật khẩu, Địa chỉ) and the submit button are
  visible/reachable within the dialog at the mobile viewport (`mobile-register-top.png` and
  `mobile-register-scrolled-to-submit.png` are visually identical here because the current
  register form fits the 390×844 viewport without scrolling — the submit button's bounding box is
  already fully within viewport bounds at rest, which is the stronger form of "reachable").
- **Signed-in popover anchoring** (fix-request-review-009 #4 retest) —
  `{viewport}_popover_within_viewport` and `{viewport}_popover_anchored_near_trigger`: after a
  real register+auto-login, clicking the account trigger opens `AccountPopover` fully inside the
  viewport, anchored near the trigger (`desktop-signed-in-popover.png`,
  `mobile-signed-in-popover.png` — the mobile popover sits above the fixed bottom nav).
- **Logout** (fix-request-review-009 #4 retest) — `{viewport}_logout_returns_to_signed_out`:
  clicking "Đăng xuất" in the popover calls the real logout API and the trigger returns to the
  signed-out ("Đăng nhập") state on both the desktop header and the mobile bottom-nav trigger
  (`desktop-after-logout.png`, `mobile-after-logout.png`).

All 24 boolean assertions in `results.json` are `true`.
