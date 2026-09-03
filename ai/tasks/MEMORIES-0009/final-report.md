# Báo cáo MEMORIES-0009 — Hoàn thiện trang chủ theo prototype và sửa header search layout shift

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0009/task.md`

## Nội dung triển khai

All 5 execution-plan slices completed across implementation cycle 1: (1) Inventory và page composition — read prototype/index/index.html fully, mapped all 11 sections in docs/prototype-inventory.md, reordered app/(marketing)/page.tsx to render them in prototype order. (2) Các element bắt buộc — rebuilt the Hero collage (8 pieces), gave Templates working filter tabs + reused catalog TemplateCard, raised Gifts to 6 full cards, added FinalCta decoration, footer newsletter validation. (3) Interaction và state — verified filter/favorite/cart/slider state was already shared via ShopProvider, added the one missing behavior (components/common/reveal.tsx, a fail-safe scroll-reveal wrapping all 11 sections). (4) Header search không gây layout shift — moved the search form out of document flow into the shared Popover (extended with role='dialog'/lockScroll={false}), zero layout impact confirmed in built HTML. (5) Responsive, accessibility và quality — added apps/public-web/test/home-page.spec.tsx (8 tests) and real-browser 375/768/1440 evidence. . Review cycles 1, 2, 3, 5 and 6 (prior attempts) fixed 4 + 1 + 3 + 3 + 2 = 13 blocking review findings in total (mobile search unreachable at 375px; Templates/Occasions/HowItWorks/FinalCta responsive-composition drift; missing CustomOrderBanner CTA; no reproducible fidelity evidence; reveal-hidden below-fold capture blanks; wrong Templates featured/filter/price data; blank below-fold fidelity photos from non-scrolling capture; a jsdom outside-click test workaround masking a real focus race; home Templates cards not matching the prototype's card hierarchy; ad-hoc /tmp capture scripts replaced with durable ai/tasks/MEMORIES-0009/evidence/scripts/*; stale freshness tags; a `lg:`-breakpoint CTA-visibility gap since further corrected by review:7:1 below; and two stale acceptance-evidence rows). Full per-finding rationale for these 13 findings is preserved in ai/tasks/MEMORIES-0009/implementation-progress.json's decisions/validation arrays and this file's own acceptance_criteria entries below (kept concise here to leave room for the current cycle 7 detail). Attempts 19 and 22 each fixed a stale-duplicate implementation-contract checklist gate (a pending finding copy left alongside a later completed copy for the same id); no source/test/evidence changes were needed either time. Review cycle 7 (attempt 21) fixed 2 findings: review:7:1 — the review:6:1 CTA-visibility fix used Tailwind's default `lg:` variant (min-width:1024px), one pixel too early versus the locked prototype's max-width:1024px-inclusive override; switched to an explicit `min-[1025px]:` arbitrary variant with `pointer-events` pairing. review:7:2 — capture-fidelity.mjs's search-open geometry check never recorded/compared window.scrollY; added scrollY tracking and a deterministic non-zero scroll position before opening search, measuring all three dismissal paths. Review cycle 8 (attempt 23) fixed review:8:1: capture-fidelity.mjs's close-button dismissal selector matched `button.textContent`, which the real icon-only close IconButton never has, so the close click was a silent no-op; fixed by selecting via accessible name scoped to the popover and adding explicit dialog-DOM-presence assertions after every open/dismiss action. Review cycle 9 (attempt 24, fix-request-review-009, evidence-only) fixed 2 findings: review:9:1 — capture-fidelity.mjs's outside-click dismissal check dispatched only a synthetic `mousedown` event and never verified a complete click lifecycle; replaced with a real CDP mousePressed+mouseReleased pointer sequence on a hit-tested inert header-background point (the header logo link was rejected as the target because its own click triggers Next.js Link's scroll-to-top-on-navigate side effect even for a same-URL click, which would contaminate the scroll-preservation assertion — confirmed via a throwaway debug script) plus a one-time click-listener assertion proving the target's own click event actually fired, not just the popover's mousedown-triggered dismissal. review:9:2 — fidelity-matrix.json was stale (cycle-6 generated_at; 3 dead artifact references to screenshots superseded by review:7:1's cta-boundary-*.png; search-open entries omitted scrollY/closed-state description); republished from this cycle's fresh capture with corrected metadata, zero dead references (verified programmatically), and scrollY/dialog-state description in every search-open entry. Current-attempt facts: [implementation-attempt: 24] [implementation-cycle: 1] [change-cycle: 0] [acceptance-state: pending] [head-revision: 6fbf43e87ba9043800872fc15fc60a756bfb8be5] [integration-state: feature_worktree_only] [provenance-inventory: 1 inputs / 46 artifacts].

## Repository đã thay đổi

### frontend

- `apps/public-web/app/(marketing)/page.tsx`
- `apps/public-web/components/home/custom-order-banner.tsx`
- `apps/public-web/components/home/final-cta.tsx`
- `apps/public-web/components/home/gifts-teaser.tsx`
- `apps/public-web/components/home/hero.tsx`
- `apps/public-web/components/home/templates-teaser.tsx`
- `apps/public-web/components/home/testimonials-section.tsx`
- `apps/public-web/components/site-footer.tsx`
- `apps/public-web/components/site-header.tsx`
- `apps/public-web/test/routes.spec.tsx`
- `apps/public-web/test/site-header.spec.tsx`
- `docs/prototype-inventory.md`
- `packages/ui/src/components/popover.tsx`
- `packages/ui/src/hooks/use-dismissable-layer.ts`
- `packages/ui/test/popover.spec.tsx`
- `apps/public-web/components/common/reveal.tsx`
- `apps/public-web/components/home/blog-teaser.tsx`
- `apps/public-web/components/home/editor-intro-section.tsx`
- `apps/public-web/components/home/hero-collage.tsx`
- `apps/public-web/components/home/how-it-works-section.tsx`
- `apps/public-web/components/home/occasions-section.tsx`
- `apps/public-web/components/home/qr-story-section.tsx`
- `apps/public-web/test/home-page.spec.tsx`
- `apps/public-web/test/reveal.spec.tsx`
- `apps/public-web/lib/mock/card-templates.ts`
- `apps/public-web/lib/types/card-template.ts`
- `apps/public-web/components/shop/template-card.tsx`


## Git diff stat

### frontend

```text
apps/public-web/app/(marketing)/page.tsx           |  15 ++
 .../components/home/custom-order-banner.tsx        |  34 +++-
 apps/public-web/components/home/final-cta.tsx      |  61 +++++-
 apps/public-web/components/home/gifts-teaser.tsx   | 137 ++++++++++----
 apps/public-web/components/home/hero.tsx           |  48 ++---
 .../components/home/templates-teaser.tsx           |  88 +++++++--
 .../components/home/testimonials-section.tsx       |  11 +-
 apps/public-web/components/shop/template-card.tsx  |  83 +++++++-
 apps/public-web/components/site-footer.tsx         |  31 ++-
 apps/public-web/components/site-header.tsx         |  80 +++++---
 apps/public-web/lib/mock/card-templates.ts         |  95 ++++++++++
 apps/public-web/lib/types/card-template.ts         |   2 +
 apps/public-web/test/routes.spec.tsx               |   4 +-
 apps/public-web/test/site-header.spec.tsx          | 210 ++++++++++++++++++++-
 docs/prototype-inventory.md                        |  55 +++++-
 packages/ui/src/components/popover.tsx             |  21 ++-
 packages/ui/src/hooks/use-dismissable-layer.ts     |  29 ++-
 packages/ui/test/popover.spec.tsx                  |  37 ++++
 18 files changed, 882 insertions(+), 159 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| frontend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

PASS: Đã hoàn tất full review 27 file qua đủ bảy review pass. Tất cả 15 acceptance criteria đạt, 19 finding trước đây đã được retest và xác nhận resolved, validation hiện tại cùng fidelity/provenance evidence đều đầy đủ. Không phát hiện blocker, major hoặc regression mới; implementation sẵn sàng cho user acceptance.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/repos/frontend/ui-rules.md — approved — ui-rules.md's 'Drawer/modal/toast conventions' line is stale — it says only Toast exists and 'chưa có drawer/modal nào được triển khai', but Dialog/Drawer/Popover already existed before this task and MEMORIES-0009 further extended Popover with role/lockScroll options for non-modal reuse (e.g. the header search overlay). Documenting the current, verified state so future slices know these primitives exist and how to reuse Popover outside a menu context.
- ai/repos/frontend/testing.md — approved — Adds a durable gotcha for anyone capturing full-page/full-height screenshots of pages that use the prototype's `.reveal` scroll pattern or apps/public-web/components/common/reveal.tsx: a non-scrolling headless capture leaves below-fold content invisible (opacity:0) even when the capture height covers the whole document, because the reveal is IntersectionObserver-driven and the observer's root never grows past the emulated viewport. MEMORIES-0009 review cycle 2 hit exactly this — captureBeyondViewport screenshots were full document height but blank below the hero — and fixed it by emulating `prefers-reduced-motion: reduce`, which both the prototype and `Reveal` already treat as an immediate-visible fallback (no source change required). Recording this so the next task doing similar CDP/Playwright fidelity capture work on this app does not repeat the mistake.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
