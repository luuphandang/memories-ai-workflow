# Báo cáo MEMORIES-0002 — [AUTH] Implement Account, User Profile and Portal Authorization Foundation

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `3`
- Change cycle hiện hành: `2`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0002/task.md`
- `ai/tasks/MEMORIES-0002/changes/cycle-001/requirement-addendum.md`
- `ai/tasks/MEMORIES-0002/changes/cycle-002/requirement-addendum.md`

## Nội dung triển khai

This attempt (implementation attempt 5, review cycle 3) resolves fix-request-review-3.md's single `major` finding against the cycle-3/review-3 worktree state, without touching anything else. The finding: `CreateAccountUseCase`'s duplicate-phone check (`existsByProviderAndIdentifier`, create-account.use-case.ts:96) is a preflight read, not a lock — two concurrent `POST /auth/register` requests for the same phone can both pass it before either commits. The database's partial unique index (`UQ_identity_auth_identities_provider_identifier`) is the real source of truth and correctly rejects the loser's INSERT, but `TypeOrmAuthIdentityRepository.save()` previously let that raw `QueryFailedError` propagate unchanged, and `GlobalExceptionFilter` maps any exception it doesn't recognize (including `QueryFailedError`) to a generic HTTP 500 — so the loser of the race got an opaque server error instead of the AC46-required `phone_already_exists`/409 business error, even though the losing transaction itself still rolled back correctly (no partial state was ever left; only the *reported status code* was wrong). Fixed by adding a `translateUniqueViolation` step inside `TypeOrmAuthIdentityRepository.save()` (`libs/modules/identity-access/src/infrastructure/persistence/typeorm-auth-identity.repository.ts`): it catches `QueryFailedError`, checks the wrapped Postgres driver error for SQLSTATE `23505` (unique_violation) against the named constraint `UQ_identity_auth_identities_provider_identifier`, and if both match, throws `DomainError.conflict('phone_already_exists', ...)` — the exact error `GlobalExceptionFilter` already maps to 409, and the identical code/message the preflight check already throws for the non-racy case. Any other `QueryFailedError` (unrelated constraint, unrelated table) is rethrown unchanged, so this only narrows the one specific race, not error handling generally. This repository method is shared by both `CreateAccountUseCase` (registration/admin account creation) and `ChangeAccountPhoneUseCase` (which has the exact same TOCTOU shape with its own `existsByProviderAndIdentifier` preflight, change-account-phone.use-case.ts:50-53), so the fix closes the race for both call sites, not only registration, without touching either use case's code. Added a new, real-Postgres e2e test to `apps/api/test/auth-flow.e2e-spec.ts` — 'lets exactly one of two concurrent registrations for the same phone succeed, rejecting the other with a 409 business error and no partial state' — that fires two concurrent `POST /auth/register` requests with the same phone through the real HTTP layer, asserts the response statuses are exactly `[201, 409]` (never 500) with the loser's body carrying `errorCode: 'phone_already_exists'`, then queries the real `AccountRepository`/`AuthIdentityRepository`/`UserProfileRepository`/`AccountRoleRepository` (already exported from each module's public-api.ts by a prior attempt) to confirm the winner has exactly one committed `AuthIdentity`/`UserProfile`/`AccountRole` graph, and finally logs in with the registered credentials end to end to prove the committed account is fully usable. Every deterministic validation command was re-run from a clean shell against the live worktree and real infrastructure (memories-test-postgres) after this change: lint, typecheck, unit tests (unchanged: 54 suites/244 tests — this fix touches only infrastructure/e2e code, no new unit-testable logic was introduced beyond what the e2e test already exercises against the real database), build, architecture (0 violations, 390 modules), migration run+revert+run, and the full e2e suite (6 suites/42 tests, up from 6/41 — the one new concurrency test), plus every skill-required deterministic check script. No other file, use case, or already-passed criterion from the prior cycle-3/review-2-fix submission was touched.

Prior attempts (preserved for context):

Attempt 4 #1 (AC47): the centralized password policy referenced by task.md §19 did not actually exist — `RegisterDto`, `CreateAccountDto` and `ChangeAccountPasswordDto` each hard-coded their own `@MinLength(8)`/`@MaxLength(255)`, and neither `CreateAccountUseCase` nor `ChangeAccountPasswordUseCase` validated password length at all, so any caller invoking those use cases directly (bypassing HTTP DTO validation) could hash and persist an out-of-policy password. Fixed by adding one new module, `libs/modules/identity-access/src/domain/value-objects/password-policy.ts`, exporting `PASSWORD_POLICY` (MIN_LENGTH/MAX_LENGTH constants) and `assertPasswordPolicy()` (throws `DomainError.validation`, mapped to HTTP 400 by the existing `GlobalExceptionFilter` — the same status a DTO-level failure already produced). All three DTOs now derive their `@MinLength`/`@MaxLength` decorator arguments from `PASSWORD_POLICY` instead of duplicating the literals, and `CreateAccountUseCase.execute`/`ChangeAccountPasswordUseCase.execute` both call `assertPasswordPolicy()` before hashing, inside the transaction, so the policy is enforced at the application/domain boundary regardless of caller. New unit coverage: `password-policy.spec.ts` (boundary values, and that the thrown error never echoes the password), plus new negative-path tests in `create-account.use-case.spec.ts` and a new `change-account-password.use-case.spec.ts` (didn't exist before this attempt) proving each use case rejects and persists nothing for a policy-violating password. #2 (AC51): the only prior 'transaction' tests used a mocked `UnitOfWork` whose fake `withTransaction` just calls the callback inline, so they could prove step *sequencing* but never a real rollback. Added `apps/api/test/register-transaction-rollback.e2e-spec.ts`, a real-Postgres e2e spec that boots the full `AppModule` with `USER_PROFILE_PROVISIONER` overridden (via Nest's `overrideProvider`) to record the `accountId` it was called with and then reject — forcing `CreateAccountUseCase`'s real transaction to fail on its last write (§8 step 6) after Account/AuthIdentity/AccountRole have already been written in the same transaction — then queries the same real repositories the app itself uses (`AccountRepository.findById`/`findByIdIncludingDeleted`, `AuthIdentityRepository.findAllByAccountId`, `AccountRoleRepository.listRoleIdsForAccount`, `UserProfileRepository.existsByAccountId`) by that captured id and asserts all four are absent. This required exporting `ACCOUNT_REPOSITORY`/`AccountRepository` and `AUTH_IDENTITY_REPOSITORY`/`AuthIdentityRepository` from identity-access's `public-api.ts`, and `USER_PROFILE_REPOSITORY`/`UserProfileRepository` from user-profiles' `public-api.ts` — following the exact precedent already set by `ACCOUNT_ROLE_REPOSITORY`/`ROLE_REPOSITORY` being exported there for the same test-only reason. Every deterministic validation command was re-run from a clean shell against the live worktree and real infrastructure (memories-test-postgres) after these changes: lint, typecheck, unit tests (54 suites/244 tests, up from 52/236 — the three new spec files), build, architecture (0 violations, 390 modules), migration run+revert+run, and the full e2e suite (6 suites/41 tests, up from 5/40 — the new rollback spec), plus every skill-required deterministic check script. No other file from the prior cycle-3/review-1-fix submission was touched. Cycle 3 itself resumed a worktree that already contained a substantially complete MEMORIES-0002 backend (Account/AuthIdentity/UserProfile/RBAC/JWT/portal-authorization/request-context/audit/CRUD) with all 9 blockers/majors from changes-review fix-request-review-1.md already fixed in-place (verified by direct code inspection plus check_auth_invariants.py/check_port_bindings.py/check_module_wiring.py, not re-implemented). This cycle's net-new work is the changes/cycle-002 addendum: public self-registration `POST /auth/register` (RegisterDto, RegisterUseCase, RegisterResponseDto, AuthController wiring, module registration, unit tests, e2e tests, docs). RegisterUseCase composes the existing CreateAccountUseCase (§8 transaction, unchanged) and then issues a PUBLIC-portal session the same way LoginUseCase does, so a successful registration returns an access token + refresh cookie equivalent to a PUBLIC login for the account just created, with no client-controllable portal/role/permission/accountId. This continuation (attempt 2, after the prior attempt was marked failed) re-ran every deterministic validation command from scratch against the live worktree rather than trusting the prior self-report: lint, typecheck, unit test (52 suites/236 tests), build, architecture (0 violations/385 modules), migration run+revert+run against real Postgres, and the full real-infrastructure e2e suite. All four e2e specs now pass, including apps/api/test/media-upload-flow.e2e-spec.ts, which the prior cycle's self-report had marked failing on a local EADDRINUSE :::9464 conflict — that port was free on re-verification (lsof confirmed no listener), so the failure was confirmed transient/environmental as suspected, not a code defect, and AC40 is now fully passed rather than partial. Spot-checked source for fix-request-review-1 items #1, #2 and #8 directly (JwtAuthGuard's live ACCOUNT_LOOKUP-backed status/tokenVersion check with the DI token genuinely wired in identity-access.module.ts; PortalGuard + RequirePortal('ADMIN') on UserProfileController; only status/phone/password PATCH routes on AccountController, no generic no-op PATCH) to confirm the prior cycle's claims were not fabricated. Review cycle 1 (codex) then returned one `major` finding — AC50 failed because `POST /auth/register` only declared its 201 Swagger response, omitting the reachable 400/403/409/429 error outcomes. Fixed by adding a shared `ErrorResponseDto` next to `GlobalExceptionFilter` (the same envelope every route's non-2xx response already uses), documenting all four error statuses with `@ApiResponse` on `AuthController.register`, and — since the `verify-openapi-contract` skill's deterministic checker (`check_openapi_contract.py`) had never actually been run in this task before, a real gap this cycle closes — creating the worktree-root `openapi-contracts.json` manifest plus a new generated-document contract test (`apps/api/test/openapi-contract.e2e-spec.ts`) that builds the real `buildOpenApiDocument()` output and asserts exactly `[201, 400, 403, 409, 429]` are documented for the route. No other files from the prior cycle-3 submission were touched.

## Repository đã thay đổi

### backend

- `libs/modules/identity-access/src/presentation/http/register.dto.ts`
- `libs/modules/identity-access/src/presentation/http/auth-response.dto.ts`
- `libs/modules/identity-access/src/application/use-cases/register.use-case.ts`
- `libs/modules/identity-access/src/presentation/http/auth.controller.ts`
- `libs/modules/identity-access/src/identity-access.module.ts`
- `libs/modules/identity-access/test/register.use-case.spec.ts`
- `apps/api/test/auth-flow.e2e-spec.ts`
- `docs/guides/authentication-flow.md`
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
- `libs/modules/identity-access/src/domain/value-objects/password-policy.ts`
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
- `libs/modules/identity-access/src/presentation/http/change-account-password.dto.ts`
- `libs/modules/identity-access/src/presentation/http/change-account-phone.dto.ts`
- `libs/modules/identity-access/src/presentation/http/change-account-status.dto.ts`
- `libs/modules/identity-access/src/presentation/http/create-account.dto.ts`
- `libs/modules/identity-access/src/presentation/http/list-accounts.dto.ts`
- `libs/modules/identity-access/src/presentation/http/login.dto.ts`
- `libs/modules/identity-access/src/public-api.ts`
- `libs/modules/identity-access/test/account.spec.ts`
- `libs/modules/identity-access/test/auth-identity.spec.ts`
- `libs/modules/identity-access/test/change-account-password.use-case.spec.ts`
- `libs/modules/identity-access/test/create-account.use-case.spec.ts`
- `libs/modules/identity-access/test/local-authentication.provider.spec.ts`
- `libs/modules/identity-access/test/login.use-case.spec.ts`
- `libs/modules/identity-access/test/password-policy.spec.ts`
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
- `apps/api/src/business-modules.ts`
- `apps/cli/src/business-modules.ts`
- `apps/cli/src/cli-runner.service.ts`
- `apps/cli/src/commands/seed.command.ts`
- `apps/scheduler/src/business-modules.ts`
- `apps/worker/src/business-modules.ts`
- `docs/architecture/module-boundaries.md`
- `nest-cli.json`
- `package.json`
- `package-lock.json`
- `tsconfig.json`
- `apps/api/test/media-upload-flow.e2e-spec.ts`
- `libs/platform/security/src/global-exception.filter.ts`
- `apps/api/test/openapi-contract.e2e-spec.ts`
- `apps/api/test/register-transaction-rollback.e2e-spec.ts`
- `openapi-contracts.json`


## Git diff stat

### backend

```text
apps/api/src/business-modules.ts                   |   2 +
 apps/api/test/media-upload-flow.e2e-spec.ts        |  51 +++++--
 apps/cli/src/business-modules.ts                   |   2 +
 apps/cli/src/cli-runner.service.ts                 |  11 +-
 apps/cli/src/commands/seed.command.ts              |  11 +-
 apps/scheduler/src/business-modules.ts             |   2 +
 apps/worker/src/business-modules.ts                |   2 +
 docs/architecture/module-boundaries.md             |  23 +++
 docs/guides/authentication-flow.md                 | 165 +++++++++++++++++++--
 .../identity-access/src/identity-access.module.ts  | 116 ++++++++++++++-
 libs/modules/identity-access/src/public-api.ts     |  12 ++
 .../configuration/src/config/auth.config.ts        |  12 ++
 .../configuration/src/schemas/env.schema.ts        |   6 +
 libs/platform/database/src/public-api.ts           |   1 +
 .../security/src/authorization.contract.ts         |  38 ++++-
 .../security/src/global-exception.filter.ts        |  14 ++
 libs/platform/security/src/jwt-auth.guard.ts       |  61 +++++++-
 libs/platform/security/src/public-api.ts           |   5 +
 .../platform/security/src/refresh-cookie.helper.ts |  20 +++
 libs/platform/security/src/security.module.ts      |  17 ++-
 libs/platform/security/test/jwt-auth.guard.spec.ts |  56 +++++++
 libs/shared/kernel/src/public-api.ts               |   1 +
 nest-cli.json                                      |   9 ++
 package-lock.json                                  |   1 +
 package.json                                       |   1 +
 tsconfig.json                                      |   4 +
 26 files changed, 591 insertions(+), 52 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, build=passed, test-architecture=passed, migration-run=passed, migration-revert=passed, migration-run=passed, test-e2e=passed |

## Codex review

Coverage is complete across all seven review passes. The full backend tracked diff and untracked implementation inventory were reviewed, all applicable vertical-slice gates passed, current-cycle validation is complete, and every prior blocking finding is resolved. No blocker, major, minor, or note finding remains; the implementation is technically ready for user acceptance.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- Không có.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
