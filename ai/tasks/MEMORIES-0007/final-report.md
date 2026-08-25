# Báo cáo MEMORIES-0007 — Consolidate transaction-aware TypeORM repository resolution

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0007/task.md`

## Nội dung triển khai

Added a single shared, type-safe TypeORM repository-resolution primitive, TypeOrmRepositoryResolver<Entity>, at libs/platform/database/src/typeorm-repository-resolver.ts (exported via public-api.ts). It replaces the context.get() -> queryRunner.manager.getRepository(entityTarget) -> fallback algorithm that every TypeORM persistence adapter used to reimplement as a private repositoryFor()/variantRepositoryFor()/linkRepositoryFor() method. Grep for `queryRunnerContext.get()`, `manager.getRepository`, and `TypeOrmQueryRunnerContext` injection across libs (cross-checked with CodeGraph) confirmed exactly the 13 baseline occurrences named in task.md and no additional equivalent occurrence: TypeOrmOutboxRepository, TypeOrmCatalogTermRepository, TypeOrmProductRepository (3 entities: product/variant/link), TypeOrmAuthIdentityRepository, TypeOrmAccountRepository, TypeOrmRolePermissionRepository, TypeOrmAccountRoleRepository, TypeOrmRefreshSessionRepository, TypeOrmPermissionRepository, TypeOrmRoleRepository, TypeOrmCardTemplateRepository (2 entities: template/link), TypeOrmUserProfileRepository, TypeOrmMediaAssetRepository. A hit in seed-products.use-case.ts was only a code comment naming the old private methods (updated, not a duplicate implementation). All 13 were migrated: each adapter now holds one TypeOrmRepositoryResolver per ORM entity it owns (one for single-entity adapters, two or three for the product/card-template multi-entity adapters), constructed once from the adapter's existing @InjectRepository fallback and TypeOrmQueryRunnerContext, with every call site (`this.repositoryFor()` etc.) replaced by `this.<name>Resolver.get()`. The resolver holds no mutable resolution state — entityTarget/fallback/context reference are fixed at construction, but the QueryRunner/repository lookup itself is redone on every get() call — so a value from one transaction/request can never leak into a later call on the same (singleton) adapter instance. Two intentional non-migrations were preserved exactly as-is because they predate and are unrelated to this refactor: TypeOrmOutboxRepository.listUnpublished/markPublished/recordFailure call this.repository directly (never via repositoryFor()) because they are meant to run against the default connection outside any transaction, and this repository-resolution refactor does not change that behavior. All specific query/mapping/soft-delete/conditional-update/upsert/raw-SQL/aggregate-persistence logic in every adapter is unchanged; only the resolution of which TypeORM Repository instance backs each call was extracted. Added libs/platform/database/test/typeorm-repository-resolver.spec.ts (fallback path, active-runner path, correct entity target with two resolvers sharing one QueryRunner, re-resolution across transaction boundaries, no reuse of the transactional repository after the transaction's callback ends, and concurrent-transaction isolation for the same resolver instance). Added characterization tests for one single-entity adapter (typeorm-catalog-term.repository.spec.ts) and both multi-entity adapters explicitly named in AC4 (typeorm-product.repository.spec.ts, typeorm-card-template.repository.spec.ts), each proving fallback-vs-transactional routing per entity in and out of transaction. No domain repository interface, use-case/controller contract, API contract, or database schema/migration changed. lint, typecheck, test (70 suites / 338 tests, including the existing TypeOrmUnitOfWork/TypeOrmQueryRunnerContext concurrency and rollback tests unmodified), test:architecture (dependency-cruiser, 0 violations) and build all pass on the current worktree state.

## Repository đã thay đổi

### backend

- `libs/modules/card-catalog/src/infrastructure/persistence/typeorm-card-template.repository.ts`
- `libs/modules/card-catalog/test/typeorm-card-template.repository.spec.ts`
- `libs/modules/catalog/src/infrastructure/persistence/typeorm-catalog-term.repository.ts`
- `libs/modules/catalog/test/typeorm-catalog-term.repository.spec.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-account-role.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-account.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-auth-identity.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-permission.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-refresh-session.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-role-permission.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-role.repository.ts`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts`
- `libs/modules/product-catalog/src/application/use-cases/seed-products.use-case.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/typeorm-product.repository.ts`
- `libs/modules/product-catalog/test/typeorm-product.repository.spec.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/typeorm-user-profile.repository.ts`
- `libs/platform/database/src/public-api.ts`
- `libs/platform/database/src/typeorm-repository-resolver.ts`
- `libs/platform/database/test/typeorm-repository-resolver.spec.ts`
- `libs/platform/queue/src/outbox/typeorm-outbox.repository.ts`


## Git diff stat

### backend

```text
.../typeorm-card-template.repository.ts            | 66 ++++++++-------
 .../persistence/typeorm-catalog-term.repository.ts | 32 +++----
 .../persistence/typeorm-account-role.repository.ts | 33 ++++----
 .../persistence/typeorm-account.repository.ts      | 29 ++++---
 .../typeorm-auth-identity.repository.ts            | 34 ++++----
 .../persistence/typeorm-permission.repository.ts   | 30 ++++---
 .../typeorm-refresh-session.repository.ts          | 36 ++++----
 .../typeorm-role-permission.repository.ts          | 35 ++++----
 .../persistence/typeorm-role.repository.ts         | 30 ++++---
 .../persistence/typeorm-media-asset.repository.ts  | 32 +++----
 .../use-cases/seed-products.use-case.ts            |  4 +-
 .../persistence/typeorm-product.repository.ts      | 97 +++++++++++-----------
 .../persistence/typeorm-user-profile.repository.ts | 35 ++++----
 libs/platform/database/src/public-api.ts           |  1 +
 .../queue/src/outbox/typeorm-outbox.repository.ts  | 27 +++---
 15 files changed, 281 insertions(+), 240 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, test-architecture=passed, build=passed |

## Codex review

Full review completed with all seven passes, all 20 changed/untracked files reviewed, no findings, and AC1-AC14 verified. The shared resolver is entity-specific, re-resolves against the current async context without caching, is used by all 13 baseline adapters, and preserves specialized persistence behavior. Current-cycle source-hashed evidence passes lint, typecheck, 70 unit suites/338 tests, architecture, build, and 16 real-infrastructure e2e suites/130 tests. The prior e2e finding is resolved. Technically ready for user acceptance, not completed.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/repos/backend/conventions.md — not approved — Consider documenting the new convention: a TypeORM persistence adapter that needs to participate in TypeOrmUnitOfWork transactions should construct one TypeOrmRepositoryResolver<Entity> per ORM entity it owns (from libs/platform/database) instead of writing its own repositoryFor()-style method, so future adapters follow the shared primitive introduced by MEMORIES-0007 instead of reintroducing the duplicated pattern.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
