# Memories Backend Architecture

## Style
Clean Architecture 4 lớp cho mỗi business module (`domain` / `application` / `infrastructure` / `presentation`), tách biệt `libs/platform/*` (hạ tầng dùng chung: configuration, database, cache, queue, realtime, storage, security, observability, health) khỏi `libs/modules/*` (bounded context nghiệp vụ). Mọi ràng buộc kiến trúc được `depcruise` (`npm run test:architecture`, cấu hình tại `.dependency-cruiser.js`) kiểm tra tự động, không chỉ dựa vào convention.

## Module boundaries
- 1 module chỉ được import từ module khác qua đúng `public-api.ts`/package entry point của module đó (rule `no-cross-module-internal-import`).
- `domain` không được phụ thuộc NestJS/TypeORM/Redis/BullMQ/AWS SDK/Socket.IO/class-validator (rule `domain-no-framework-dependency`), và không được import ngược `application`/`infrastructure`/`presentation` của chính module mình (rule `domain-no-outer-layer-dependency`).
- `application` chỉ khai báo use case + port (interface), không được phụ thuộc `infrastructure`/`presentation` (rule `application-no-infrastructure-or-presentation-dependency`).
- Business module không được phụ thuộc trực tiếp `bullmq`/`@nestjs/bullmq` — phải publish job qua port `BackgroundJobPublisher` (rule `no-direct-bullmq-dependency-in-business-module`).
- Không cho phép circular dependency (rule `no-circular`).

## Request/data flow
`Controller` (presentation, `@nestjs/common` + DTO có `class-validator`/`@ApiProperty`) → `UseCase` (application, implement 1 interface theo pattern chung) → domain entity + repository port → `infrastructure` (TypeORM repository) implement port đó. Request body được validate/transform qua `ValidationPipe` dùng chung (`buildValidationPipe()`), lỗi nghiệp vụ ném dưới dạng `DomainError` (kèm `DomainErrorKind` + `code` ổn định), `GlobalExceptionFilter` (đăng ký global qua `configureApp()`) là nơi DUY NHẤT map exception sang HTTP status + JSON body chuẩn.

## Background jobs/events
Use case publish job qua port `BackgroundJobPublisher` (không import `bullmq` trực tiếp) — `BullMqQueueFactory`/`BullMqWorkerRunner` (`libs/platform/queue`) là adapter thật. Ghi DB + enqueue job nguyên tử nhờ Transactional Outbox Pattern: use case ghi domain state + 1 outbox row trong CÙNG 1 transaction (`UnitOfWork.withTransaction`), `OutboxRelay` (chỉ chạy trong `apps/worker`) poll và publish job thật sau đó. Job thất bại sau khi hết số lần retry được `handleFinalFailure` xử lý; `FailureReconciliationService` (cũng chỉ ở `apps/worker`) quét định kỳ để bắt các job fail-final mà `handleFinalFailure` chính nó cũng từng thất bại. Sự kiện realtime publish qua port `RealtimePublisher` → Socket.IO adapter dùng Redis pub/sub để scale nhiều instance.

## Quyết định không được phá vỡ
- `domain` layer không bao giờ phụ thuộc framework/infrastructure.
- Cross-module import chỉ qua `public-api.ts`.
- Background job chỉ publish qua `BackgroundJobPublisher`, không gọi `bullmq`/`@nestjs/bullmq` trực tiếp từ business module.
- TypeORM `synchronize` tắt ở MỌI environment — thay đổi schema chỉ qua migration.
- Thứ tự graceful shutdown giữa các service dùng chung Queue: `BullMqQueueFactory` đóng kết nối Queue ở phase `BeforeApplicationShutdown` — LUÔN chạy SAU `OnModuleDestroy` của mọi module (đảm bảo bởi chính NestJS, xác minh trong `node_modules/@nestjs/core/nest-application-context.js`) — nên mọi service còn thao tác vào Queue đó (`OutboxRelay`, `FailureReconciliationService`, `BullMqMetricsCollector`) phải dừng hẳn ở `OnModuleDestroy`, không được tự ý đổi sang phase khác (xem doc comment của `libs/platform/queue/src/bullmq/bullmq-queue.factory.ts`).

## Application composition roots

Mọi process import `BUSINESS_MODULES` (`api`, `worker`, `scheduler`, `cli`, và process mới sau này) phải đăng ký đầy đủ platform dependency mà các module đó cần, ví dụ `SecurityModule.register()` khi có `JwtAuthGuard`. Khi thêm dependency cross-cutting, rà toàn bộ `apps/*/src/app.module.ts`; không giả định dependency của API tự có trong process khác. Provider cần được inject ngoài module khai báo phải được export tường minh.
