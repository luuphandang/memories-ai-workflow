# Browser evidence — fix-request-review-009 #1 and #4

Captured 2026-08-17 with headless Chromium (system Google Chrome via Playwright) against a real,
fully provisioned isolated stack: `mem5005c9-postgres/redis/minio` (scratch host ports
25433/26380/29010-11), the real NestJS API on scratch port 23000 (migrated + seeded, MinIO buckets
provisioned via `mc mb`), and a real `apps/public-web` `next dev` server on scratch port 23100
pointed at that API (`.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:23000/api/v1`).
Geometry/reachability claims below are all asserted programmatically via Playwright
`boundingBox()`/viewport checks, not visual inspection alone — see `results.json` for the exact
numbers.

## #1 — close-button positioning (fix-request-review-009 #1)

`packages/ui/src/components/dialog.tsx`'s panel div was missing `position: relative`, so
`DialogClose`'s `absolute right-4 top-4` was contained by the `fixed inset-0` overlay two levels
up instead of the panel — rendering the × pinned to the viewport corner, not the panel corner.
Fixed by adding `relative` to the panel div.

- `desktop-login-close-button.png` / `desktop-register-close-button.png` — 1280×800: the × sits
  inside the login/register panel's top-right corner. `results.json`:
  `desktop_login_close_within_panel` / `desktop_register_close_within_panel` = `true` (the close
  button's bounding box is fully contained within the dialog panel's bounding box).
- `mobile-login-close-button.png` — 390×844: same containment, `mobile_login_close_within_panel`
  = `true`.

## #4 — signed-in account popup and mobile registration (fix-request-review-009 #4)

A real account was registered through the live `POST /auth/register` API, then signed in through
the actual UI (`LoginForm`, not token injection) to capture:

- `desktop-signed-in-popover.png` — 1280×800: header user icon → `AccountPopover` anchored at the
  trigger, "Đăng xuất" fully within the viewport (`desktop_popover_within_viewport`,
  `desktop_popover_anchored_near_trigger` = `true`).
- `mobile-signed-in-popover.png` — 390×844: mobile bottom-nav account icon → the same popover,
  anchored above the fixed bottom nav, not clipped or overlapped
  (`mobile_popover_within_viewport` = `true`).
- `mobile-after-logout.png` — clicking "Đăng xuất" in the mobile popover calls the real logout
  API and returns the UI to the signed-out state (`mobile_logout_returns_to_signed_out` = `true`).
- `mobile-register-top.png` / `mobile-register-scrolled-to-submit.png` — 390×844: every register
  field (Họ và tên, Số điện thoại, Mật khẩu, Xác nhận mật khẩu, Địa chỉ) and the submit button are
  reachable by scrolling within the modal (`mobile_register_submit_reachable` = `true`).

`results.json` contains the full set of bounding-box numbers and boolean assertions this README
summarizes.
