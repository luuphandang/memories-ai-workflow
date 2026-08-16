# Queue and Background Jobs

## Publication and delivery

- Business modules publish qua port `BackgroundJobPublisher`; không phụ thuộc trực tiếp BullMQ. Khi một use case vừa đổi domain state vừa tạo job, ghi domain state và outbox row trong cùng `UnitOfWork.withTransaction()`, sau đó để `OutboxRelay` publish.
- Transactional outbox được lưu tại `background_jobs.outbox_messages` (không dùng schema `public`); migration và `OutboxMessageOrmEntity` phải luôn khai báo thống nhất schema `background_jobs`.
- BullMQ có semantics at-least-once: redelivery và hai execution chồng nhau là tình huống hợp lệ. Mọi terminal transition phải dùng CAS nguyên tử ở repository, với cả expected status và attempt identity (`jobId`/version) khi nhiều attempt dùng chung trạng thái trung gian.
- Job ID chỉ unique trong một queue. ID phục vụ deduplication nên deterministic; lần reprocess hợp lệ phải dùng ID theo attempt. Không dùng `:` làm delimiter cho custom ID.
- Non-retryable error được chuyển thành `UnrecoverableError`; final-failure detection phải bao phủ cả trường hợp này, không chỉ so `attemptsMade` với `attempts`.

## Reconciliation and pagination

- Trước khi tạo thêm kho reconciliation, ưu tiên nguồn durable sẵn có nếu độc lập với hạ tầng đang lỗi. Failed jobs chỉ là nguồn reconciliation khi retention giữ chúng đủ lâu và thao tác reconcile idempotent.
- Quét backlog theo oldest-first để tránh starvation. Khi vừa đọc vừa xóa, cursor chỉ tiến theo số item được giữ lại; batch đầu bị lỗi không được chặn vĩnh viễn phần còn lại.
- Tác vụ chạy trễ không kế thừa `AsyncLocalStorage`; phải capture `correlationId` và `actorId` vào outbox/job lúc tạo.

## Worker correctness

- Không suy ra quiescence chỉ từ callback hoặc một cặp event: BullMQ còn finalize job sau callback và có nhánh lock-loss/deferred-failure khác nhau. Dùng lifecycle barrier của worker; nếu buộc phải tracking thì namespace theo queue và phủ cả processor `finally` lẫn `completed`/`failed`.
- Mọi `EventEmitter` từ worker/client phải có listener `error`. Async work gọi từ timer hoặc fire-and-forget phải tự catch toàn bộ rejection.
