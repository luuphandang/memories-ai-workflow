# Request Context — Data Flow

## HTTP request (`apps/api`)

```text
Inbound HTTP request
  → CorrelationMiddleware (ObservabilityModule, chạy trước theo thứ tự import trong app.module.ts)
      đọc header x-request-id/x-correlation-id, sinh nếu thiếu, mở CorrelationContext.run()
  → RequestContextMiddleware (SecurityModule, chạy sau)
      đọc lại CorrelationContext.current() để tái dùng cùng requestId/correlationId,
      mở RequestContext.run() với store rỗng (actor/roles/permissions chưa có)
  → guard chain (JwtAuthGuard, PermissionsGuard, ...)
      JwtAuthGuard verify JWT rồi MUTATE trực tiếp object store hiện tại (không mở run() mới)
      để gán accountId/sessionId/portal/userProfileId/roles/permissions
  → use case / application layer
      đọc RequestContext.currentActorId() để stamp audit column (createdBy/updatedBy/deletedBy)
  → TypeOrmUnitOfWork.withTransaction()
      kiểm tra TypeOrmQueryRunnerContext.get(): nếu đã có QueryRunner active (lời gọi lồng nhau)
      thì join transaction hiện tại; nếu chưa có thì mở QueryRunner mới và TypeOrmQueryRunnerContext.run()
  → repository
      đọc TypeOrmQueryRunnerContext.get() để lấy đúng QueryRunner của transaction đang chạy
  → logger (pino-http, chạy factory genReqId/customProps NGOÀI Nest DI/request scope)
      đọc CorrelationContext.requestId()/correlationId() để gắn vào mọi log line
```

## Background job (`apps/worker`, qua BullMQ)

```text
Request/use case gọi BullMqPublisher.publish()
  → envelope.correlationId mặc định = CorrelationContext.correlationId() của request đang publish
    (hoặc override qua options.correlationId)
  → job được ghi vào Redis/BullMQ, KHÔNG mang theo actor/roles/permissions, chỉ mang correlationId

BullMqWorkerRunner.process(job)
  → mở MỘT CorrelationContext.run() MỚI, độc lập, seed lại { requestId, correlationId } từ envelope
    (job không kế thừa CLS store của request HTTP đã publish nó)
  → handler.handle(envelope) chạy trong context mới này
  → RequestContext KHÔNG được khôi phục cho job hiện tại (hành vi hiện tại, không phải bỏ sót —
    đã chốt tiếp tục giữ nguyên khi migrate sang nestjs-cls, xem decisions.md DEC-001)
```

## CLI (`apps/cli`)

```text
CliRunnerService.run(argv)
  → requestContext.runAsSystem(() => command.run(args))
      mở RequestContext.run() với store isSystemActor: true, accountId: null
  → command / use case
      RequestContext.currentActorId() trả về SYSTEM_ACTOR_ID (không phải null)
      → audit column của mọi write do CLI thực hiện được stamp SYSTEM_ACTOR_ID
```

## Isolation invariant

Mỗi luồng trên (một request HTTP, một job, một lệnh CLI) phải thấy một context độc lập — không
bao giờ đọc/ghi chéo store của một luồng khác đang chạy đồng thời trên cùng process. Đây là lý do
gốc `TypeOrmQueryRunnerContext` dùng `AsyncLocalStorage` thay vì field mutable thường
(`typeorm-unit-of-work.ts` có comment giải thích rủi ro cụ thể: field mutable là singleton dùng
chung, một request có thể ghi đè QueryRunner của request khác).
