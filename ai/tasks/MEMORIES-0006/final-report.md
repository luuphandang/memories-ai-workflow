# Báo cáo MEMORIES-0006 — Migration Context To nestjs-cls

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0006/task.md`

## Nội dung triển khai

Migrated backend runtime context (correlation, request/security, database QueryRunner tracking) from three independent hand-written AsyncLocalStorage instances to one shared nestjs-cls@6.2.1 infrastructure encapsulated behind a new libs/platform/context library. Public API of CorrelationContext, RequestContext and TypeOrmQueryRunnerContext/TypeOrmUnitOfWork is preserved. Each app composition root (api/worker/cli/scheduler/realtime) configures the CLS root exactly once via RuntimeContextModule.forRoot(); apps/api and apps/realtime auto-mount the HTTP CLS initializer; apps/worker opens one independent root per BullMQ job; apps/cli/apps/scheduler open roots on demand via RequestContext#runAsSystem(). A new dependency-cruiser rule enforces that libs/platform/context never depends on security/observability/database/typeorm. RuntimeContextSeed's ownership-claiming validator is a closed-world preflight: only a fully value-graph-walked plain object/array or a genuinely plain, undecorated Date may ever be seeded, with no caller-declared "trust me, this is atomic" escape hatch (removed at attempt 27 -- fix-request review cycle 15 finding #1), so no value graph the public seed API accepts can expose shared mutable state across two roots. Every changed characterization-sensitive implementation has a recorded legacy-baseline test run against the frozen origin/master@c8ca980 source (evidence/characterization-baseline.md, [characterization-baseline: v9]).

Current validated state: lint, typecheck, [unit-tests: 69 suites / 448 tests], all 5 application builds, test:architecture (474 modules / 1794 deps / 0 violations), migration:run + db:seed, [e2e-tests: 20 suites / 146 tests], and the legacy characterization harness ([characterization-tests: 5 suites / 30 tests]) all pass fresh against a rebuilt throwaway real Postgres/Redis/MinIO stack. libs/platform/context/test/runtime-context.service.spec.ts has [context-spec-cases: 59] cases. Full per-review-cycle implementation history is in decisions[] below and handoff_status.review_state; this summary intentionally states each fact once, tagged `[name: value]`, rather than accumulating superseded numbers -- ai/skills/review-vertical-slice-completeness/scripts/check_evidence_freshness.py deterministically rejects any future attempt that lets a tagged fact drift out of sync with itself or with the artifact it describes.

## Repository đã thay đổi

### backend

- `.dependency-cruiser.js`
- `apps/api/src/app.module.ts`
- `apps/cli/src/app.module.ts`
- `apps/cli/test/cli-runner.audit-persistence.e2e-spec.ts`
- `apps/cli/test/cli-runner.service.spec.ts`
- `apps/realtime/src/app.module.ts`
- `apps/scheduler/src/app.module.ts`
- `apps/worker/src/app.module.ts`
- `libs/modules/card-catalog/src/application/use-cases/seed-card-templates.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/seed-roles-and-permissions.use-case.ts`
- `libs/modules/identity-access/test/seed-roles-and-permissions.use-case.spec.ts`
- `libs/modules/product-catalog/src/application/use-cases/seed-products.use-case.ts`
- `libs/platform/context/src/public-api.ts`
- `libs/platform/context/src/runtime-context-accessor.ts`
- `libs/platform/context/src/runtime-context.module.ts`
- `libs/platform/context/src/runtime-context.service.ts`
- `libs/platform/context/src/runtime-context.types.ts`
- `libs/platform/context/test/runtime-context.service.spec.ts`
- `libs/platform/context/tsconfig.lib.json`
- `libs/platform/database/src/typeorm-unit-of-work.ts`
- `libs/platform/database/test/typeorm-unit-of-work-real-postgres.e2e-spec.ts`
- `libs/platform/database/test/typeorm-unit-of-work.spec.ts`
- `libs/platform/observability/src/correlation-context.ts`
- `libs/platform/observability/src/correlation.middleware.ts`
- `libs/platform/observability/src/logger.module.ts`
- `libs/platform/observability/test/correlation-context.spec.ts`
- `libs/platform/observability/test/logger.module.spec.ts`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts`
- `libs/platform/queue/test/bullmq-real-redis-isolation.e2e-spec.ts`
- `libs/platform/queue/test/bullmq.publisher.spec.ts`
- `libs/platform/queue/test/bullmq.worker.correlation.spec.ts`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts`
- `libs/platform/security/src/request-context.middleware.ts`
- `libs/platform/security/src/request-context.ts`
- `libs/platform/security/test/http-context-lifecycle.e2e-spec.ts`
- `libs/platform/security/test/jwt-auth.guard.spec.ts`
- `libs/platform/security/test/request-context.spec.ts`
- `libs/shared/kernel/src/entities/auditable-props.ts`
- `nest-cli.json`
- `package-lock.json`
- `package.json`
- `tsconfig.json`


## Git diff stat

### backend

```text
.dependency-cruiser.js                             |  20 ++
 apps/api/src/app.module.ts                         |   8 +
 apps/cli/src/app.module.ts                         |   4 +
 apps/realtime/src/app.module.ts                    |   4 +
 apps/scheduler/src/app.module.ts                   |   6 +
 apps/worker/src/app.module.ts                      |   4 +
 .../use-cases/seed-card-templates.use-case.ts      |  13 +-
 .../seed-roles-and-permissions.use-case.ts         |  32 ++-
 .../seed-roles-and-permissions.use-case.spec.ts    |  37 ++-
 .../use-cases/seed-products.use-case.ts            |  13 +-
 libs/platform/database/src/typeorm-unit-of-work.ts |  35 ++-
 .../database/test/typeorm-unit-of-work.spec.ts     |  94 +++++++
 .../observability/src/correlation-context.ts       | 100 +++++++-
 .../observability/src/correlation.middleware.ts    |   9 +-
 libs/platform/observability/src/logger.module.ts   |   9 +-
 .../observability/test/correlation-context.spec.ts | 274 ++++++++++++++++++++-
 .../observability/test/logger.module.spec.ts       | 265 ++++++++++++++++++++
 libs/platform/queue/src/bullmq/bullmq.worker.ts    |  19 +-
 libs/platform/queue/test/bullmq.publisher.spec.ts  |  68 +++++
 .../queue/test/bullmq.worker.correlation.spec.ts   | 100 +++++++-
 .../queue/test/bullmq.worker.retries.spec.ts       |  10 +
 .../security/src/request-context.middleware.ts     |   2 +-
 libs/platform/security/src/request-context.ts      |  88 +++++--
 libs/platform/security/test/jwt-auth.guard.spec.ts |  58 +++++
 libs/shared/kernel/src/entities/auditable-props.ts |   6 +-
 nest-cli.json                                      |   9 +
 package-lock.json                                  |  16 ++
 package.json                                       |  19 +-
 tsconfig.json                                      |   1 +
 29 files changed, 1254 insertions(+), 69 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

Full review completed for all 42 implementation files and their direct dependencies. CodeGraph impact analysis, all seven review passes, AC1-AC22, current-cycle validation/provenance, applicable risk areas, and every prior Codex finding were verified. No blocker, major, minor, or note-level defects remain; the implementation is technically ready for user acceptance.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/domains/request-context/INDEX.md — not approved — The migration described as in-progress ('đang migrate sang nestjs-cls (epic MEMORIES-0006)') is now implemented and pending user acceptance for this task. Once accepted, INDEX.md/overview.md/data-flow.md/decisions.md should be refreshed to describe the shared nestjs-cls-backed RuntimeContextService (libs/platform/context) with correlation/request/database namespaces instead of three independent AsyncLocalStorage instances, and decisions.md should record the seedActiveRoot()-vs-run() split and the runRoot()-per-BullMQ-job/CLI-command pattern documented in this task's implementation.json decisions.
- ai/repos/backend/architecture.md — not approved — If this document enumerates platform libraries or dependency-direction rules, add libs/platform/context as a new platform library (nestjs-cls-backed runtime context infrastructure) with the dependency direction observability/security/database/queue -> platform/context -> nestjs-cls, and note that .dependency-cruiser.js now also enforces two platform/context-scoped rules in addition to the five libs/modules/*-scoped ones.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
