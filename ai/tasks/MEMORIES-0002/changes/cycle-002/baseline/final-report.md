# Báo cáo MEMORIES-0002 — [AUTH] Implement Account, User Profile and Portal Authorization Foundation

## Kết quả kỹ thuật

- Trạng thái workflow: `awaiting_user_acceptance`
- Implementation cycle: `2`
- Change cycle hiện hành: `1`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `pending`

**Kết quả đã đạt cổng kỹ thuật nhưng chưa được xem là hoàn thành.** Người dùng cần kiểm tra và chạy `./ai/bin/ai task accept MEMORIES-0002`. Nếu chưa đúng, dùng `request-change` thay vì accept.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0002/task.md`
- `ai/tasks/MEMORIES-0002/changes/cycle-001/requirement-addendum.md`

## Nội dung triển khai

Resolved all 9 findings in fix-request-review-1.md for the identity-access/user-profiles backend foundation (Account/AuthIdentity/UserProfile/RefreshSession/Role/Permission, phone+password login, portal authorization, request context, audit metadata, Account/UserProfile CRUD). Items 1-8 (live Account status/tokenVersion check on every protected request, PortalGuard on the UserProfile admin API, atomic compare-and-swap refresh rotation, userProfileId retained across refresh, OriginGuard CSRF/origin protection on /auth/refresh, RequestContext-sourced audit actor, UserProfile.dateOfBirth date-only transformer, and removing the fake generic PATCH /accounts/:accountId) were already implemented in the worktree carried over from implementation cycle 1's later attempts; this cycle verified each by code inspection and passing tests. Item 9 (missing deterministic validation evidence) was resolved by actually running the full configured validation matrix: lint, typecheck, unit tests, build, architecture boundary check, migration run+revert against a disposable empty database, and E2E tests against the real docker-compose test stack. Running the E2E suite surfaced one genuine regression -- auth-flow.e2e-spec.ts's refresh/logout tests predated the OriginGuard fix and never set an Origin header, so they failed 403 once CORS_ORIGIN was configured -- which was fixed by adding an Origin header to every refresh call and a new explicit valid/invalid-origin test. Per requirement-addendum.md cycle 1, this epic is backend-only from this cycle forward; no frontend work was in scope or attempted.

## Repository đã thay đổi

### backend

- `apps/api/test/auth-flow.e2e-spec.ts`
- `apps/api/test/media-upload-flow.e2e-spec.ts`
- `apps/api/src/business-modules.ts`
- `apps/cli/src/business-modules.ts`
- `apps/cli/src/cli-runner.service.ts`
- `apps/cli/src/commands/seed.command.ts`
- `apps/scheduler/src/business-modules.ts`
- `apps/worker/src/business-modules.ts`
- `docs/architecture/module-boundaries.md`
- `docs/guides/authentication-flow.md`
- `libs/modules/identity-access/src/identity-access.module.ts`
- `libs/modules/identity-access/src/public-api.ts`
- `libs/modules/identity-access/src/application/ports/authentication-provider.port.ts`
- `libs/modules/identity-access/src/application/ports/password-hasher.port.ts`
- `libs/modules/identity-access/src/application/ports/phone-normalizer.port.ts`
- `libs/modules/identity-access/src/application/use-cases/change-account-password.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/change-account-phone.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/change-account-status.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/create-account.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/delete-account.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/get-account.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/list-accounts.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/login.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/logout.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/refresh-session.use-case.ts`
- `libs/modules/identity-access/src/application/use-cases/seed-roles-and-permissions.use-case.ts`
- `libs/modules/identity-access/src/domain/accounts/account-status.ts`
- `libs/modules/identity-access/src/domain/accounts/account.repository.ts`
- `libs/modules/identity-access/src/domain/accounts/account.ts`
- `libs/modules/identity-access/src/domain/auth-identities/auth-identity.repository.ts`
- `libs/modules/identity-access/src/domain/auth-identities/auth-identity.ts`
- `libs/modules/identity-access/src/domain/auth-identities/auth-provider.ts`
- `libs/modules/identity-access/src/domain/permissions/permission.repository.ts`
- `libs/modules/identity-access/src/domain/permissions/permission.ts`
- `libs/modules/identity-access/src/domain/permissions/role-permission.repository.ts`
- `libs/modules/identity-access/src/domain/roles/account-role.repository.ts`
- `libs/modules/identity-access/src/domain/roles/role.repository.ts`
- `libs/modules/identity-access/src/domain/roles/role.ts`
- `libs/modules/identity-access/src/domain/sessions/portal.ts`
- `libs/modules/identity-access/src/domain/sessions/refresh-session.repository.ts`
- `libs/modules/identity-access/src/domain/sessions/refresh-session.ts`
- `libs/modules/identity-access/src/domain/value-objects/phone-number.vo.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/account-role.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/account.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/account.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/auth-identity.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/auth-identity.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/permission.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/permission.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/refresh-session.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/refresh-session.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/role-permission.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/role.mapper.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/role.orm-entity.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-account-role.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-account.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-auth-identity.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-permission.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-refresh-session.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-role-permission.repository.ts`
- `libs/modules/identity-access/src/infrastructure/persistence/typeorm-role.repository.ts`
- `libs/modules/identity-access/src/infrastructure/security/account-lookup.service.ts`
- `libs/modules/identity-access/src/infrastructure/security/account-phone-search.service.ts`
- `libs/modules/identity-access/src/infrastructure/security/local-authentication.provider.ts`
- `libs/modules/identity-access/src/infrastructure/security/permission-checker.service.ts`
- `libs/modules/identity-access/src/infrastructure/security/phone-normalizer.ts`
- `libs/modules/identity-access/src/infrastructure/security/scrypt-password-hasher.ts`
- `libs/modules/identity-access/src/presentation/http/account-response.dto.ts`
- `libs/modules/identity-access/src/presentation/http/account.controller.ts`
- `libs/modules/identity-access/src/presentation/http/auth-response.dto.ts`
- `libs/modules/identity-access/src/presentation/http/auth.controller.ts`
- `libs/modules/identity-access/src/presentation/http/change-account-password.dto.ts`
- `libs/modules/identity-access/src/presentation/http/change-account-phone.dto.ts`
- `libs/modules/identity-access/src/presentation/http/change-account-status.dto.ts`
- `libs/modules/identity-access/src/presentation/http/create-account.dto.ts`
- `libs/modules/identity-access/src/presentation/http/list-accounts.dto.ts`
- `libs/modules/identity-access/src/presentation/http/login.dto.ts`
- `libs/modules/identity-access/test/account.spec.ts`
- `libs/modules/identity-access/test/auth-identity.spec.ts`
- `libs/modules/identity-access/test/create-account.use-case.spec.ts`
- `libs/modules/identity-access/test/local-authentication.provider.spec.ts`
- `libs/modules/identity-access/test/login.use-case.spec.ts`
- `libs/modules/identity-access/test/permission-checker.service.spec.ts`
- `libs/modules/identity-access/test/phone-normalizer.spec.ts`
- `libs/modules/identity-access/test/phone-number.spec.ts`
- `libs/modules/identity-access/test/scrypt-password-hasher.spec.ts`
- `libs/modules/identity-access/test/seed-roles-and-permissions.use-case.spec.ts`
- `libs/modules/user-profiles/src/application/use-cases/create-user-profile.use-case.ts`
- `libs/modules/user-profiles/src/application/use-cases/delete-user-profile.use-case.ts`
- `libs/modules/user-profiles/src/application/use-cases/get-user-profile.use-case.ts`
- `libs/modules/user-profiles/src/application/use-cases/list-user-profiles.use-case.ts`
- `libs/modules/user-profiles/src/application/use-cases/update-user-profile.use-case.ts`
- `libs/modules/user-profiles/src/domain/user-profile.repository.ts`
- `libs/modules/user-profiles/src/domain/user-profile.ts`
- `libs/modules/user-profiles/src/infrastructure/contracts/user-profile-lookup.service.ts`
- `libs/modules/user-profiles/src/infrastructure/contracts/user-profile-provisioner.service.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/typeorm-user-profile.repository.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/user-profile.mapper.ts`
- `libs/modules/user-profiles/src/infrastructure/persistence/user-profile.orm-entity.ts`
- `libs/modules/user-profiles/src/presentation/http/create-user-profile.dto.ts`
- `libs/modules/user-profiles/src/presentation/http/list-user-profiles.dto.ts`
- `libs/modules/user-profiles/src/presentation/http/update-user-profile.dto.ts`
- `libs/modules/user-profiles/src/presentation/http/user-profile-response.dto.ts`
- `libs/modules/user-profiles/src/presentation/http/user-profile.controller.ts`
- `libs/modules/user-profiles/src/public-api.ts`
- `libs/modules/user-profiles/src/user-profiles.module.ts`
- `libs/modules/user-profiles/test/create-user-profile.use-case.spec.ts`
- `libs/modules/user-profiles/test/user-profile.spec.ts`
- `libs/modules/user-profiles/tsconfig.lib.json`
- `libs/platform/configuration/src/config/auth.config.ts`
- `libs/platform/configuration/src/schemas/env.schema.ts`
- `libs/platform/database/src/audit.orm-entity.ts`
- `libs/platform/database/src/migrations/1722540000000-CreateIdentityAccessSchema.ts`
- `libs/platform/database/src/migrations/1722550000000-CreateUserProfilesSchema.ts`
- `libs/platform/database/src/public-api.ts`
- `libs/platform/security/src/authorization.contract.ts`
- `libs/platform/security/src/identity.contracts.ts`
- `libs/platform/security/src/jwt-auth.guard.ts`
- `libs/platform/security/src/origin.guard.ts`
- `libs/platform/security/src/portal.guard.ts`
- `libs/platform/security/src/public-api.ts`
- `libs/platform/security/src/refresh-cookie.helper.ts`
- `libs/platform/security/src/request-context.middleware.ts`
- `libs/platform/security/src/request-context.ts`
- `libs/platform/security/src/security.module.ts`
- `libs/platform/security/test/jwt-auth.guard.spec.ts`
- `libs/platform/security/test/origin.guard.spec.ts`
- `libs/platform/security/test/portal.guard.spec.ts`
- `libs/shared/kernel/src/entities/auditable-props.ts`
- `libs/shared/kernel/src/public-api.ts`
- `nest-cli.json`
- `package.json`
- `package-lock.json`
- `tsconfig.json`


## Git diff stat

### backend

```text
apps/api/src/business-modules.ts                   |   2 +
 apps/api/test/media-upload-flow.e2e-spec.ts        |  51 ++++++---
 apps/cli/src/business-modules.ts                   |   2 +
 apps/cli/src/cli-runner.service.ts                 |  11 +-
 apps/cli/src/commands/seed.command.ts              |  11 +-
 apps/scheduler/src/business-modules.ts             |   2 +
 apps/worker/src/business-modules.ts                |   2 +
 docs/architecture/module-boundaries.md             |  23 +++++
 docs/guides/authentication-flow.md                 |  49 +++++++--
 .../identity-access/src/identity-access.module.ts  | 114 +++++++++++++++++++--
 libs/modules/identity-access/src/public-api.ts     |   7 ++
 .../configuration/src/config/auth.config.ts        |  12 +++
 .../configuration/src/schemas/env.schema.ts        |   6 ++
 libs/platform/database/src/public-api.ts           |   1 +
 .../security/src/authorization.contract.ts         |  38 ++++++-
 libs/platform/security/src/jwt-auth.guard.ts       |  61 ++++++++++-
 libs/platform/security/src/public-api.ts           |   5 +
 .../platform/security/src/refresh-cookie.helper.ts |  20 ++++
 libs/platform/security/src/security.module.ts      |  17 ++-
 libs/platform/security/test/jwt-auth.guard.spec.ts |  56 ++++++++++
 libs/shared/kernel/src/public-api.ts               |   1 +
 nest-cli.json                                      |   9 ++
 package-lock.json                                  |   1 +
 package.json                                       |   1 +
 tsconfig.json                                      |   4 +
 25 files changed, 455 insertions(+), 51 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, build=passed, test-architecture=passed, migration-run=passed, migration-revert=passed, migration-run=passed, test-e2e=passed |

## Codex review

Không phát hiện finding blocker hoặc major. Implementation cycle 2 xử lý đầy đủ các finding trước, các runtime path xuyên layer được wiring, evidence matrix không có khoảng trống, và toàn bộ validation bắt buộc của cycle hiện hành đã pass. Bản triển khai backend sẵn sàng để người dùng nghiệm thu.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- ai/repos/backend/architecture.md — not approved — Consider documenting the AccountController contract decision explicitly (no generic PATCH /accounts/:accountId; status/phone/password each have a dedicated endpoint because Account carries no other mutable field) so future reviewers don't re-flag the missing route as a defect.
- ai/repos/backend/testing.md — not approved — Note that any E2E test hitting POST /auth/refresh must set an Origin header matching a CORS_ORIGIN allowlist entry (OriginGuard), since supertest sends no Origin by default and the app enforces this whenever CORS_ORIGIN is configured.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
