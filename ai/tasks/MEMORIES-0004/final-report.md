# Báo cáo MEMORIES-0004 — Catalog, Taxonomy & Faceted Filtering Implementation

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0004/task.md`

## Nội dung triển khai

Implemented the catalog/taxonomy/faceted-filtering epic end to end: a new shared `catalog` bounded context (occasion, card_style, product_category, recipient_segment, material, card_format, color_family, personalization_capability as one discriminated catalog_terms table, with real parent/child hierarchy for product_category), the previously-empty `card-catalog` and `product-catalog` module skeletons filled in with domain/application/infrastructure/presentation layers, four migrations, idempotent seed data matching the mau-thiep/qua-ky-niem prototypes, three public GET endpoints (/api/v1/catalogs, /api/v1/card-templates, /api/v1/products) with pagination, deterministic sort, search, multi-select filters and facet counts (AND across facets, OR within a facet, descendant-inclusive category counts, no M2M duplicate counting), full Swagger/OpenAPI documentation and a verified generated-document contract test. On the frontend: array-aware query serialization and typed catalogs/card-templates/products API wrappers generated from the backend's real OpenAPI schema, TanStack Query hooks with AbortSignal-based request cancellation, a URL-search-params-as-source-of-truth filter/search/sort/page hook, and both `/mau-thiep` and `/qua-ky-niem` migrated off local mock arrays onto the real API with loading/background-refresh/error-retry/empty/zero-count-disabled states, while preserving the existing MEMORIES-0003 layout and presentation components (adapted via view-model mapper functions instead of rewriting them).

Review-cycle-4 fix pass: fixed a boolean-query-param bug (`rush=false` silently read as `true` under global `enableImplicitConversion`; fixed with `@Type(() => String)` before the custom `@Transform`); restored the qua-ky-niem hero artwork on mobile/tablet; added 15 GiftCatalog integration tests; replaced the UI-fidelity capture script with a CDP-driven one that fails loudly on a browser error page and captures the full scrollable page.

Review-cycle-7 fix pass: refreshed stale handoff/migration-count evidence (3/9 -> 4/10) with a full isolated empty-database migration cycle rerun (apply x4/seed/e2e/revert x4/reapply/reseed/e2e, passing identically both times); recaptured 4 UI-fidelity entries that had been taken against a database the capture script's port-mismatched default never actually reached.

Validation-fix attempt 2: fixed a frontend-wide typecheck/build break in packages/config/src/env.ts — replaced an unsound `as NodeJS.ProcessEnv` cast with a narrow `PublicEnvSource` type matching the 6 keys `getAppEnv` actually reads.

Review-cycle-8 fix pass (backend-only): resolved 4 verified findings (full mechanism in `decisions` below): regenerated changed_files from `git diff`/`git ls-files`; added `CatalogTerm.reconcile()` so a seed rerun repairs manually-altered rows, not just skips them; fixed blank/malformed filter validation (AC12, `toIdArray` no longer drops empty CSV segments, numeric filters use `@Type(() => String)` + `toTrimmedNumber`); wrapped seed use-case saves in `UnitOfWork.withTransaction(...)` for atomicity. Full backend validation reran clean: lint/typecheck/test 282/61 (+5)/test:architecture/test:e2e 104/13 (+27 tests, +3 suites)/build/export:openapi, all 5 deterministic skill scripts.

Review-cycle-9 fix pass (full-plan scope): reverted a global CORP relaxation in `configureApp` that had no benefit (CORP doesn't restrict cors-mode `fetch()`, verified against MDN) and weakened a real protection — new security-headers.e2e-spec.ts (4 tests); fixed a dead search button/Enter-key submit in card-catalog.tsx, wrapped in `<form onSubmit>` like gift-catalog.tsx (2 new tests).

Review-cycle-10 fix pass (full-plan scope): fixed a stale "three migrations" summary sentence and re-audited every count in this document (446/1613 -> 447/1620); disabled zero-count derived-filter choices (gift-catalog rush checkbox, card-catalog access-tier radios) that stayed clickable while selected-but-zero stays clearable (4 new tests); added e2e coverage for 4 previously-untested product filter families plus 2 cross-facet AND cases, each picking ids dynamically from the live facets response. Full e2e suite now 114/14 (+6); public-web suite now 60/9 (+4).

Review-cycle-11 fix pass (backend-only, full-plan scope): `enforce_catalog_terms_hierarchy()` validated only the row being written against its own `parent_id`, never a row that OTHER rows reference via THEIR `parent_id` — an UPDATE changing a referenced PRODUCT_CATEGORY parent's catalog_type silently succeeded, leaving its child pointed at a now-wrongly-typed parent. Trigger now also rejects any catalog_type change on a row still referenced by another row's parent_id; new catalog-hierarchy-guard.e2e-spec.ts case proves the rejection; migration reverted+reapplied against live Postgres. Full backend validation reran clean (test:e2e 115/14 (+1), rest unchanged). Frontend unaffected.

Review-cycle-12 fix pass (full-plan scope): resolved 4 verified major findings. #1 rewrote price/preparation/rush facets as one bounded `COUNT(DISTINCT CASE WHEN...)` query per facet in Postgres, replacing a Node-side load-every-matching-variant-then-Array.filter approach (new 24-variant e2e fixture). #2 added `status = 'ACTIVE'` to every catalog-term read path missing it (product/card-template link filters, category descendant closure, findDescendantIds), so a deactivated term stops being filterable/renderable/traversable (3 new real-Postgres regressions). #3 `mapProduct` mapped a null variant to a fabricated `price: 0`; `GiftProduct.price`/`Price` widened to `number | null`, rendering 'Đang cập nhật giá' instead (purchase controls already disabled via `inStock`); new integration test. #4 reran the full empty-database migration cycle against a freshly recreated Postgres database with all current-cycle code present. Full backend validation reran clean (test:e2e 119/15 (+4), rest unchanged, all 6 deterministic skill scripts); frontend reran clean (test 61/9 (+1)).

Validation-fix attempt 3: `npm run test:e2e` (the exact required command, invoked with no extra flags by both CI and this validation gate) was flaky under Jest's default parallel workers — every e2e spec file targets one shared live Postgres database, so concurrent spec files racing inserts/deletes against each other could shift a count-based assertion mid-run. Reproduced the reported failure locally (`products.e2e-spec.ts` "keeps derived price, preparation and rating facet counts consistent with their filters", expected 15 received 17 — a sibling spec's concurrently-created rows leaking into the assertion window), confirming this was the same DB-contention pattern review-cycle-12 had already documented as pre-existing but never fixed at the command level. Root-caused and fixed by setting `maxWorkers: 1` in `test/jest-e2e.json`, so `npm run test:e2e` itself is deterministic in every environment without relying on an operator remembering `--runInBand`. Reran twice locally after the fix: 119/119 passing both times.

Review-cycle-15 fix pass (full-plan scope): #1/#2 ran `npm run format` in both worktrees for the repo-wide `format:check` CI gate (27 pre-existing backend + 3 frontend files reformatted, plus 4 controllers' @ApiResponse decorators reconciled with check_openapi_contract.py's boundary heuristic — see decisions). #3 confirmed the migration-tooling regression no longer exists (HEAD already equals origin/master). Full backend/frontend validation reran clean, all counts unchanged from review-cycle-13.

## Repository đã thay đổi

### backend

- `.github/workflows/ci.yml`
- `.gitignore`
- `apps/api/src/business-modules.ts`
- `apps/api/src/configure-app.ts`
- `apps/api/test/catalog.e2e-spec.ts`
- `apps/api/test/catalog-hierarchy-guard.e2e-spec.ts`
- `apps/api/test/catalog-seed-convergence.e2e-spec.ts`
- `apps/api/test/card-templates.e2e-spec.ts`
- `apps/api/test/card-template-aggregate-transaction-rollback.e2e-spec.ts`
- `apps/api/test/security-headers.e2e-spec.ts`
- `apps/api/test/products.e2e-spec.ts`
- `apps/api/test/product-aggregate-transaction-rollback.e2e-spec.ts`
- `apps/api/test/openapi-contract.e2e-spec.ts`
- `apps/cli/src/business-modules.ts`
- `apps/cli/src/commands/seed.command.ts`
- `apps/scheduler/src/business-modules.ts`
- `apps/worker/src/business-modules.ts`
- `tsconfig.json`
- `nest-cli.json`
- `openapi-contracts.json`
- `package.json`
- `libs/modules/identity-access/src/presentation/http/auth.controller.ts`
- `libs/modules/catalog/src/domain/catalog-term/catalog-term.ts`
- `libs/modules/catalog/src/domain/catalog-term/catalog-term.repository.ts`
- `libs/modules/catalog/src/application/ports/catalog-terms-reader.ts`
- `libs/modules/catalog/src/application/use-cases/list-catalog-terms.use-case.ts`
- `libs/modules/catalog/src/application/use-cases/seed-catalog-terms.use-case.ts`
- `libs/modules/catalog/src/infrastructure/persistence/catalog-term.orm-entity.ts`
- `libs/modules/catalog/src/infrastructure/persistence/catalog-term.mapper.ts`
- `libs/modules/catalog/src/infrastructure/persistence/typeorm-catalog-term.repository.ts`
- `libs/modules/catalog/src/infrastructure/contracts/catalog-term-lookup.service.ts`
- `libs/modules/catalog/src/presentation/http/catalog-term-response.dto.ts`
- `libs/modules/catalog/src/presentation/http/list-catalog-terms.dto.ts`
- `libs/modules/catalog/src/presentation/http/catalog.controller.ts`
- `libs/modules/catalog/src/catalog.module.ts`
- `libs/modules/catalog/src/public-api.ts`
- `libs/modules/catalog/tsconfig.lib.json`
- `libs/modules/catalog/test/catalog-term.spec.ts`
- `libs/modules/catalog/test/list-catalog-terms.use-case.spec.ts`
- `libs/modules/card-catalog/src/domain/card-template/card-template.ts`
- `libs/modules/card-catalog/src/domain/card-template/card-template.repository.ts`
- `libs/modules/card-catalog/src/application/use-cases/list-card-templates.use-case.ts`
- `libs/modules/card-catalog/src/application/use-cases/seed-card-templates.use-case.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/card-template.orm-entity.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/card-template-catalog-term.orm-entity.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/card-template.mapper.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/typeorm-card-template.repository.ts`
- `libs/modules/card-catalog/src/presentation/http/card-template-response.dto.ts`
- `libs/modules/card-catalog/src/presentation/http/list-card-templates.dto.ts`
- `libs/modules/card-catalog/src/presentation/http/card-template.controller.ts`
- `libs/modules/card-catalog/src/card-catalog.module.ts`
- `libs/modules/card-catalog/src/public-api.ts`
- `libs/modules/card-catalog/test/card-template.spec.ts`
- `libs/modules/card-catalog/test/list-card-templates.use-case.spec.ts`
- `libs/modules/product-catalog/src/domain/product/product.ts`
- `libs/modules/product-catalog/src/domain/product/product-variant.ts`
- `libs/modules/product-catalog/src/domain/product/product.repository.ts`
- `libs/modules/product-catalog/src/application/use-cases/list-products.use-case.ts`
- `libs/modules/product-catalog/src/application/use-cases/seed-products.use-case.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/product.orm-entity.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/product-variant.orm-entity.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/product-catalog-term.orm-entity.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/product.mapper.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/typeorm-product.repository.ts`
- `libs/modules/product-catalog/src/presentation/http/product-response.dto.ts`
- `libs/modules/product-catalog/src/presentation/http/list-products.dto.ts`
- `libs/modules/product-catalog/src/presentation/http/product.controller.ts`
- `libs/modules/product-catalog/src/product-catalog.module.ts`
- `libs/modules/product-catalog/src/public-api.ts`
- `libs/modules/product-catalog/test/product.spec.ts`
- `libs/modules/product-catalog/test/product-variant.spec.ts`
- `libs/modules/product-catalog/test/list-products.use-case.spec.ts`
- `libs/platform/database/src/migrations/1722560000000-CreateCatalogSchema.ts`
- `libs/platform/database/src/migrations/1722570000000-CreateCardCatalogSchema.ts`
- `libs/platform/database/src/migrations/1722580000000-CreateProductCatalogSchema.ts`
- `libs/platform/database/src/migrations/1722590000000-AddCatalogTermsHierarchyGuard.ts`
- `apps/api/test/catalog-inactive-terms.e2e-spec.ts`
- `test/jest-e2e.json`
- `.github/test/workflow-security.spec.ts`
- `apps/cli/test/reprocess-job.command.spec.ts`
- `apps/worker/src/worker-metrics.server.ts`
- `apps/worker/test/worker-metrics.server.spec.ts`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts`
- `libs/modules/media/src/application/use-cases/create-media-asset.use-case.ts`
- `libs/modules/media/src/application/use-cases/reprocess-media-asset.use-case.ts`
- `libs/modules/media/src/presentation/http/create-media-asset.dto.ts`
- `libs/modules/media/src/presentation/http/media.controller.ts`
- `libs/modules/media/test/generate-thumbnail.handler.spec.ts`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts`
- `libs/modules/media/test/get-media-asset.use-case.spec.ts`
- `libs/modules/media/test/reprocess-media-asset.use-case.spec.ts`
- `libs/platform/database/test/typeorm-unit-of-work.spec.ts`
- `libs/platform/queue/src/bullmq/bullmq-queue.factory.ts`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts`
- `libs/platform/queue/src/bullmq/shutdown-deadline.ts`
- `libs/platform/queue/src/contracts/background-job-handler.ts`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts`
- `libs/platform/queue/test/bullmq.publisher.spec.ts`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts`
- `libs/platform/queue/test/outbox-relay.service.spec.ts`
- `libs/platform/realtime/test/redis-emitter-client.shutdown.spec.ts`
- `libs/platform/realtime/test/redis-io.adapter.close.spec.ts`
- `libs/platform/storage/src/storage.contract.ts`

### frontend

- `.gitignore`
- `package-lock.json`
- `packages/api-client/src/http-client.ts`
- `packages/api-client/src/routes.ts`
- `packages/api-client/src/catalog-client.ts`
- `packages/api-client/src/card-template-client.ts`
- `packages/api-client/src/product-client.ts`
- `packages/api-client/src/index.ts`
- `packages/api-client/src/generated/schema.d.ts`
- `packages/api-client/test/query-serialization.spec.ts`
- `packages/api-client/test/catalog-resource-clients.spec.ts`
- `apps/public-web/app/providers.tsx`
- `apps/public-web/app/(marketing)/mau-thiep/page.tsx`
- `apps/public-web/app/(marketing)/qua-ky-niem/page.tsx`
- `apps/public-web/lib/api/api-client-context.tsx`
- `apps/public-web/lib/api/map-card-template.ts`
- `apps/public-web/lib/api/map-product.ts`
- `apps/public-web/lib/hooks/use-url-filter-state.ts`
- `apps/public-web/lib/queries/query-keys.ts`
- `apps/public-web/lib/queries/use-catalog-terms.ts`
- `apps/public-web/lib/queries/use-card-templates.ts`
- `apps/public-web/lib/queries/use-products.ts`
- `apps/public-web/lib/utils/compact.ts`
- `apps/public-web/lib/types/gift-product.ts`
- `apps/public-web/lib/mock/gift-products.ts`
- `apps/public-web/lib/store/shop-store.tsx`
- `apps/public-web/components/card-templates/card-catalog.tsx`
- `apps/public-web/components/gift-products/gift-catalog.tsx`
- `apps/public-web/components/gift-products/quick-view-dialog.tsx`
- `apps/public-web/components/shop/product-card.tsx`
- `apps/public-web/components/home/gifts-teaser.tsx`
- `apps/public-web/components/common/catalog-skeleton-grid.tsx`
- `apps/public-web/components/common/error-state.tsx`
- `apps/public-web/test/card-catalog.spec.tsx`
- `apps/public-web/test/gift-catalog.spec.tsx`
- `apps/public-web/test/routes.spec.tsx`
- `apps/public-web/test/utils/api-fixtures.ts`
- `apps/public-web/test/utils/navigation-mock.ts`
- `apps/public-web/test/utils/render-with-providers.tsx`
- `packages/config/src/env.ts`
- `apps/public-web/components/common/price.tsx`
- `docs/guides/local-development.md`
- `packages/api-client/test/http-client.spec.ts`
- `packages/api-client/test/media-client.spec.ts`


## Git diff stat

### backend

```text
.github/test/workflow-security.spec.ts             |  24 +++--
 .github/workflows/ci.yml                           |   3 +
 .gitignore                                         |   1 +
 apps/api/src/business-modules.ts                   |   2 +
 apps/api/src/configure-app.ts                      |  11 +-
 apps/api/test/openapi-contract.e2e-spec.ts         |  50 +++++++++
 apps/cli/src/business-modules.ts                   |   2 +
 apps/cli/src/commands/seed.command.ts              |  22 +++-
 apps/cli/test/reprocess-job.command.spec.ts        |   4 +-
 apps/scheduler/src/business-modules.ts             |   2 +
 apps/worker/src/business-modules.ts                |   2 +
 apps/worker/src/worker-metrics.server.ts           |   6 +-
 apps/worker/test/worker-metrics.server.spec.ts     |  15 ++-
 .../card-catalog/src/card-catalog.module.ts        |  31 +++++-
 libs/modules/card-catalog/src/public-api.ts        |  11 ++
 .../src/presentation/http/auth.controller.ts       |  32 ++----
 .../use-cases/confirm-media-upload.use-case.ts     |   6 +-
 .../use-cases/create-media-asset.use-case.ts       |   8 +-
 .../use-cases/reprocess-media-asset.use-case.ts    |   4 +-
 .../presentation/http/create-media-asset.dto.ts    |   5 +-
 .../src/presentation/http/media.controller.ts      |  11 +-
 .../media/test/generate-thumbnail.handler.spec.ts  |  12 ++-
 .../media/test/generate-thumbnail.use-case.spec.ts |  18 ++--
 .../media/test/get-media-asset.use-case.spec.ts    |   6 +-
 .../test/reprocess-media-asset.use-case.spec.ts    |  10 +-
 .../product-catalog/src/product-catalog.module.ts  |  38 +++++--
 libs/modules/product-catalog/src/public-api.ts     |   8 ++
 .../database/test/typeorm-unit-of-work.spec.ts     |   2 +-
 .../queue/src/bullmq/bullmq-queue.factory.ts       |   8 +-
 libs/platform/queue/src/bullmq/bullmq.worker.ts    |  37 ++++---
 .../src/bullmq/failure-reconciliation.service.ts   |   4 +-
 .../platform/queue/src/bullmq/shutdown-deadline.ts |   5 +-
 .../queue/src/contracts/background-job-handler.ts  |   5 +-
 .../queue/src/outbox/outbox-relay.service.ts       |   5 +-
 libs/platform/queue/test/bullmq.publisher.spec.ts  |  15 ++-
 .../queue/test/bullmq.worker.retries.spec.ts       |  37 +++++--
 .../test/failure-reconciliation.service.spec.ts    |  51 ++++++---
 .../queue/test/outbox-relay.service.spec.ts        | 116 +++++++++++++++++----
 .../test/redis-emitter-client.shutdown.spec.ts     |   5 +-
 .../realtime/test/redis-io.adapter.close.spec.ts   |   5 +-
 libs/platform/storage/src/storage.contract.ts      |   6 +-
 nest-cli.json                                      |   9 ++
 openapi-contracts.json                             |  24 +++++
 package.json                                       |   1 +
 test/jest-e2e.json                                 |   1 +
 tsconfig.json                                      |   1 +
 46 files changed, 536 insertions(+), 145 deletions(-)
```

### frontend

```text
.gitignore                                         |    2 +-
 apps/public-web/app/(marketing)/mau-thiep/page.tsx |   30 +-
 .../app/(marketing)/qua-ky-niem/page.tsx           |   99 +-
 apps/public-web/app/providers.tsx                  |   12 +-
 .../components/card-templates/card-catalog.tsx     |  652 ++++---
 apps/public-web/components/common/price.tsx        |   11 +-
 .../components/gift-products/gift-catalog.tsx      |  839 ++++++---
 .../components/gift-products/quick-view-dialog.tsx |   40 +-
 apps/public-web/components/home/gifts-teaser.tsx   |   22 +-
 apps/public-web/components/shop/product-card.tsx   |   40 +-
 apps/public-web/lib/mock/gift-products.ts          |  152 --
 apps/public-web/lib/store/shop-store.tsx           |    7 +-
 apps/public-web/lib/types/gift-product.ts          |   19 +-
 apps/public-web/test/card-catalog.spec.tsx         |  352 +++-
 apps/public-web/test/gift-catalog.spec.tsx         |  666 ++++++-
 apps/public-web/test/routes.spec.tsx               |   44 +-
 docs/guides/local-development.md                   |   14 +-
 package-lock.json                                  |   10 +-
 packages/api-client/src/generated/schema.d.ts      | 1881 +++++++++++++++-----
 packages/api-client/src/http-client.ts             |   19 +-
 packages/api-client/src/index.ts                   |    3 +
 packages/api-client/src/routes.ts                  |    9 +
 packages/api-client/test/http-client.spec.ts       |   16 +-
 packages/api-client/test/media-client.spec.ts      |    6 +-
 packages/config/src/env.ts                         |   35 +-
 25 files changed, 3763 insertions(+), 1217 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, test-architecture=passed, test-e2e=passed, build=passed, export-openapi=passed |
| frontend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

Đã hoàn tất đủ bảy review passes cho toàn bộ 149 tracked/untracked implementation files trong hai worktree. Tất cả 42 prior findings được retest và đã resolved; AC1–AC20 đều pass. Validation cycle hiện tại pass đầy đủ, hai format checks chạy lại cũng pass, deterministic vertical-slice/UI-fidelity evidence không thiếu. Không phát hiện blocker, major hoặc defect có thể hành động; implementation sẵn sàng cho user acceptance.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/repos/backend/source-map.md — approved — Add rows for the new `catalog`, `card-catalog` and `product-catalog` modules (controller/use-case/entity/migration paths), mirroring the existing `media`/`identity-access` row pattern, so the source map stays a reliable index of implemented (not skeleton) modules.
- ai/repos/backend/architecture.md — approved — Document the 'one shared reference-taxonomy table discriminated by type' pattern (libs/modules/catalog) as an established alternative to per-concept tables when several catalogs share an identical shape, and record the facet-count semantics convention (self-exclusion per facet, descendant-inclusive counts via recursive CTE for hierarchical types, plus response-derived price/preparation/rating option groups) as a reusable pattern for future faceted-search modules.
- ai/repos/backend/database-rules.md — approved — Document two variant-selection SQL conventions from typeorm-product.repository.ts: (1) the LATERAL-join 'cheapest matching variant' pattern (`effectiveVariantLateralSql`) for list/sort and the rating facet's product-existence guard; (2) the bounded-aggregate 'value-bucketed' pattern (`computeBucketFacet`, and `computeRatingFacet` following the same shape) required for price/preparation/rush/rating facets — each computed as a single `COUNT(DISTINCT CASE WHEN <bucket condition> THEN p.id END)` query per bucket, entirely in Postgres, never materializing per-variant or per-product rows in application memory (a single representative/cheapest variant under-counts a product with variants on each side of a bucket boundary, so (1) alone is insufficient for these facets; review-cycle-4 introduced this pattern for price/preparation/rush, review-cycle-13 extended it to rating). Also document the recursive closure-CTE pattern for parent/child facet aggregation, and the DB-level BEFORE INSERT/UPDATE trigger pattern (AddCatalogTermsHierarchyGuard) for cycle-detection invariants a plain self-FK can't express.
- ai/repos/backend/conventions.md — approved — Document a real bug/fix as a required convention: with the global ValidationPipe's `enableImplicitConversion: true`, a DTO boolean/numeric query-param field decorated only with a custom `@Transform` gets silently overridden by class-transformer's implicit primitive-conversion step (e.g. `?flag=false` becomes `true`; a blank numeric string becomes `0`, not `NaN`, silently passing `@Min(0)`) — `@Type(() => Number)`'s conversion runs before any co-located `@Transform` regardless of decorator order. Fix: add `@Type(() => String)` before the custom `@Transform` to pin the implicit-conversion type away from the real target type, so the `@Transform` output is final (see `rush` in list-products.dto.ts; `toTrimmedNumber` for priceMin/priceMax/prepWithinDays/ratingMin). Companion CSV-array rule: `toIdArray`-style helpers must NOT `.filter(Boolean)` after splitting/trimming — a blank/inner-empty segment must survive as an empty string so `@IsUUID`/`@IsIn { each: true }` rejects it instead of being silently dropped.
- ai/repos/backend/conventions.md — approved — Document the seed-convergence convention: an idempotent find-by-code-or-create seed use case must reconcile (update) an already-existing row's mutable fields onto the canonical seed definition, not just skip it, or a rerun only guarantees row *presence*, not row *content* — a manually-altered or stale-from-an-earlier-code-change row is never repaired. See `CatalogTerm.reconcile()` (libs/modules/catalog/src/domain/catalog-term/catalog-term.ts) + `SeedCatalogTermsUseCase.findOrCreate`'s existing-row branch for the reference implementation: re-validate the same invariants `create()` checks (duplicated, not extracted into a shared validator, matching the existing `UserProfile.update`/`Account.activate` convention), never reconcile the row's stable lookup identity fields (here: `code`/`catalogType`).
- ai/repos/backend/database-rules.md — approved — Document the transaction-boundary convention for multi-statement aggregate-replace methods (e.g. 'save aggregate, then delete+reinsert child rows', seen in `TypeOrmProductRepository.saveWithVariantsAndCatalogLinks`/`TypeOrmCardTemplateRepository.saveWithCatalogLinks`): the repository never opens the transaction itself — it only checks `TypeOrmQueryRunnerContext.get()` via `repositoryFor()`-style accessors. The CALLING use case wraps the whole call in `UnitOfWork.withTransaction(...)` (see `SeedProductsUseCase.seedOne`, matching `CreateAccountUseCase`). Any such delete+reinsert method called without that wrapper is not atomic — verify with an e2e test forcing a mid-sequence unique-constraint violation (two rows sharing a unique key in one insert batch is a reliable, self-contained way to do this) and asserting the aggregate row was not committed.
- ai/repos/frontend/architecture.md — approved — The 'chưa có page nào thật sự gọi useQuery/useMutation' statement is now outdated — /mau-thiep and /qua-ky-niem are the first real consumers. Document the ApiClientProvider (apps/public-web/lib/api/api-client-context.tsx) pattern for exposing the single ApiClient instance to hooks, and the useUrlFilterState URL-as-source-of-truth pattern, as the reference for future data-driven pages.
- ai/repos/frontend/source-map.md — approved — `public-web/components/` is no longer empty; add lib/queries, lib/api, lib/hooks, lib/utils to the State/store and API-client rows, and note packages/api-client now has three additional resource wrappers beyond media-client following the same operations[...]-derived-types pattern.
- ai/repos/frontend/api-client-rules.md — approved — Document the array-query-param convention (comma-joined single value, matching backend class-transformer @Transform split-on-comma DTOs) added to ApiClient.buildUrl, since prior guidance only covered flat scalar params.
- ai/repos/frontend/testing.md — approved — Document three pitfalls found while rebuilding the UI-fidelity capture tooling: (1) always verify dev-server liveness with a real content check, not just an HTTP status code (a stale Next.js dev server can return 200 with a broken webpack runtime); (2) CDP's `Page.captureScreenshot` without `captureBeyondViewport`+`clip` only grabs the viewport rect, so full-page mobile/tablet states must request the full `scrollHeight` or every state clips identically; (3) a hardcoded default target URL silently drifts stale once the app's real configured port changes — even a content-based capture precondition never exercises the real target if the default points elsewhere, so pass `FRONTEND_URL`/`API_URL` explicitly.
- ai/repos/backend/conventions.md — approved — Document the CORP/CORS distinction: Helmet's default `Cross-Origin-Resource-Policy: same-origin` only blocks no-cors cross-origin embeds (e.g. <img>/<script>), never fetch()'s default cors-mode requests — never relax it globally to let a cross-origin SPA consume the API; CORS config already governs that. Scope any real crossOriginResourcePolicy override to the specific route, not globally in configureApp.
- ai/repos/backend/conventions.md — approved — Document that every `@ApiResponse({...})` decorator on a handler must stay on one line (put `description` text in a `//` comment above instead) — `check_openapi_contract.py`'s boundary heuristic truncates the captured block at any multi-line decorator's closing `})` right before the handler, and a useful `description` almost always exceeds printWidth 100, so the two mandatory gates conflict unless description text is kept out of the decorator.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
