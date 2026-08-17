# Browser evidence — fix-request-review-006 #5

Captured 2026-08-17 with headless Chromium (system Google Chrome via Playwright) against a freshly
started `npm run dev` (`apps/public-web`, port 3100). No backend was running — the `/auth/refresh`
bootstrap call fails with `ERR_CONNECTION_REFUSED`, which is expected and doesn't block rendering;
`AuthProvider` simply defaults to signed-out, matching real first-load behavior with an unreachable
API.

- `desktop-login-open.png` — 1280x800, header user icon clicked, `AuthModal` (login view) opens.
  `document.activeElement` was captured programmatically and confirmed to be the dialog's "Đóng"
  (close) button — the initial-focus target — immediately after open.
- `desktop-register-open.png` — same viewport, after clicking "Đăng ký" inside the modal to switch
  views; shows the registration form including the optional "Địa chỉ (không bắt buộc)" field.
- `mobile-login-open.png` — 390x844, mobile bottom-nav account icon clicked, `AuthModal` opens
  full-width, not clipped, all fields/buttons reachable.

While writing the focus-lifecycle unit tests for this finding (`auth-modal.spec.tsx`,
`popover.spec.tsx`), a real bug was found and fixed in `packages/ui/src/components/dialog.tsx`:
`Dialog`'s SSR-safe `mounted` gate raced with `useDismissableLayer`'s effect — a `Dialog` that
mounts with `open` already `true` rendered null on its first commit (mounted still false), so the
focus-trap effect fired before the container DOM existed and permanently captured a null ref (its
`[open, onDismiss]` deps never change again once `mounted` flips, so the effect never re-ran to
pick up the real container). Fixed by gating the hook on `mounted && open` instead of `open` alone.
