# Báo cáo MEMORIES-0008 — Consolidate auditable aggregate-root behavior and soft-delete queries

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0008/task.md`

## Nội dung triển khai

All 7 slices complete: 'auditable-aggregate-abstraction', 'migrate-aggregate-hi-n-t-i', 'soft-delete-repository-query-contract', 'typeorm-helpers', 'audit-mapper-helpers', 'physical-delete-naming' and 'tests-and-documentation'. Shared AuditableAggregateRoot<TProps extends AuditableProps> lives in libs/shared/kernel with read-only audit, isDeleted, protected touch, public strict-semantics softDelete and an overridable already-deleted error hook; Account, AuthIdentity, UserProfile, Product, CardTemplate, Role and Permission extend it, with their duplicate audit/isDeleted/touch/softDelete implementations removed. On top of that, the same 7 aggregates' repositories share a domain-safe soft-delete query contract: DeletedRecordMode ('exclude'|'include'|'only') + RepositoryQueryOptions + resolveDeletedRecordMode (default 'exclude') in libs/shared/kernel/src/repositories/repository-query-options.ts, and a new AuditableRepository<TAggregate, TId> interface (repositories/auditable-repository.ts) that only the 7 in-scope repository interfaces extend. Every read method on those 7 repositories (findById, business-key lookups, exists methods, findAllByAccountId, list/count) accepts an optional trailing `options?: RepositoryQueryOptions`; `AccountRepository.findByIdIncludingDeleted` was removed and its two call sites now use `findById(id, { deleted: 'include' })`. The 'typeorm-helpers' slice deduplicated the mode -> query translation itself: the per-repository private `deletedWhere`/`deletedWhereSql` methods (previously duplicated verbatim across all 7 TypeORM repositories) are gone, replaced by two shared functions in libs/platform/database/src/deleted-record-query.helper.ts — `deletedRecordFindWhere<Entity extends AuditableOrmEntity>(mode)` for `FindOptionsWhere`-based find/findOne/count calls and `deletedRecordWhereSql(alias, mode)` for query-builder/raw-SQL predicates. The 'audit-mapper-helpers' slice deduplicated the six-audit-field ORM<->domain mapping itself: a new libs/platform/database/src/audit-props.mapper.ts exports `auditablePropsFromOrmEntity(raw: AuditableOrmEntity): AuditableProps` (ORM -> domain, spread into each mapper's `Aggregate.create({...})` props) and `applyAuditablePropsToOrmEntity<Entity extends AuditableOrmEntity>(entity, audit): Entity` (domain -> ORM, mutates the already-constructed entity in place), exported via public-api.ts. All 7 in-scope mappers (AccountMapper, AuthIdentityMapper, PermissionMapper, RoleMapper, CardTemplateMapper, ProductMapper, UserProfileMapper) had their duplicated 6-line `createdBy/createdAt/updatedBy/updatedAt/deletedBy/deletedAt` block replaced by one call each in `toDomain`/`toPersistence`; CatalogTerm/MediaAsset/RefreshSession mappers (out of scope, confirmed by grep — none reference the six audit fields) are untouched. No TypeORM import was added to shared kernel/domain; every `deletedRecordWhereSql` call site still passes only a repository-controlled literal alias, never request input. This session's 'physical-delete-naming' slice renamed the base `Repository<TAggregate, TId>.delete(id)` to `hardDelete(id)` (libs/shared/kernel/src/repositories/repository.ts) with a doc comment stating physical-delete semantics and the soft-delete alternative. A full-backend caller inventory (grep across apps/libs for every `.delete(` call reaching a domain repository, cross-checked against all 10 classes implementing `Repository`) found the rename fully safe to apply everywhere in one pass: no application/use-case/controller code calls the interface method at all (the two existing delete flows — DeleteAccountUseCase, DeleteUserProfileUseCase — already only call `aggregate.softDelete(...)` then `repository.save(aggregate)`); the only 5 call sites were test-only (2 e2e fixture-cleanup calls in catalog-inactive-terms.e2e-spec.ts, 2 in products.e2e-spec.ts, 1 direct unit-test call in typeorm-catalog-term.repository.spec.ts) plus 3 jest-mock object literals (`delete: jest.fn()`) in use-case spec files. All 10 TypeORM repository implementations (Account, AuthIdentity, UserProfile, Product, CardTemplate, Role, Permission, CatalogTerm, MediaAsset, RefreshSession) and every one of those caller/mock sites were renamed to `hardDelete` in the same pass — no `delete()` naming ambiguity remains anywhere in the codebase. This session's 'tests-and-documentation' slice closed the one substantive gap left by prior sessions' already-thorough test coverage (base AuditableAggregateRoot behavior, all three deleted-mode query paths across 7 repositories, and audit-mapper round-trip were already covered): a dedicated regression test for `DeleteAccountUseCase`, the only Account-cascade delete flow in the codebase, was missing entirely (grepped for existing coverage first — zero hits). Added libs/modules/identity-access/test/delete-account.use-case.spec.ts (4 cases) asserting the full cascade in one mocked transaction: Account soft-deleted with actor/timestamp, every non-already-deleted AuthIdentity soft-deleted and saved (an already-deleted identity is left untouched, not re-thrown), UserProfileProvisioner.deleteByAccountId invoked, RefreshSessionRepository.revokeAllForAccount invoked, a not-found account throws DomainError with zero side effects, and cascading an already-deleted account rejects via the inherited strict softDelete conflict. No source code changed in this slice — it is documentation/test-only. Public exports (libs/shared/kernel/src/public-api.ts, libs/platform/database/src/public-api.ts) were already complete from prior slices (AuditableAggregateRoot, AuditableRepository, RepositoryQueryOptions/DeletedRecordMode/resolveDeletedRecordMode, deletedRecordFindWhere/deletedRecordWhereSql, auditablePropsFromOrmEntity/applyAuditablePropsToOrmEntity all exported), verified again this session. Per common.md/claude-implementer.md's 'không sửa ai/repos trực tiếp' rule, the convention-doc update for this now-durable abstraction is recorded as a proposal in `knowledge_updates` below rather than edited directly.

## Repository đã thay đổi

### backend

- `apps/api/test/register-transaction-rollback.e2e-spec.ts`
- `libs/modules/card-catalog/src/domain/card-template/card-template.repository.ts`
- `libs/modules/card-catalog/src/domain/card-template/card-template.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/typeorm-card-template.repository.ts`
- `libs/modules/card-catalog/test/typeorm-card-template.repository.deleted-mode.spec.ts`
- `libs/modules/identity-access/src/domain/accounts/account.repository.ts`
- `libs/modules/identity-access/src/domain/accounts/account.ts`
- `libs/modules/identity-access/src/domain/auth-identities/auth-identity.repository.ts`
- `libs/modules/identity-access/src/domain/auth-identities/auth-identity.ts`
- `libs/modules/identity-access/src/domain/permissions/permission.repository.ts`
- `libs/modules/identity-access/src/domain/permissions/permission.ts`
- `libs/modules/identity-access/src/domain/roles/role.repository.ts`
- `libs/modules/identity-access/src/domain/roles/role.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-account.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-auth-identity.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-permission.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-role.repository.ts`
- `libs/modules/identity-access/src/infrastructure/security/account-lookup.service.ts`
- `libs/modules/identity-access/test/auth-identity.spec.ts`
- `libs/modules/identity-access/test/typeorm-account.repository.spec.ts`
- `libs/modules/identity-access/test/typeorm-auth-identity.repository.spec.ts`
- `libs/modules/identity-access/test/typeorm-permission.repository.spec.ts`
- `libs/modules/identity-access/test/typeorm-role.repository.spec.ts`
- `libs/modules/product-catalog/src/domain/product/product.repository.ts`
- `libs/modules/product-catalog/src/domain/product/product.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/typeorm-product.repository.ts`
- `libs/modules/product-catalog/test/product.spec.ts`
- `libs/modules/product-catalog/test/typeorm-product.repository.deleted-mode.spec.ts`
- `libs/modules/user-profiles/src/domain/user-profile.repository.ts`
- `libs/modules/user-profiles/src/domain/user-profile.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/typeorm-user-profile.repository.ts`
- `libs/modules/user-profiles/test/typeorm-user-profile.repository.spec.ts`
- `libs/platform/database/src/deleted-record-query.helper.ts`
- `libs/platform/database/src/public-api.ts`
- `libs/platform/database/test/deleted-record-query.helper.spec.ts`
- `libs/shared/kernel/src/aggregates/auditable-aggregate-root.ts`
- `libs/shared/kernel/src/public-api.ts`
- `libs/shared/kernel/src/repositories/auditable-repository.ts`
- `libs/shared/kernel/src/repositories/repository-query-options.ts`
- `libs/shared/kernel/test/auditable-aggregate-root.spec.ts`
- `libs/modules/card-catalog/src/infrastructure/persistence/card-template.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/account.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/auth-identity.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/permission.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/role.mapper.ts`
- `libs/modules/product-catalog/src/infrastructure/persistence/product.mapper.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/user-profile.mapper.ts`
- `libs/platform/database/src/audit-props.mapper.ts`
- `libs/platform/database/test/audit-props.mapper.spec.ts`
- `libs/shared/kernel/src/repositories/repository.ts`
- `apps/api/test/catalog-inactive-terms.e2e-spec.ts`
- `apps/api/test/products.e2e-spec.ts`
- `libs/modules/card-catalog/test/list-card-templates.use-case.spec.ts`
- `libs/modules/catalog/src/infrastructure/persistence/typeorm-catalog-term.repository.ts`
- `libs/modules/catalog/test/list-catalog-terms.use-case.spec.ts`
- `libs/modules/catalog/test/typeorm-catalog-term.repository.spec.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-refresh-session.repository.ts`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts`
- `libs/modules/product-catalog/test/list-products.use-case.spec.ts`
- `libs/modules/identity-access/test/delete-account.use-case.spec.ts`
- `apps/api/test/soft-delete-query-modes.e2e-spec.ts`


## Git diff stat

### backend

```text
apps/api/test/catalog-inactive-terms.e2e-spec.ts   |   4 +-
 apps/api/test/products.e2e-spec.ts                 |   4 +-
 .../test/register-transaction-rollback.e2e-spec.ts |   2 +-
 .../card-template/card-template.repository.ts      |  21 ++++-
 .../src/domain/card-template/card-template.ts      |  10 +-
 .../persistence/card-template.mapper.ts            |  15 +--
 .../typeorm-card-template.repository.ts            |  77 ++++++++++-----
 .../test/list-card-templates.use-case.spec.ts      |   2 +-
 .../persistence/typeorm-catalog-term.repository.ts |   2 +-
 .../test/list-catalog-terms.use-case.spec.ts       |   4 +-
 .../test/typeorm-catalog-term.repository.spec.ts   |   2 +-
 .../src/domain/accounts/account.repository.ts      |  16 ++--
 .../identity-access/src/domain/accounts/account.ts |  32 ++-----
 .../auth-identities/auth-identity.repository.ts    |  14 ++-
 .../src/domain/auth-identities/auth-identity.ts    |  23 +----
 .../domain/permissions/permission.repository.ts    |   8 +-
 .../src/domain/permissions/permission.ts           |   8 +-
 .../src/domain/roles/role.repository.ts            |   8 +-
 .../identity-access/src/domain/roles/role.ts       |   8 +-
 .../infrastructure/persistence/account.mapper.ts   |  15 +--
 .../persistence/auth-identity.mapper.ts            |  15 +--
 .../persistence/permission.mapper.ts               |  15 +--
 .../src/infrastructure/persistence/role.mapper.ts  |  15 +--
 .../persistence/typeorm-account.repository.ts      |  33 ++++---
 .../typeorm-auth-identity.repository.ts            |  62 +++++++++---
 .../persistence/typeorm-permission.repository.ts   |  36 ++++---
 .../typeorm-refresh-session.repository.ts          |   2 +-
 .../persistence/typeorm-role.repository.ts         |  33 ++++---
 .../security/account-lookup.service.ts             |   4 +-
 .../identity-access/test/auth-identity.spec.ts     |  17 ++++
 .../persistence/typeorm-media-asset.repository.ts  |   2 +-
 .../src/domain/product/product.repository.ts       |  18 +++-
 .../product-catalog/src/domain/product/product.ts  |  10 +-
 .../infrastructure/persistence/product.mapper.ts   |  15 +--
 .../persistence/typeorm-product.repository.ts      | 104 ++++++++++++++-------
 .../test/list-products.use-case.spec.ts            |   2 +-
 libs/modules/product-catalog/test/product.spec.ts  |  11 +++
 .../src/domain/user-profile.repository.ts          |  13 ++-
 .../user-profiles/src/domain/user-profile.ts       |  32 ++-----
 .../persistence/typeorm-user-profile.repository.ts |  56 +++++++----
 .../persistence/user-profile.mapper.ts             |  15 +--
 libs/platform/database/src/public-api.ts           |   2 +
 libs/shared/kernel/src/public-api.ts               |   3 +
 libs/shared/kernel/src/repositories/repository.ts  |   7 +-
 44 files changed, 448 insertions(+), 349 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, test-architecture=passed, build=passed |

## Codex review

Full review complete across all 61 changed files and seven required passes. All three prior major findings are resolved, AC1-AC18 are verified, current-cycle unit/e2e/architecture/build evidence and provenance are valid, and no blocking or non-blocking implementation finding remains. The implementation is technically ready for user acceptance; this verdict does not mark the Jira item completed.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/repos/backend/conventions.md — approved — Document the AuditableAggregateRoot<TProps>/AuditableRepository<TAggregate, TId>/RepositoryQueryOptions convention introduced by MEMORIES-0008 as the standard for any future aggregate that needs audit trail + soft delete: (1) extend libs/shared/kernel/src/aggregates/auditable-aggregate-root.ts's AuditableAggregateRoot instead of re-implementing audit/isDeleted/touch/softDelete — `audit` returns a frozen copy (never mutable), `touch` is protected, `softDelete` is strict (second call conflicts via an overridable `alreadyDeletedError()` hook); (2) declare the repository interface via AuditableRepository<TAggregate, TId> (libs/shared/kernel/src/repositories/auditable-repository.ts) rather than the base Repository, and accept an optional trailing `options?: RepositoryQueryOptions` (`{ deleted?: 'exclude' | 'include' | 'only' }`, default 'exclude' via resolveDeletedRecordMode) on every read method (find/exists/list/count/business-key lookup) — never add a bespoke `findByIdIncludingDeleted`-style method; (3) translate the mode to a TypeORM condition via the shared libs/platform/database/src/deleted-record-query.helper.ts functions (deletedRecordFindWhere for FindOptionsWhere, deletedRecordWhereSql for query-builder/raw SQL) instead of writing a new per-repository IsNull()/deleted_at switch; (4) map the six ORM<->domain audit fields via libs/platform/database/src/audit-props.mapper.ts's auditablePropsFromOrmEntity/applyAuditablePropsToOrmEntity instead of six manual field assignments per mapper; (5) name the physical-delete repository method `hardDelete`, never bare `delete`, to keep it visually distinct from `aggregate.softDelete(...) + repository.save(...)`. Not yet added directly to conventions.md per the 'không sửa ai/repos trực tiếp' constraint on implementer agents — a maintainer/orchestrator pass should fold this in as a new bullet once the task is accepted.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
