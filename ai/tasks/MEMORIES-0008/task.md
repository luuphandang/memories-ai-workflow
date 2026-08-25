# MEMORIES-0008: Consolidate auditable aggregate-root behavior and soft-delete queries

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0008`

## Goal

Loại bỏ code audit và soft-delete bị lặp trong các aggregate root bằng một
`AuditableAggregateRoot` dùng chung, đồng thời chuẩn hóa cách repository truy vấn bản ghi đã xóa
qua options có ba chế độ `exclude`, `include`, `only` (mặc định `exclude`).

Giữ hierarchy đơn giản:

```text
Entity
└── AggregateRoot
    ├── aggregate không audit
    └── AuditableAggregateRoot
```

Không tạo `SoftDeletableAggregateRoot`: soft delete là một audit transition cập nhật
`deletedAt`, `deletedBy`, `updatedAt`, `updatedBy`, tương tự `touch`.

## Background

Các aggregate auditable hiện tự lặp `audit`, `isDeleted`, `touch`, `softDelete`, kiểm tra trực tiếp
`deletedAt`, và mapping sáu audit fields. Persistence layer cũng lặp `IsNull()` hoặc
`deleted_at IS NULL`; `AccountRepository` còn có API riêng `findByIdIncludingDeleted`, trong khi
custom find/exists/list chưa có contract chung để chọn deleted records.

Đây là refactor domain và persistence contract nội bộ, không phải tính năng HTTP mới.

## Current system inventory

Backend hiện có 10 aggregate kế thừa `AggregateRoot`.

### Phải migrate

| Aggregate | Audit | `isDeleted` | `touch` | `softDelete` | Repository lọc deleted |
| --- | --- | --- | --- | --- | --- |
| `Account` | Có | Có | Có | Có, strict | Có |
| `AuthIdentity` | Có | Có | Có | Có, chưa strict | Có |
| `UserProfile` | Có | Có | Có | Có, strict | Có |
| `Product` | Có | Qua `isActive` | Không | Không | Có |
| `CardTemplate` | Có | Qua `isActive` | Không | Không | Có |
| `Role` | Có | Không | Không | Không | Có |
| `Permission` | Có | Không | Không | Không | Có |

Đây là baseline; implementer phải search lại toàn backend và bổ sung mọi aggregate dùng
`AuditableProps` tương đương được phát hiện.

### Không migrate trong task này

- `MediaAsset`: lifecycle theo processing status, không có audit fields.
- `RefreshSession`: lifecycle theo revoke/expire, không dùng soft delete.
- `CatalogTerm`: chỉ có `createdAt`, `updatedAt`; chuyển đổi cần schema/migration.

### Persistence duplication

- `findById`, business-key lookup, provider lookup, `exists`, `list` và custom query hard-code điều
  kiện loại deleted records.
- Mapper của bảy aggregate trong scope lặp mapping `createdBy`, `createdAt`, `updatedBy`,
  `updatedAt`, `deletedBy`, `deletedAt`.
- `Repository.delete()` hiện là physical delete, dễ bị nhầm với domain soft delete.

## Scope

### 1. Auditable aggregate abstraction

- [ ] Tạo `AuditableAggregateRoot<TProps extends AuditableProps>` trong shared kernel, kế thừa
  `AggregateRoot<TProps>`.
- [ ] Cung cấp một implementation dùng chung cho `audit` read-only, `isDeleted`, protected
  `touch(actorId, occurredAt)` và `softDelete(actorId, occurredAt)`.
- [ ] Không tạo `SoftDeletableAggregateRoot` hoặc hierarchy tương đương dành riêng cho soft delete.
- [ ] Không inject `Clock`, `RequestContext` hoặc infrastructure dependency vào domain/shared
  kernel; application layer tiếp tục cung cấp actor và thời điểm.
- [ ] Soft delete lần hai dùng strict semantics: trả domain conflict và không ghi đè delete metadata
  ban đầu.
- [ ] Giữ/cho phép override error code cụ thể hiện hữu nếu contract hiện tại phụ thuộc vào nó.
- [ ] Không thêm `restore` khi chưa có use case nghiệp vụ.

### 2. Migrate aggregate hiện tại

- [ ] Migrate `Account`, `AuthIdentity`, `UserProfile`, `Product`, `CardTemplate`, `Role`,
  `Permission` sang abstraction mới.
- [ ] Xóa implementation trùng của `audit`, `isDeleted`, `touch`, `softDelete`; dùng `isDeleted`
  thay kiểm tra trực tiếp `props.deletedAt` khi phù hợp.
- [ ] Mutation đang cập nhật audit phải tiếp tục gọi `touch`; không tự động đổi behavior mutation
  khác ngoài scope.
- [ ] Giữ invariants, status transitions, token version, domain events và observable errors.
- [ ] Không migrate `CatalogTerm`, `MediaAsset`, `RefreshSession` để làm hierarchy đồng đều.

### 3. Soft-delete repository query contract

- [ ] Tạo shared options với semantics tương đương:

  ```ts
  type DeletedRecordMode = 'exclude' | 'include' | 'only';
  interface RepositoryQueryOptions {
    deleted?: DeletedRecordMode;
  }
  ```

  Implementer có thể chọn tên cuối cùng rõ nghĩa hơn nhưng ba giá trị và semantics là bắt buộc.
- [ ] Khi options/property bị bỏ qua, mặc định là `exclude`.
- [ ] `exclude` chỉ lấy `deleted_at IS NULL`; `include` không lọc `deleted_at`; `only` chỉ lấy
  `deleted_at IS NOT NULL`.
- [ ] Chỉ áp dụng options cho repository quản lý auditable/soft-deletable aggregate; không ép
  `MediaAssetRepository`, `RefreshSessionRepository`, join-table repository nhận options vô nghĩa.
- [ ] Áp dụng cho mọi method đọc liên quan: `findById`, custom `find/findAll`, business-key lookup,
  `exists`, `list` và count/total.
- [ ] Thay `findByIdIncludingDeleted` bằng `findById(id, { deleted: 'include' })` hoặc API tên cuối
  cùng tương ứng.
- [ ] Caller không truyền options phải giữ behavior hiện tại: không thấy và không đếm deleted rows.
- [ ] Query có join áp dụng mode cho aggregate chính; joined records giữ business semantics hiện tại
  trừ khi contract method nói khác.

### 4. TypeORM helpers

- [ ] Tạo helper dùng chung tại platform database/infrastructure để chuyển deleted mode thành
  TypeORM find condition và query-builder predicate.
- [ ] Không lặp switch ba mode hoặc hard-code `IsNull()` khi helper dùng được.
- [ ] Query-builder helper chỉ nhận alias do implementation kiểm soát; không ghép request input vào
  SQL.
- [ ] Giữ transaction-aware repository resolution và query semantics hiện tại.
- [ ] Không đưa TypeORM dependency vào shared kernel/domain.

### 5. Audit mapper helpers

- [ ] Tạo helper chung cho sáu audit fields theo hai chiều ORM → domain props và domain → ORM.
- [ ] Migrate mapper trong scope khi không mất type safety/behavior chuyên biệt.
- [ ] Helper không phụ thuộc concrete ORM entity của bounded context và round-trip đủ actor,
  timestamp, nullability.

### 6. Physical delete naming

- [ ] Kiểm kê caller của `Repository.delete()` và xác nhận physical-delete semantics.
- [ ] Ưu tiên đổi thành `hardDelete()` nếu migrate toàn bộ caller an toàn trong task.
- [ ] Nếu đổi tên gây breaking scope không hợp lý, giữ `delete()` nhưng document rõ physical
  semantics và ghi follow-up; không âm thầm đổi implementation thành soft delete.
- [ ] Soft delete tiếp tục đi qua `aggregate.softDelete(...)` rồi `repository.save(aggregate)`.

### 7. Tests and documentation

- [ ] Unit test `AuditableAggregateRoot` qua concrete test aggregate.
- [ ] Test helper/repository cho default và đủ ba deleted modes.
- [ ] Regression test repository/use case đại diện và cascade xóa Account.
- [ ] Cập nhật public exports và knowledge/convention nếu abstraction trở thành chuẩn bền vững.

## Acceptance criteria

- [ ] AC1 — Có đúng một `AuditableAggregateRoot` dùng chung cho `audit`, `isDeleted`, `touch`,
  `softDelete`; không có aggregate abstraction riêng cho soft delete.
- [ ] AC2 — Bảy aggregate trong scope kế thừa abstraction mới và không còn implementation lặp.
- [ ] AC3 — `MediaAsset`, `RefreshSession`, `CatalogTerm` giữ model/schema hiện tại.
- [ ] AC4 — `audit` không cho caller mutate props; `touch` protected và cập nhật đúng update fields.
- [ ] AC5 — Soft delete lần đầu ghi delete/update metadata cùng actor/thời điểm; lần hai conflict và
  không thay metadata ban đầu.
- [ ] AC6 — Existing error codes và observable business behavior quan trọng không regression.
- [ ] AC7 — Query options hỗ trợ `exclude`, `include`, `only`; omitted mặc định `exclude`.
- [ ] AC8 — TypeORM find options và query builder đều thực thi đúng semantics ba mode.
- [ ] AC9 — Mọi method đọc aggregate trong scope nhận/truyền mode nhất quán, gồm find, exists, list,
  count/total và business-key lookup.
- [ ] AC10 — Không còn `findByIdIncludingDeleted`; caller dùng options chung.
- [ ] AC11 — Default callers không thấy/đếm deleted rows; `include` trả cả hai loại; `only` chỉ trả
  deleted rows.
- [ ] AC12 — Audit mapper helpers round-trip đủ sáu fields và loại bỏ mapping lặp trong scope khi an
  toàn.
- [ ] AC13 — Physical delete không đổi semantics ngầm và được đặt tên/document rõ.
- [ ] AC14 — Không có TypeORM, request context hoặc clock dependency rò rỉ vào domain abstraction.
- [ ] AC15 — Không đổi HTTP API, database schema/migration hoặc business behavior ngoài contract nội
  bộ được mô tả.
- [ ] AC16 — Tests bao phủ base behavior, ba modes/default, mapper round-trip, Account cascade, ít
  nhất một `exists` và một paginated `list`.
- [ ] AC17 — `lint`, `typecheck`, `test`, `test:architecture`, `build` đều pass.
- [ ] AC18 — Handoff liệt kê inventory cuối, files/contracts đã migrate, quyết định
  `delete`/`hardDelete`, evidence và duplication có chủ ý còn lại.

## Out of scope

- Tạo `SoftDeletableAggregateRoot`, restore API/use case hoặc lifecycle mới.
- Thêm audit/soft-delete schema cho `CatalogTerm`, `MediaAsset`, `RefreshSession`.
- Expose deleted mode qua HTTP DTO nếu API hiện tại không yêu cầu.
- Thay đổi partial unique index, schema hoặc migration.
- Tự động soft-delete relation/join rows ngoài cascade hiện hữu.
- Generic CRUD repository, frontend refactor hoặc TypeORM concern trong shared kernel.

## Technical notes

- Abstraction dự kiến: `libs/shared/kernel/src/aggregates/auditable-aggregate-root.ts`.
- Audit contract: `libs/shared/kernel/src/entities/auditable-props.ts`.
- TypeORM audit base: `libs/platform/database/src/audit.orm-entity.ts`.
- Deleted query types phải domain-safe; TypeORM conversion helpers nằm ở infrastructure/platform.
- Có thể dùng interface riêng cho auditable repositories thay vì sửa base `Repository`, nhằm tránh
  options xuất hiện trên repository không hỗ trợ soft delete.
- Không giả định TypeORM `withDeleted` nếu entity không dùng `@DeleteDateColumn`; helper phải phù hợp
  mapping hiện tại.

## Validation

```text
npm run lint
npm run typecheck
npm run test
npm run test:architecture
npm run build
```

Nếu integration test cần database thật, handoff phải ghi command, môi trường và evidence; không dùng
mock rồi tuyên bố database behavior đã được xác minh.

## Constraints

- Không quản lý worktree/branch, commit hoặc push.
- Không đọc secret hoặc `.env*`.
- Không sửa ngoài backend worktree khai báo, trừ task artifact/report do workflow quản lý.
