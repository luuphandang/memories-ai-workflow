# Request Context — Overview

## Mục tiêu

Cung cấp một context runtime dùng chung, cô lập theo request/job/lệnh CLI, để mọi lớp phía dưới
(guard, use case, repository, logger, background job) đọc được actor hiện tại, correlation ID và
transaction/QueryRunner đang active mà không phải truyền tay qua từng tham số hàm.

## Phạm vi

- Chỉ áp dụng cho `apps/backend` (`apps/api`, `apps/worker`, `apps/scheduler`, `apps/cli`,
  `apps/realtime`).
- Không phải một business domain (không có entity/API nghiệp vụ riêng) — đây là platform
  cross-cutting concern, được tiêu thụ bởi hầu hết `libs/modules/*`.
- Trạng thái hiện tại (trước `MEMORIES-0006`): 3 instance `AsyncLocalStorage` độc lập, không chia
  sẻ store. `MEMORIES-0006` migrate cả 3 sang `nestjs-cls`.

## Thành phần source liên quan

- `libs/platform/observability/src/correlation-context.ts`,
  `correlation.middleware.ts`, `logger.module.ts`, `observability.module.ts`.
- `libs/platform/security/src/request-context.ts`, `request-context.middleware.ts`,
  `security.module.ts`, `jwt-auth.guard.ts`.
- `libs/platform/database/src/typeorm-unit-of-work.ts`, `database.module.ts`.
- `libs/platform/queue/src/bullmq/bullmq.publisher.ts`, `bullmq.worker.ts`.
- `apps/cli/src/cli-runner.service.ts`.
- `apps/api/src/app.module.ts` (thứ tự import quyết định thứ tự middleware).
- `libs/platform/context/*` — **lib mới, chưa tồn tại**, kế hoạch tại `decisions.md`: theo
  DEC-002, sở hữu dependency `nestjs-cls` và là nơi DUY NHẤT import trực tiếp `ClsService`/
  `ClsModule`/`ClsServiceManager` trong platform layer, nhưng KHÔNG tự định nghĩa bất kỳ concrete
  domain type nào (không có type gộp kiểu `ApplicationClsStore`, kể cả cho `QueryRunner`) — chỉ
  cung cấp cơ chế generic (typed namespaced slice) để `security`/`observability`/`database` tự
  bind type của mình vào. Theo DEC-003, việc đăng ký `ClsModule.forRoot()` KHÔNG thuộc lib này mà
  thuộc composition root của từng `apps/*` (mỗi Nest application tự gọi một lần).
  `security`/`observability`/`database` đều phụ thuộc vào lib này thay vì `security` phụ thuộc
  trực tiếp `observability` như hiện tại.

## Thuật ngữ

| Thuật ngữ | Mô tả |
|---|---|
| `CorrelationStore` | `{ requestId, correlationId, traceId? }`, seed bởi `CorrelationMiddleware`, đọc bởi logger và job publisher. |
| `RequestContextStore` | Actor/request metadata (`accountId`, `roles`, `permissions`, `portal`, `sessionId`, `isSystemActor`, ...), seed bởi `RequestContextMiddleware`, enrich bởi `JwtAuthGuard`. |
| `TypeOrmQueryRunnerContext` | Store giữ `QueryRunner` active của transaction hiện tại, dùng để phát hiện `withTransaction` lồng nhau (reentrant). |
| `SYSTEM_ACTOR_ID` | UUID hằng số (`00000000-0000-0000-0000-000000000000`) stamp vào audit column khi `RequestContextStore.isSystemActor` là `true`. Chỉ CLI (`CliRunnerService` qua `runAsSystem()`) set cờ này hiện nay — worker job không có `RequestContextStore` nào cả nên `currentActorId()` trả về `null` (không phải `SYSTEM_ACTOR_ID`), và scheduler chưa có consumer nào đọc `RequestContext`. Phân biệt với `null` (request ẩn danh, không có actor xác thực). |
| `isSystemActor` | Cờ trên `RequestContextStore`, chỉ được set `true` bởi `RequestContext.runAsSystem()` (dùng bởi CLI). Một request HTTP ẩn danh có `accountId: null, isSystemActor: false`; một job worker không có `RequestContextStore` nào để đọc cờ này từ (`currentActorId()` trả `null` do thiếu context, không phải do cờ `false`). |
| `runAsSystem()` | Helper của `RequestContext` chạy một callback dưới context actor hệ thống (dùng bởi `CliRunnerService` cho mọi lệnh CLI). |
| `ClsService` / `ClsStore` | Khái niệm của `nestjs-cls` — service/DI-injectable bọc quanh một `AsyncLocalStorage` dùng chung, sẽ thay thế cả 3 store trên sau `MEMORIES-0006`. |
| `ClsServiceManager.getClsService()` | Accessor tĩnh của `nestjs-cls` dùng ở nơi không chạy trong Nest DI/request scope (ví dụ factory `genReqId`/`customProps` của pino-http). |
