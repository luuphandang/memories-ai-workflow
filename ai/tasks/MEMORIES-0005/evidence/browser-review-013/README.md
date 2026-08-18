# Browser evidence — fix-request-review-013 #2

Captured 2026-08-17 with headless Chromium (system Google Chrome via Playwright) against a real
`apps/public-web` `next dev` server on scratch port 23100 (no backend required — the flow under
test is pure client-side focus management: opening the auth modal and switching between the
login/register views never calls the API). Assertions are captured programmatically via
`page.evaluate`/`document.activeElement`, not visual inspection alone — see `results.json` for the
exact values; screenshots corroborate visually.

## Bug

`apps/public-web/components/auth/auth-modal.tsx`'s login<->register view switch unmounted the
previously focused "Đăng ký"/"Đăng nhập" switch button along with its old view. `Dialog` stayed
open, so `useDismissableLayer`'s initial-focus effect (which only runs when the dialog opens, not
on every view swap) never re-ran, and the browser dropped `document.activeElement` to `<body>`.
From there, a forward Tab press was not intercepted by the Tab-trap keydown handler (its
boundary check only fires when the active element is the *last* item in the focusable list) and
could escape the dialog to background page content.

## Fix

`AuthModal` now holds a `ref` on `DialogTitle` (made ref-forwarding in
`packages/ui/src/components/dialog.tsx`) and calls `.focus()` on it from the view-switch handlers
— the title renders at the same JSX position in both views, so its DOM node persists across the
swap and is always a safe, in-dialog focus target (`tabIndex={-1}`, matching the existing
container-fallback pattern in `useDismissableLayer`).

## Results (`results.json`)

For both `desktop` (1280×800) and `mobile` (390×844) viewports:

- `afterToRegister`: after clicking "Đăng ký", `document.activeElement` is the dialog's `<h2>`
  title ("Tạo tài khoản mới"), contained within `[role="dialog"]` — never `<body>`.
- `afterForwardTab`: pressing Tab from the title moves to an `<input>` still inside the dialog
  (the register form's first field) — the fix does not just avoid `<body>`, forward Tab stays
  correctly trapped.
- `afterShiftTab`: pressing Shift+Tab twice (past the first item) wraps back to a focusable
  element still inside the dialog, never escaping to background content.
- `afterToLogin`: after clicking "Đăng nhập" back, `document.activeElement` is again the dialog's
  `<h2>` title ("Đăng nhập"), inside the dialog.

Screenshots: `desktop-after-switch-to-register.png`, `desktop-after-switch-back-to-login.png`,
`mobile-after-switch-to-register.png`, `mobile-after-switch-back-to-login.png`.
