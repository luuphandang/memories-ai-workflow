# Báo cáo MEMORIES-0003 — [FE] Implement Prototype Pages into Frontend Application

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0003/task.md`

## Nội dung triển khai

Implemented all 6 prototype routes (/, /mau-thiep, /qua-ky-niem, /dat-lam-rieng, /gio-hang, /tao-thiep) in apps/public-web on a new MEMORIES design foundation (rebranded palette + semantic tokens scoped to public-web only, next/font typography, 9 accessible packages/ui primitives with owner-package unit tests) and a shared public shell (SiteHeader/SiteFooter/mobile drawer/bottom nav, in-memory ShopProvider for cart+favorites). Typed mock data and shared shop components back all 6 pages. This is the 3rd implementation attempt on this task: attempt 2 shipped all 6 routes but left 3 acceptance slices as 'partial' with 4 documented gaps (packages/ui had no test infra; gio-hang used inline <select>s instead of the prototype's picker modals and had no personalization-edit modal; /mau-thiep and /qua-ky-niem's mobile filters rendered as a stacked block instead of a slide-up drawer; /tao-thiep's editor had no starting-template picker or layer z-order controls). This attempt closed all 4 gaps with real implementation: packages/ui now has vitest+jsdom+testing-library and 25 unit tests across all 9 primitives; gio-hang's wrap/gift-card pickers are now Dialog-based visual-grid modals plus a personalization-edit modal (backed by a new ShopProvider.updatePersonalization action); /mau-thiep and /qua-ky-niem's mobile filters now open in a bottom Drawer (shared Dialog/Drawer focus-trap) while the desktop sidebar is unchanged; /tao-thiep gained a starting-template picker modal on entry and bring-to-front/send-to-back layer-order controls. lint/typecheck/test/build pass for public-web, admin-web (unaffected) and ui; all 3 required deterministic skill scripts pass. Residual, explicitly out-of-scope gaps (multi-select and a persistent layers-list panel in the editor; dat-lam-rieng's portfolio image-carousel detail modal) are documented in docs/prototype-inventory.md and do not block any acceptance criterion, which asks for the prototypes' core interactions rather than 1:1 engine parity. This is a follow-up remediation pass responding to review cycle 3's fix request, which flagged 3 major issues with the prior handoff rather than the implementation itself: (1) execution-plan.json still showed every slice 'pending' while implementation.json claimed 'implemented' -- fixed by syncing execution-plan.json's slice/plan status to 'completed' now that the underlying work is genuinely done. (2) The fidelity evidence was self-contradictory: acceptance-evidence.json said no browser screenshot tool was available and comparison was code/DOM-only, while the same validation directory already held 33 real reference/actual screenshot pairs and a matrix.json that hardcoded every entry as 'passed' without ever diffing them -- investigation found capture-fidelity.mjs has a 'FIDELITY_MATRIX_ONLY' shortcut mode that writes a fully-'passed' matrix.json without comparing any pixels, which is what had actually produced it. This pass wrote a real (pure-stdlib, no PIL/ImageMagick available) PNG pixel-grid comparison script, ran it against all 33 existing pairs, and found one of the 33 'actual' screenshots (tao-thiep-populated-1440x900.png) was literally a Chrome 'ERR_CONNECTION_REFUSED' page, not the app -- the dev server was evidently down during that earlier capture. That one screenshot was recaptured for real (started the public-web dev server + a headless Chrome with --remote-debugging-port=9222, reused the existing capture-fidelity.mjs flow) and now shows the actual editor canvas. The comparison now honestly reports 31/33 passed and 2 failed (qua-ky-niem's quick-view modal at 768x1024/1440x900 is a real, measured layout difference vs the prototype's full-bleed gallery -- documented in docs/prototype-inventory.md and left as a known, reviewer-facing gap rather than silently marked passed). (3) The public-web test suite had no route-render test for any of the 6 required pages, no home-page section coverage and no /mau-thiep CardCatalog test -- added test/routes.spec.tsx (smoke-renders all 6 App Router pages) and test/card-catalog.spec.tsx (search/empty-state/mobile-filter-drawer/preview-dialog, mirroring the existing GiftCatalog test pattern), bringing public-web to 9 test files / 28 tests. This is a 4th remediation attempt (workflow-tracked as implementation attempt 7) responding to review cycle 4's fix request, which found 2 major issues: (1) the gift quick-view modal (components/gift-products/quick-view-dialog.tsx) substantially diverged from the qua-ky-niem prototype's gallery/detail hierarchy at 768x1024 and 1440x900 -- traced to a real responsive bug, not a cosmetic one: the two-column gallery/info split kicked in at Tailwind's `sm` breakpoint (640px) instead of matching the prototype's own 900px collapse point, and the image column lost its aspect-square constraint at that breakpoint (`sm:aspect-auto`), letting the CSS-grid row stretch the image to match a tall info column's height and produce an oversized, cropped hero image that pushed the actual product form off the captured viewport. Fixed by moving the split to `lg` (1024px), keeping the image permanently aspect-square, widening the dialog to `max-w-[960px]` with a `1fr/1.1fr` column ratio matching the prototype's `.qv-modal`, adding a padded ivory gallery panel, and surfacing the product rating and a Chất liệu/Chuẩn bị specs list (both already present in the GiftProduct mock type but previously unused here) so the info column's content hierarchy matches the prototype's `qv-info` block. Re-captured and re-compared: mean_cell_color_distance dropped from 102.27/95.52 (failed) to 26.08/54.8 (passed) at 768x1024/1440x900; all 33/33 fidelity matrix entries now report 'passed'. (2) The task's own delivery-gates/acceptance-evidence reported the responsive/fidelity slice as 'passed' while matrix.json held 2 recorded 'failed' entries -- a self-contradiction the fix request asked to close by making 'the fidelity checker' reject non-passing entries. Rather than modifying the shared, hash-locked ai/skills/review-frontend-ui-fidelity/scripts/check_fidelity_matrix.py (a shape-only checker that intentionally allows a documented 'failed' status per its own SKILL.md, and whose behavior is shared by every task using that skill), this attempt added a task-owned stricter gate, worktrees/MEMORIES-0003/.ai/validation/check-fidelity-all-passed.py, which fails the build if any required matrix entry is not literally 'passed'. It now runs alongside the shared shape checker and reports PASSED (33/33). acceptance-evidence.json, delivery-gates.json, summary.json and frontend.json were regenerated from fresh lint/typecheck/test/build/skill-script runs so every evidence file agrees with the real, current state. This is a 5th remediation attempt (workflow-tracked as implementation attempt 8) responding to review cycle 5's fix request, which found 1 major issue: a repository-wide brand scan still matched the old prototype brand name (acceptance criterion 18's prohibited spelling) in this task's own created source and documentation -- a doc comment in packages/design-system/src/tokens.css:45 attributing the palette's origin, and three prose references in docs/prototype-inventory.md naming actual legacy-branded prototype filenames (a superseded logo asset, and the editor's legacy JS engine file, twice). Fixed by rewording all four to describe the same provenance (rebranded / ported from the prototypes' pre-existing legacy brand) without spelling the old brand name, and by fixing the same pattern found afterwards in this handoff's own text and in worktrees/MEMORIES-0003/.ai/validation/skills/acceptance-evidence.json. A repository-wide case-insensitive brand-name scan across the frontend worktree and .ai/validation now returns zero matches (excluding the prototype/ source tree itself, which task.md forbids modifying, and past session-exchange transcripts/fix-request documents, which are logs/inputs rather than task-created deliverables). No code, route, or test behavior changed this cycle; lint/typecheck/test/build and every deterministic skill/fidelity gate were re-run and still pass unchanged.

## Repository đã thay đổi

### frontend

- `.env.example`
- `apps/admin-web/app/(auth)/login/page.tsx`
- `apps/admin-web/app/not-found.tsx`
- `apps/admin-web/app/page.tsx`
- `apps/admin-web/app/providers.tsx`
- `apps/admin-web/components/auth-guard.tsx`
- `apps/admin-web/components/dashboard-nav.tsx`
- `apps/admin-web/lib/routes.ts`
- `apps/public-web/app/(auth)/login/page.tsx`
- `apps/public-web/app/(marketing)/dat-lam-rieng/page.tsx`
- `apps/public-web/app/(marketing)/gio-hang/page.tsx`
- `apps/public-web/app/(marketing)/layout.tsx`
- `apps/public-web/app/(marketing)/mau-thiep/page.tsx`
- `apps/public-web/app/(marketing)/page.tsx`
- `apps/public-web/app/(marketing)/qua-ky-niem/page.tsx`
- `apps/public-web/app/favicon.ico`
- `apps/public-web/app/fonts.ts`
- `apps/public-web/app/globals.css`
- `apps/public-web/app/layout.tsx`
- `apps/public-web/app/manifest.ts`
- `apps/public-web/app/not-found.tsx`
- `apps/public-web/app/providers.tsx`
- `apps/public-web/app/robots.ts`
- `apps/public-web/app/sitemap.ts`
- `apps/public-web/app/tao-thiep/layout.tsx`
- `apps/public-web/app/tao-thiep/page.tsx`
- `apps/public-web/components/card-templates/card-catalog.tsx`
- `apps/public-web/components/card-templates/template-preview-dialog.tsx`
- `apps/public-web/components/cart/cart-item-row.tsx`
- `apps/public-web/components/cart/cart-summary.tsx`
- `apps/public-web/components/cart/cart-view.tsx`
- `apps/public-web/components/cart/gift-card-picker-dialog.tsx`
- `apps/public-web/components/cart/wrap-picker-dialog.tsx`
- `apps/public-web/components/common/breadcrumb.tsx`
- `apps/public-web/components/common/empty-state.tsx`
- `apps/public-web/components/common/price.tsx`
- `apps/public-web/components/common/section-heading.tsx`
- `apps/public-web/components/custom-order/custom-order-form.tsx`
- `apps/public-web/components/custom-order/faq-section.tsx`
- `apps/public-web/components/custom-order/portfolio-section.tsx`
- `apps/public-web/components/editor/editor-element.tsx`
- `apps/public-web/components/editor/editor-view.tsx`
- `apps/public-web/components/editor/use-card-editor.ts`
- `apps/public-web/components/gift-products/gift-catalog.tsx`
- `apps/public-web/components/gift-products/quick-view-dialog.tsx`
- `apps/public-web/components/home/custom-order-banner.tsx`
- `apps/public-web/components/home/final-cta.tsx`
- `apps/public-web/components/home/gifts-teaser.tsx`
- `apps/public-web/components/home/hero.tsx`
- `apps/public-web/components/home/templates-teaser.tsx`
- `apps/public-web/components/home/testimonials-section.tsx`
- `apps/public-web/components/icon-link.tsx`
- `apps/public-web/components/icons.tsx`
- `apps/public-web/components/mobile-bottom-nav.tsx`
- `apps/public-web/components/shop/product-card.tsx`
- `apps/public-web/components/shop/template-card.tsx`
- `apps/public-web/components/shop/template-thumbnail.tsx`
- `apps/public-web/components/site-footer.tsx`
- `apps/public-web/components/site-header.tsx`
- `apps/public-web/lib/brand.ts`
- `apps/public-web/lib/cart-totals.ts`
- `apps/public-web/lib/mock/card-templates.ts`
- `apps/public-web/lib/mock/cart.ts`
- `apps/public-web/lib/mock/custom-order.ts`
- `apps/public-web/lib/mock/gift-products.ts`
- `apps/public-web/lib/mock/reviews.ts`
- `apps/public-web/lib/mock/swatches.ts`
- `apps/public-web/lib/nav.ts`
- `apps/public-web/lib/routes.ts`
- `apps/public-web/lib/store/shop-store.tsx`
- `apps/public-web/lib/types/card-template.ts`
- `apps/public-web/lib/types/cart.ts`
- `apps/public-web/lib/types/custom-order.ts`
- `apps/public-web/lib/types/editor.ts`
- `apps/public-web/lib/types/gift-product.ts`
- `apps/public-web/lib/types/review.ts`
- `apps/public-web/public/brand/memories-logo.png`
- `apps/public-web/public/cart/card-dieuchua.jpg`
- `apps/public-web/public/cart/card-loichuc.jpg`
- `apps/public-web/public/cart/card-nang.jpg`
- `apps/public-web/public/cart/card-ngay.jpg`
- `apps/public-web/public/cart/goiy-hoa-kho.jpg`
- `apps/public-web/public/cart/goiy-hop-qua.jpg`
- `apps/public-web/public/cart/goiy-qr-album.jpg`
- `apps/public-web/public/cart/goiy-the-ngay.jpg`
- `apps/public-web/public/cart/goiy-thiep-in.jpg`
- `apps/public-web/public/cart/sp-den-khac.jpg`
- `apps/public-web/public/cart/sp-hoa-kem.jpg`
- `apps/public-web/public/cart/sp-hop-ky-niem.jpg`
- `apps/public-web/public/cart/sp-khung-anh.jpg`
- `apps/public-web/public/cart/sp-mo-hinh.jpg`
- `apps/public-web/public/cart/wrap-box.jpg`
- `apps/public-web/public/cart/wrap-paper.jpg`
- `apps/public-web/public/cart/wrap-premium.jpg`
- `apps/public-web/public/gifts/sp-01.png`
- `apps/public-web/public/gifts/sp-02.png`
- `apps/public-web/public/gifts/sp-03.png`
- `apps/public-web/public/gifts/sp-04.png`
- `apps/public-web/public/gifts/sp-05.png`
- `apps/public-web/public/gifts/sp-06.png`
- `apps/public-web/public/gifts/sp-07.png`
- `apps/public-web/public/gifts/sp-08.png`
- `apps/public-web/public/gifts/sp-09.png`
- `apps/public-web/public/gifts/sp-10.png`
- `apps/public-web/public/gifts/sp-11.png`
- `apps/public-web/public/gifts/sp-12.png`
- `apps/public-web/public/gifts/sp-13.png`
- `apps/public-web/public/gifts/sp-14.png`
- `apps/public-web/public/gifts/sp-15.png`
- `apps/public-web/public/gifts/sp-16.png`
- `apps/public-web/public/marketing/bst-nguoi-thuong.png`
- `apps/public-web/public/marketing/bst-theo-anh.png`
- `apps/public-web/public/marketing/bst-thu-cong.png`
- `apps/public-web/public/marketing/chi-tiet-hop.png`
- `apps/public-web/public/marketing/chi-tiet-ruy-bang.png`
- `apps/public-web/public/marketing/chi-tiet-thiep.png`
- `apps/public-web/public/marketing/hero-hop-qua.png`
- `apps/public-web/public/marketing/hero-khung-anh.png`
- `apps/public-web/public/marketing/hero-thiep-qr.png`
- `apps/public-web/public/marketing/sec-dat-lam-rieng.png`
- `apps/public-web/public/marketing/sec-qr-phone.png`
- `apps/public-web/test/card-catalog.spec.tsx`
- `apps/public-web/test/cart-item-personalization.spec.tsx`
- `apps/public-web/test/cart-view.spec.tsx`
- `apps/public-web/test/custom-order-form.spec.tsx`
- `apps/public-web/test/editor-view.spec.tsx`
- `apps/public-web/test/gift-catalog.spec.tsx`
- `apps/public-web/test/routes.spec.tsx`
- `apps/public-web/test/site-header.spec.tsx`
- `docs/prototype-inventory.md`
- `packages/api-client/src/index.ts`
- `packages/api-client/src/media-client.ts`
- `packages/api-client/src/routes.ts`
- `packages/config/src/env.ts`
- `packages/config/test/env.spec.ts`
- `packages/design-system/src/tokens.css`
- `packages/design-system/tailwind-preset.js`
- `packages/ui/package.json`
- `packages/ui/tsconfig.json`
- `packages/ui/vitest.config.ts`
- `packages/ui/src/components/badge.tsx`
- `packages/ui/src/components/carousel.tsx`
- `packages/ui/src/components/dialog.tsx`
- `packages/ui/src/components/drawer.tsx`
- `packages/ui/src/components/form-field.tsx`
- `packages/ui/src/components/icon-button.tsx`
- `packages/ui/src/components/quantity-input.tsx`
- `packages/ui/src/components/select.tsx`
- `packages/ui/src/components/tabs.tsx`
- `packages/ui/src/hooks/use-dismissable-layer.ts`
- `packages/ui/src/index.ts`
- `packages/ui/test/setup.ts`
- `packages/ui/test/badge.spec.tsx`
- `packages/ui/test/carousel.spec.tsx`
- `packages/ui/test/dialog.spec.tsx`
- `packages/ui/test/drawer.spec.tsx`
- `packages/ui/test/form-field.spec.tsx`
- `packages/ui/test/icon-button.spec.tsx`
- `packages/ui/test/quantity-input.spec.tsx`
- `packages/ui/test/select.spec.tsx`
- `packages/ui/test/tabs.spec.tsx`


## Git diff stat

### frontend

```text
.env.example                                |  1 +
 apps/admin-web/app/(auth)/login/page.tsx    |  4 +-
 apps/admin-web/app/not-found.tsx            |  4 +-
 apps/admin-web/app/page.tsx                 |  4 +-
 apps/admin-web/app/providers.tsx            |  7 ++-
 apps/admin-web/components/auth-guard.tsx    |  4 +-
 apps/admin-web/components/dashboard-nav.tsx | 66 ++++++++++++++++++++---------
 apps/public-web/app/(auth)/login/page.tsx   |  4 +-
 apps/public-web/app/(marketing)/page.tsx    | 35 ++++++++++++---
 apps/public-web/app/globals.css             | 49 +++++++++++++++++++++
 apps/public-web/app/layout.tsx              | 31 ++++++++++----
 apps/public-web/app/manifest.ts             | 24 ++++++++---
 apps/public-web/app/not-found.tsx           |  4 +-
 apps/public-web/app/providers.tsx           |  7 ++-
 apps/public-web/app/robots.ts               |  7 ++-
 apps/public-web/app/sitemap.ts              | 21 +++++++--
 packages/api-client/src/index.ts            |  1 +
 packages/api-client/src/media-client.ts     |  7 +--
 packages/config/src/env.ts                  |  2 +
 packages/config/test/env.spec.ts            |  1 +
 packages/design-system/src/tokens.css       | 48 +++++++++++++++++++++
 packages/design-system/tailwind-preset.js   | 35 +++++++++++++++
 packages/seo/src/build-metadata.ts          |  3 +-
 packages/ui/package.json                    | 13 +++++-
 packages/ui/src/index.ts                    |  9 ++++
 packages/ui/tsconfig.json                   |  2 +-
 26 files changed, 329 insertions(+), 64 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| frontend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

Coverage is complete across all seven review passes. All prior findings are resolved, all 18 acceptance criteria pass, current-cycle lint/typecheck/test/build evidence passes, and both fidelity gates report 33/33 comparisons passed. No blocker or major finding remains; the implementation is technically ready for user acceptance.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/skills/migrate-prototype-nextjs-page/scripts/check_prototype_migration.py — not approved — The 'prototype runtime path' rule matches the literal substring 'prototype/' anywhere in source text, including doc comments that legitimately cite a prototype file for traceability (e.g. '/** Adapted from prototype/qua-ky-niem/qua-ky-niem.html's ... */'). This forced rewording comments to prose ('the qua-ky-niem prototype page's ...') to pass the gate across 3 implementation attempts. Consider excluding matches inside comment blocks, or matching only import/require/src-attribute-style references, so genuine attribution comments don't have to avoid the word 'prototype/'.
- ai/skills/establish-frontend-design-system/scripts/check_design_system_usage.py — not approved — The raw-color-repetition rule (hex value repeated >=4 times) doesn't distinguish styling values from business/mock DATA values (e.g. an array of actual hex color swatches a product genuinely offers). This task centralized repeated swatch hex values into a named lib/mock/swatches.ts to pass the gate, which is reasonable, but the checker could reduce false-positive friction by ignoring hex literals inside array-literal values assigned to a data-shaped field name (e.g. `colors:`, `swatches:`) versus className/style contexts.
- ai/repos/frontend/conventions.md — not approved — packages/ui previously had no vitest config, test script or testing-library devDependencies (unlike apps/public-web and packages/config); this task added a minimal vitest+jsdom+testing-library setup (vitest.config.ts, test/setup.ts, package.json changes) as part of closing test-v-validation. Recommend documenting this as the standard pattern for any package that owns UI primitives, so future packages don't reintroduce the same gap.
- worktrees/MEMORIES-0003/.ai/validation/capture-fidelity.mjs — not approved — This script has a 'FIDELITY_MATRIX_ONLY=1' mode that writes a fully-'passed' matrix.json for every route/viewport/state combination without ever opening a browser or comparing a single pixel -- it is purely a template-filling shortcut. That is what produced the matrix.json this review-cycle-3 fix-request flagged as contradicting acceptance-evidence.json's honest 'no comparison tool available' text from an earlier point in the same task. A real comparison script (compare-fidelity.py, added this attempt) now overwrites matrix.json's status per entry from an actual pixel-grid diff. Recommend either deleting the FIDELITY_MATRIX_ONLY shortcut entirely or renaming/gating it clearly as scaffolding-only so a future attempt cannot mistake its output for real evidence again.
- ai/skills/migrate-prototype-nextjs-page/references/route-migration-checklist.md — not approved — This task's real Major fidelity regression (quick-view modal at tablet/desktop) came from reusing a shared modal primitive's default two-column breakpoint (Tailwind `sm`, 640px) instead of checking the prototype's own CSS collapse breakpoint (900px here), combined with dropping an `aspect-square` constraint at that breakpoint, which let a CSS-grid row stretch an image to fill a tall sibling column's height. Recommend the migration checklist explicitly call out: (1) read the prototype's own @media collapse breakpoints for any multi-column dialog/panel before picking a Tailwind breakpoint utility, rather than defaulting to `sm:grid-cols-2`; (2) verify every image inside a CSS-grid two-column layout keeps an explicit aspect-ratio at every breakpoint the columns can be active, since `fill`+object-cover images silently stretch to fill whatever height grid row-stretch gives them.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
