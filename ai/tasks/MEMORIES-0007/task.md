# MEMORIES-0007: Consolidate transaction-aware TypeORM repository resolution

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0007`

## Goal

Loại bỏ logic lặp lại trong các TypeORM repository của backend, trước hết là pattern
`repositoryFor()` dùng để chọn repository từ active `QueryRunner` hoặc repository được
NestJS inject, bằng một abstraction dùng chung, type-safe và có trách nhiệm rõ ràng.

Refactor phải giữ nguyên toàn bộ observable behavior, transaction semantics, domain repository
contracts và dependency boundaries hiện tại. Kết quả cần làm cho repository implementation ngắn
gọn hơn mà không tạo một generic CRUD repository quá rộng.

## Background

Các persistence adapter hiện tự lặp lại cùng một quyết định:

```ts
const queryRunner = queryRunnerContext.get();
return queryRunner
  ? queryRunner.manager.getRepository(Entity)
  : injectedRepository;
```

Pattern này xuất hiện ở nhiều module. Các adapter quản lý nhiều ORM entity còn có thêm các method
như `variantRepositoryFor()` và `linkRepositoryFor()` với cùng thuật toán. Việc sao chép làm tăng
chi phí bảo trì và tạo nguy cơ repository mới quên tham gia active transaction hoặc triển khai
fallback khác với phần còn lại của hệ thống.

Đây là refactor kỹ thuật của backend persistence infrastructure; không tạo capability hay business
domain mới.

## Current system

- `TypeOrmUnitOfWork` mở transaction và đặt active `QueryRunner` vào
  `TypeOrmQueryRunnerContext`.
- Mỗi TypeORM persistence adapter inject repository mặc định và
  `TypeOrmQueryRunnerContext`, rồi tự triển khai method chọn repository.
- Khi có active transaction, mọi database operation phải sử dụng repository lấy từ
  `queryRunner.manager`; ngoài transaction phải dùng đúng injected repository.
- Nested transaction hiện join transaction ngoài; concurrent execution phải tiếp tục được cô lập.
- Qua khảo sát ban đầu, pattern xuất hiện trong 13 implementation:
  - media: `TypeOrmMediaAssetRepository`;
  - catalog: `TypeOrmCatalogTermRepository`;
  - card catalog: `TypeOrmCardTemplateRepository`;
  - product catalog: `TypeOrmProductRepository`;
  - identity access: account, auth identity, refresh session, role, permission, account-role và
    role-permission repositories;
  - user profiles: `TypeOrmUserProfileRepository`;
  - queue/outbox: `TypeOrmOutboxRepository`.
- Danh sách trên là baseline khảo sát, không phải lý do bỏ qua occurrence tương đương khác được phát
  hiện khi implementer kiểm tra toàn bộ backend worktree.

## Scope

- [ ] Lập inventory tất cả logic TypeORM repository-resolution bị lặp trong backend, gồm các method
  `repositoryFor`, `variantRepositoryFor`, `linkRepositoryFor` và pattern tương đương.
- [ ] Thiết kế một primitive dùng chung tại `libs/platform/database` để resolve TypeORM repository
  theo active `TypeOrmQueryRunnerContext`.
- [ ] Primitive hỗ trợ type-safe cho một hoặc nhiều ORM entity trong cùng persistence adapter.
- [ ] Migrate toàn bộ các occurrence tương đương đã xác định sang primitive chung.
- [ ] Giữ query, mapping, soft-delete, conditional update, upsert, raw SQL và aggregate persistence
  logic chuyên biệt trong repository cụ thể.
- [ ] Bổ sung unit/characterization tests cho resolver dùng chung và các adapter đại diện.
- [ ] Cập nhật public exports, module wiring và repository knowledge nếu abstraction mới tạo ra
  convention bền vững.

## Acceptance criteria

- [ ] AC1 — Có một API dùng chung, type-safe trong `@memories/platform/database` thực hiện việc chọn
  repository: dùng `activeQueryRunner.manager.getRepository(entityTarget)` khi context có active
  runner, nếu không dùng injected fallback repository.
- [ ] AC2 — API dùng chung không giữ `QueryRunner` hoặc resolved transactional repository trong
  mutable singleton state/cache; repository được resolve tại thời điểm operation để không leak giữa
  request/job concurrent hoặc ra ngoài transaction lifecycle.
- [ ] AC3 — Tất cả 13 persistence implementation trong baseline, cùng mọi occurrence tương đương
  khác tìm thấy trong backend, sử dụng abstraction chung; không còn bản sao cục bộ của thuật toán
  `context.get() -> manager.getRepository(...) -> fallback`.
- [ ] AC4 — Repository có nhiều ORM entity, đặc biệt product và card-template repositories, resolve
  đúng từng entity target và đúng injected fallback tương ứng; không nhầm repository giữa aggregate,
  variant hoặc link entity.
- [ ] AC5 — Ngoài transaction, mọi adapter tiếp tục gọi đúng injected TypeORM repository và giữ
  nguyên kết quả, lỗi và side effect hiện có.
- [ ] AC6 — Trong transaction, mọi operation của adapter tiếp tục dùng repository từ chính active
  `QueryRunner`, bao gồm `save`, `delete`, `update`, `upsert`, query builder và raw query.
- [ ] AC7 — Nested transaction, rollback và concurrent transaction isolation của
  `TypeOrmUnitOfWork` không thay đổi; không có operation vô tình thoát ra default DataSource.
- [ ] AC8 — Domain repository interfaces, use-case/controller contracts, API contracts, database
  schema và migrations không thay đổi chỉ để phục vụ refactor này.
- [ ] AC9 — Abstraction mới chỉ giải quyết infrastructure concern về repository resolution; không
  tạo generic CRUD base class ép các domain repository vào cùng hành vi và không để TypeORM dependency
  rò rỉ vào `libs/shared/kernel` hoặc domain/application layers.
- [ ] AC10 — Unit tests của abstraction chứng minh ít nhất: fallback path, active-runner path, đúng
  entity target, resolve lại theo context hiện hành và không reuse transactional repository sau khi
  callback transaction kết thúc.
- [ ] AC11 — Characterization/regression tests đại diện cho cả single-entity và multi-entity adapter
  chứng minh các call được route qua đúng repository trong và ngoài transaction.
- [ ] AC12 — Existing transaction/concurrency tests tiếp tục pass; test mới sẽ fail nếu implementer
  quay lại dùng repository mặc định bên trong active transaction.
- [ ] AC13 — `lint`, `typecheck`, `test`, `test-architecture` và `build` của backend đều pass.
- [ ] AC14 — Implementation handoff ghi rõ inventory đã migrate, abstraction được chọn, test evidence,
  changed files và mọi duplication có chủ ý còn lại kèm lý do.

## Out of scope

- Thay đổi business rules, API behavior, DTO hoặc response schema.
- Thay đổi database schema, tạo migration hoặc sửa dữ liệu.
- Thay thế TypeORM, `TypeOrmUnitOfWork` hoặc cơ chế transaction/context hiện hành.
- Xây dựng generic repository cung cấp CRUD mặc định cho domain aggregates.
- Refactor query SQL/query-builder chuyên biệt chỉ vì chúng dài hoặc giống nhau về cú pháp.
- Refactor frontend hoặc repository khác ngoài backend worktree đã đăng ký.

## Technical notes

- Vị trí abstraction ưu tiên: `libs/platform/database/src/`, export qua
  `libs/platform/database/src/public-api.ts`.
- Ưu tiên một resolver/composition primitive nhỏ thay vì inheritance hierarchy. Implementer có thể
  chọn API cuối cùng nếu đáp ứng toàn bộ acceptance criteria và giải thích trade-off.
- Entity target phải được truyền tường minh để TypeORM trả về repository thuộc đúng
  `QueryRunner.manager`.
- Không cache repository lấy từ `QueryRunner`: lifetime của nó gắn với transaction/connection.
- Dùng CodeGraph và source search để kiểm tra callers, module boundary và toàn bộ occurrence trước
  khi migrate.

## Validation

Chạy tối thiểu:

```text
npm run lint
npm run typecheck
npm run test
npm run test:architecture
npm run build
```

Implementer phải thêm test tập trung vào transaction-aware resolution, không chỉ dựa vào việc các
test nghiệp vụ hiện hữu tình cờ pass.

## Constraints

- Không quản lý worktree/branch.
- Không commit hoặc push.
- Không đọc hoặc ghi secret.
- Chỉ sửa backend worktree đã đăng ký và task evidence/knowledge được workflow cho phép.
- Không làm yếu test, validation, transaction guard hoặc architecture boundary để đạt trạng thái pass.
