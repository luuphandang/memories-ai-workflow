# MEMORIES-0001: [TECH] Initialize Project Architecture and Folder Structure

## Jira

* Type: `epic`
* Parent: `-`
* Epic: `MEMORIES-0001`

## Goal

Khởi tạo kiến trúc nền tảng và cấu trúc thư mục chuẩn cho toàn bộ hệ thống MEMORIES, bao gồm:

* Backend NestJS.
* Website public Next.js.
* Website admin Next.js.
* Background worker sử dụng BullMQ.
* PostgreSQL, TypeORM, Redis và AWS S3.
* Realtime communication.
* Logging, monitoring và health check.
* Docker cho môi trường phát triển và triển khai.
* CI/CD cho kiểm tra chất lượng, build và phát hành theo phiên bản.

Kiến trúc cần đáp ứng các mục tiêu:

1. Hỗ trợ phát triển nhanh trong giai đoạn đầu dưới dạng modular monolith.
2. Phân tách rõ ràng giữa business domain và infrastructure.
3. Hạn chế coupling giữa các module nghiệp vụ.
4. Cho phép dùng lại các cấu hình và thành phần hạ tầng trong nhiều module.
5. Cho phép mở rộng thêm application process, worker hoặc integration mới mà không phải thay đổi lớn cấu trúc hiện tại.
6. Chuẩn bị sẵn ranh giới module để có thể tách thành microservice khi hệ thống phát triển đủ lớn.
7. Chuẩn hóa cách tổ chức source code, cấu hình, testing, migration, documentation và deployment cho toàn bộ đội ngũ phát triển.
8. Đảm bảo source code có thể được kiểm tra, build và triển khai nhất quán giữa local, development, staging và production.

## Background

MEMORIES là nền tảng phục vụ ba nhóm nghiệp vụ chính:

1. **Tạo kỷ niệm**

   * Quản lý mẫu thiệp.
   * Thiết kế và cá nhân hóa thiệp.
   * Tải lên hình ảnh, video và tài nguyên thiết kế.
   * Lưu bản nháp và quản lý phiên bản thiết kế.
   * Xuất thiệp thành hình ảnh hoặc PDF.
   * Chia sẻ thiệp đến người nhận.

2. **Trao gửi kỷ niệm**

   * Quản lý sản phẩm quà tặng.
   * Quản lý giỏ hàng và thanh toán.
   * Quản lý đơn hàng.
   * Quản lý vận chuyển.
   * Quản lý sản phẩm cá nhân hóa.
   * Tiếp nhận và xử lý yêu cầu đặt làm riêng.
   * Quản lý sản xuất và kho hàng.

3. **Lưu giữ kỷ niệm**

   * Quản lý thiệp đã tạo, đã gửi và đã nhận.
   * Quản lý bộ sưu tập.
   * Quản lý ngày đáng nhớ.
   * Gửi lời nhắc và thông báo.
   * Quản lý nội dung, hình ảnh và dữ liệu cá nhân của người dùng.

Hệ thống có nhiều tác vụ không nên xử lý trực tiếp trong HTTP request, ví dụ:

* Xử lý hình ảnh.
* Sinh thumbnail.
* Kiểm tra file tải lên.
* Xuất thiệp thành hình ảnh hoặc PDF.
* Gửi email.
* Gửi thông báo.
* Tạo báo cáo.
* Dọn dẹp file tạm.
* Xử lý dữ liệu định kỳ.
* Thực hiện các tác vụ có retry.

Trong giai đoạn hiện tại, hệ thống sử dụng **BullMQ và Redis** cho toàn bộ background job.

RabbitMQ và Kafka chưa được tích hợp trong phạm vi Epic này. Tuy nhiên, các module nghiệp vụ không được phụ thuộc trực tiếp vào BullMQ. Việc gửi và xử lý background job phải đi qua abstraction hoặc application port để có thể thay thế hoặc bổ sung message broker trong tương lai.

Kiến trúc cần được thiết kế theo các nguyên tắc:

* Modular monolith.
* Clean Architecture.
* SOLID.
* Dependency inversion.
* Configuration as code.
* Environment-based configuration.
* Reusable infrastructure modules.
* Explicit module boundaries.
* Infrastructure implementation nằm phía sau interface hoặc injection token.
* Không đặt business logic trong controller, queue processor, cron job hoặc framework adapter.

## Current system

Hiện tại hệ thống đang ở giai đoạn khởi tạo kiến trúc và chưa có một cấu trúc thống nhất cho toàn bộ backend và frontend.

### Backend

* Sử dụng NestJS.
* Sử dụng PostgreSQL và TypeORM.
* Sử dụng Redis.
* Sử dụng BullMQ cho background job.
* Chưa tích hợp RabbitMQ.
* Chưa tích hợp Kafka.
* Cần hỗ trợ lưu trữ file trên AWS S3 bằng presigned URL.
* Cần hỗ trợ realtime bằng Socket.IO.
* Cần có Swagger/OpenAPI.
* Cần có hệ thống logging, metrics, tracing và health check.
* Cần tách HTTP API và background worker thành các process có thể chạy độc lập.
* Chưa có quy ước thống nhất cho:

  * Module boundaries.
  * Clean Architecture layers.
  * Shared abstractions.
  * Queue registration.
  * Queue producer.
  * Queue processor.
  * Retry và backoff.
  * Job naming.
  * Job payload.
  * Configuration validation.
  * Database migration.
  * Error handling.
  * Logging.
  * Testing.
  * Deployment.

### Frontend

* Sử dụng Next.js App Router.
* Có hai ứng dụng độc lập:

  * Public website.
  * Admin website.
* Hai ứng dụng cần nằm trong cùng một repository.
* Sử dụng Tailwind CSS.
* Sử dụng shadcn/ui và Radix UI.
* Sử dụng TanStack Query cho dữ liệu tương tác phía client.
* Sử dụng React Hook Form và Zod cho biểu mẫu.
* Cần dùng chung:

  * UI components.
  * Design tokens.
  * API client.
  * Authentication.
  * Validation.
  * Utilities.
  * TypeScript configuration.
  * ESLint configuration.
* Chưa có quy ước thống nhất về route group, feature folder, shared package và module boundary.

### CI/CD và release

* Cần chuẩn hóa pipeline kiểm tra chất lượng source code.
* Cần build Docker image bất biến.
* Production deployment phải được thực hiện theo release branch có phiên bản, ví dụ:

```text
release/v1.0.0
```

* Không triển khai production trực tiếp từ `develop`, `feature/*` hoặc một commit chưa thuộc release.
* Artifact được kiểm thử tại staging phải là chính artifact được triển khai lên production.
* Cần hỗ trợ rollback theo release version.

## Scope

### 1. Repository structure

* [ ] Khởi tạo hai repository độc lập:

```text
backend/
frontend/
```

* [ ] Thiết lập README cấp repository.
* [ ] Thiết lập `.editorconfig`.
* [ ] Thiết lập `.gitignore`.
* [ ] Thiết lập `.dockerignore`.
* [ ] Thiết lập file môi trường mẫu.
* [ ] Thiết lập quy ước branch, commit và pull request.
* [ ] Thiết lập CODEOWNERS nếu repository hỗ trợ.
* [ ] Tài liệu hóa cách cài đặt và chạy dự án ở local.

### 2. Backend workspace

* [ ] Khởi tạo NestJS workspace theo cấu trúc modular monolith.
* [ ] Tách các application process:

```text
apps/
├── api/
├── worker/
├── realtime/
├── scheduler/
└── cli/
```

* [ ] `apps/api` chịu trách nhiệm:

  * REST API.
  * Authentication và authorization.
  * Swagger/OpenAPI.
  * Health check.
  * Presigned URL.
  * Các request đồng bộ.
  * Gửi background job thông qua application port.

* [ ] `apps/worker` chịu trách nhiệm:

  * Chạy BullMQ Worker.
  * Xử lý background job.
  * Retry job.
  * Ghi nhận trạng thái job.
  * Ghi log và metric cho từng lần xử lý.

* [ ] `apps/realtime` chịu trách nhiệm:

  * Socket.IO gateway.
  * Xác thực kết nối.
  * Notification realtime.
  * Trạng thái xử lý file.
  * Trạng thái xuất thiệp.
  * Trạng thái đơn hàng và sản xuất.
  * Redis adapter khi chạy nhiều instance.

* [ ] `apps/scheduler` chịu trách nhiệm:

  * Tạo scheduled job.
  * Gửi job sang BullMQ.
  * Dọn dẹp file tạm.
  * Nhắc ngày đáng nhớ.
  * Thực thi retention policy.
  * Không chứa business logic lớn.

* [ ] `apps/cli` hỗ trợ:

  * Seed dữ liệu.
  * Backfill dữ liệu.
  * Import template.
  * Reprocess job.
  * Tác vụ bảo trì có kiểm soát.

### 3. Backend business modules

* [ ] Khởi tạo cấu trúc module theo bounded context:

```text
libs/modules/
├── identity-access/
├── customers/
├── privacy/
├── card-catalog/
├── card-designs/
├── media/
├── memories/
├── product-catalog/
├── product-customization/
├── inventory/
├── carts/
├── checkout/
├── orders/
├── payments/
├── shipping/
├── custom-orders/
├── production/
├── promotions/
├── reviews/
├── content/
├── notifications/
├── support/
├── reporting/
└── audit/
```

* [ ] Các module chưa có nghiệp vụ cụ thể có thể được tạo ở mức skeleton hoặc được ghi nhận trong tài liệu roadmap.
* [ ] Mỗi module phải có ranh giới public API rõ ràng.
* [ ] Module khác chỉ được phép import từ `public-api.ts` hoặc package entry point.
* [ ] Không import trực tiếp implementation nội bộ của module khác.

### 4. Clean Architecture

* [ ] Chuẩn hóa cấu trúc mỗi backend module:

```text
module/
├── src/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── presentation/
│   ├── module.ts
│   └── public-api.ts
└── test/
```

* [ ] `domain` không được phụ thuộc vào:

  * NestJS.
  * TypeORM.
  * Redis.
  * BullMQ.
  * AWS SDK.
  * Socket.IO.
  * Class Validator.
  * HTTP DTO.

* [ ] `application` khai báo use case và các port cần thiết.

* [ ] `infrastructure` triển khai database, cache, storage và queue adapter.

* [ ] `presentation` chứa controller, HTTP request/response, websocket gateway hoặc queue processor adapter.

* [ ] Business logic không được đặt trong:

  * Controller.
  * Queue processor.
  * Socket gateway.
  * Scheduler.
  * TypeORM entity.
  * External SDK adapter.

### 5. Shared abstractions

* [ ] Khởi tạo shared kernel cho những abstraction thực sự dùng lại:

```text
libs/shared/kernel/
├── entities/
├── value-objects/
├── aggregates/
├── use-cases/
├── repositories/
├── mappers/
├── results/
├── events/
├── identifiers/
└── errors/
```

* [ ] Cung cấp các abstraction cần thiết, ví dụ:

  * `Entity`.
  * `AggregateRoot`.
  * `ValueObject`.
  * `UseCase`.
  * `Repository`.
  * `Mapper`.
  * `UnitOfWork`.
  * `Clock`.
  * `IdGenerator`.
  * `Result`.
  * `PaginatedResult`.

* [ ] Không tạo một `BaseService`, `BaseController` hoặc `CommonUtils` lớn chứa các hành vi không liên quan.

* [ ] Chỉ đưa thành phần vào shared khi đã có nhu cầu dùng lại rõ ràng.

* [ ] Shared module không được phụ thuộc ngược vào business module.

### 6. Platform modules

* [ ] Khởi tạo các module nền tảng dùng lại:

```text
libs/platform/
├── configuration/
├── database/
├── cache/
├── queue/
├── storage/
├── realtime/
├── observability/
├── security/
└── health/
```

* [ ] Mỗi platform module có:

  * Configuration interface.
  * Injection token.
  * Module registration.
  * Adapter implementation.
  * Error mapping.
  * Test cơ bản.
  * Public entry point.

* [ ] Các platform module hỗ trợ cấu hình bằng:

  * `register()`.
  * `registerAsync()`.
  * Factory provider.
  * Environment variables.
  * Dependency injection.

* [ ] Không đọc trực tiếp `process.env` trong business module.

* [ ] Toàn bộ environment variable được đọc và kiểm tra tại configuration layer.

* [ ] Cấu hình không hợp lệ phải làm ứng dụng fail fast khi bootstrap.

### 7. Configuration management

* [ ] Sử dụng một configuration module tập trung.
* [ ] Phân tách configuration theo miền:

```text
configuration/
├── app.config.ts
├── database.config.ts
├── redis.config.ts
├── bullmq.config.ts
├── s3.config.ts
├── auth.config.ts
├── realtime.config.ts
├── observability.config.ts
└── security.config.ts
```

* [ ] Validation toàn bộ environment variable bằng schema.

* [ ] Hỗ trợ configuration cho:

  * Local.
  * Test.
  * Development.
  * Staging.
  * Production.

* [ ] Không commit secret vào repository.

* [ ] Cung cấp `.env.example` có mô tả rõ từng biến.

* [ ] Secret production được lấy từ secret manager hoặc CI/CD environment.

* [ ] Cấu hình phải có kiểu dữ liệu rõ ràng và không truyền chuỗi environment thô vào business module.

### 8. BullMQ architecture

* [ ] Tích hợp BullMQ với Redis cho background job.
* [ ] BullMQ là queue implementation duy nhất trong phạm vi Epic này.
* [ ] Không tích hợp RabbitMQ.
* [ ] Không tích hợp Kafka.
* [ ] Không để business module phụ thuộc trực tiếp vào `@nestjs/bullmq` hoặc class của BullMQ.
* [ ] Khai báo abstraction cho việc gửi background job, ví dụ:

```ts
export interface BackgroundJobPublisher {
  publish<TPayload>(
    jobName: string,
    payload: TPayload,
    options?: BackgroundJobOptions,
  ): Promise<string>;
}
```

* [ ] BullMQ adapter triển khai abstraction trên.
* [ ] Sử dụng injection token thay vì khởi tạo queue trực tiếp trong business service.
* [ ] Chuẩn hóa cấu trúc queue:

```text
libs/platform/queue/
├── contracts/
│   ├── background-job-publisher.ts
│   ├── background-job-handler.ts
│   ├── background-job-options.ts
│   └── background-job-envelope.ts
├── bullmq/
│   ├── bullmq.module.ts
│   ├── bullmq.config.ts
│   ├── bullmq-queue.factory.ts
│   ├── bullmq.publisher.ts
│   ├── bullmq.worker.ts
│   ├── bullmq.events.ts
│   ├── bullmq.health-indicator.ts
│   └── bullmq.errors.ts
├── registry/
│   ├── queue.registry.ts
│   ├── job-handler.registry.ts
│   └── queue.tokens.ts
└── public-api.ts
```

* [ ] Hỗ trợ đăng ký queue bằng cấu hình tập trung.
* [ ] Cho phép module đăng ký producer mà không cần biết thông tin Redis.
* [ ] Cho phép worker đăng ký handler theo job name.
* [ ] Chuẩn hóa tên queue và job.
* [ ] Job name phải có namespace theo business domain, ví dụ:

```text
media.generate-thumbnail.v1
media.scan-upload.v1
card.render-image.v1
card.render-pdf.v1
notification.send-email.v1
report.generate.v1
```

* [ ] Job payload phải được định nghĩa bằng contract có version.

* [ ] Job envelope phải hỗ trợ tối thiểu:

  * Job ID.
  * Job name.
  * Version.
  * Created time.
  * Correlation ID.
  * Causation ID nếu có.
  * Actor hoặc user ID nếu phù hợp.
  * Payload.

* [ ] Hỗ trợ cấu hình mặc định:

  * Attempts.
  * Backoff.
  * Delay.
  * Priority.
  * Timeout nếu được hỗ trợ ở handler layer.
  * Remove on complete.
  * Remove on fail.
  * Job retention.
  * Concurrency.
  * Rate limiter.

* [ ] Cho phép override cấu hình theo từng queue hoặc job.

* [ ] Có strategy tạo deterministic job ID cho các job yêu cầu idempotency.

* [ ] Processor phải xử lý idempotent đối với job có khả năng retry.

* [ ] Cấu hình retry phải phân biệt:

  * Lỗi có thể retry.
  * Lỗi không thể retry.
  * Lỗi validation.
  * Lỗi business rule.
  * Lỗi external dependency.

* [ ] Có cơ chế ghi nhận failed job và hỗ trợ reprocess có kiểm soát.

* [ ] Có log cho:

  * Job added.
  * Job active.
  * Job completed.
  * Job failed.
  * Job retried.
  * Job stalled.
  * Job duration.

* [ ] Có metric cho:

  * Waiting jobs.
  * Active jobs.
  * Completed jobs.
  * Failed jobs.
  * Delayed jobs.
  * Job processing duration.
  * Retry count.
  * Queue lag.

* [ ] Có health check cho kết nối Redis và BullMQ.

* [ ] Queue configuration phải được dùng lại bởi API, worker, scheduler và CLI.

* [ ] Việc bổ sung queue mới không yêu cầu sửa trực tiếp bootstrap logic của toàn bộ ứng dụng.

* [ ] Tài liệu hóa cách:

  * Tạo queue.
  * Khai báo job contract.
  * Publish job.
  * Tạo handler.
  * Cấu hình retry.
  * Kiểm thử processor.
  * Reprocess failed job.

### 9. Database and TypeORM

* [ ] Tích hợp PostgreSQL với TypeORM.

* [ ] Cấu hình datasource tập trung và tái sử dụng.

* [ ] API, worker, scheduler và CLI sử dụng chung database configuration.

* [ ] Production không sử dụng `synchronize: true`.

* [ ] Thiết lập migration:

  * Generate.
  * Create.
  * Run.
  * Revert.
  * Show.

* [ ] Migration phải chạy bằng CLI hoặc deployment job riêng.

* [ ] Thiết lập base repository hoặc repository utilities ở mức phù hợp.

* [ ] Không để domain entity phụ thuộc TypeORM.

* [ ] Tách domain entity và TypeORM persistence entity.

* [ ] Không tạo TypeORM relation trực tiếp xuyên bounded context.

* [ ] Module lưu ID của aggregate thuộc module khác thay vì phụ thuộc ORM entity.

* [ ] Hỗ trợ transaction abstraction hoặc unit of work.

* [ ] Có test database configuration và migration bootstrap.

### 10. Redis and cache

* [ ] Tích hợp Redis thông qua platform cache module.

* [ ] Redis connection được dùng lại giữa:

  * Cache.
  * BullMQ.
  * Realtime adapter khi phù hợp.

* [ ] Không tạo nhiều Redis connection không cần thiết.

* [ ] Cho phép cấu hình connection riêng cho BullMQ khi hạ tầng production yêu cầu.

* [ ] Cache được truy cập qua abstraction.

* [ ] Business module không phụ thuộc trực tiếp Redis client.

* [ ] Hỗ trợ:

  * TTL.
  * Namespaced key.
  * Serialization.
  * Cache invalidation.
  * Graceful error handling.

* [ ] Có health check và logging cho Redis.

### 11. AWS S3 and media storage

* [ ] Tạo storage abstraction không phụ thuộc trực tiếp AWS SDK.

* [ ] Tạo S3 adapter triển khai storage abstraction.

* [ ] Hỗ trợ:

  * Tạo presigned upload URL.
  * Tạo presigned download URL.
  * Kiểm tra object.
  * Xóa object.
  * Đọc metadata.
  * Kiểm tra size và MIME type.

* [ ] Không lưu presigned URL vào database.

* [ ] Chỉ lưu:

  * Bucket.
  * Object key.
  * MIME type.
  * File size.
  * Checksum nếu có.
  * Owner.
  * Purpose.
  * Processing status.
  * Retention information.

* [ ] Chuẩn hóa prefix hoặc bucket theo loại dữ liệu:

```text
temporary-uploads/
private-originals/
processed-assets/
public-assets/
```

* [ ] Luồng xử lý file sử dụng BullMQ:

  * Client upload trực tiếp lên S3.
  * API xác nhận upload hoàn thành.
  * API publish background job.
  * Worker kiểm tra hoặc xử lý file.
  * Worker cập nhật trạng thái.
  * Hệ thống gửi notification hoặc realtime event.

* [ ] Validate extension, MIME type, size và ownership.

* [ ] Thiết kế sẵn port cho malware scanning; việc tích hợp scanner thực tế có thể được thực hiện ở task riêng.

### 12. Realtime

* [ ] Khởi tạo Socket.IO gateway dưới dạng application process riêng hoặc adapter có thể chạy độc lập.
* [ ] Hỗ trợ xác thực socket connection.
* [ ] Chuẩn hóa event name và payload.
* [ ] Event contract phải có version khi cần.
* [ ] Business module không gọi trực tiếp Socket.IO server.
* [ ] Sử dụng realtime publisher abstraction.
* [ ] Cho phép API hoặc worker publish realtime event thông qua adapter.
* [ ] Hỗ trợ Redis adapter để scale nhiều instance.
* [ ] Có logging cho connection, disconnection và publish failure.
* [ ] Có health check cho realtime process.

### 13. Authentication and security foundation

* [ ] Chuẩn bị module authentication và authorization.

* [ ] Hỗ trợ access token có thời hạn ngắn.

* [ ] Hỗ trợ refresh token trong HttpOnly cookie.

* [ ] Refresh token được rotate và có thể revoke.

* [ ] Không lưu access token trong localStorage.

* [ ] Cấu hình cookie theo môi trường.

* [ ] Hỗ trợ:

  * CORS configuration.
  * Helmet hoặc security headers.
  * Request validation.
  * Payload size limit.
  * Rate limit.
  * Request ID.
  * Correlation ID.
  * Sanitized error response.

* [ ] Không log:

  * Password.
  * Access token.
  * Refresh token.
  * Cookie.
  * Presigned URL đầy đủ.
  * Dữ liệu thanh toán nhạy cảm.
  * Nội dung thiệp riêng tư.

* [ ] Chuẩn bị authorization abstraction cho role và permission.

* [ ] Admin authentication phải có khả năng bổ sung MFA ở task sau.

### 14. Swagger and API conventions

* [ ] Tích hợp Swagger/OpenAPI.

* [ ] Swagger có thể bật hoặc tắt theo environment.

* [ ] Chuẩn hóa:

  * API prefix.
  * API version.
  * Request validation.
  * Response envelope nếu sử dụng.
  * Error code.
  * Pagination.
  * Sorting.
  * Filtering.
  * Date-time format.

* [ ] API error không trả stack trace ở production.

* [ ] OpenAPI document có thể được export thành file.

* [ ] Frontend có thể sinh API client từ OpenAPI.

* [ ] Có script kiểm tra OpenAPI generation.

### 15. Observability

* [ ] Tích hợp structured logging.

* [ ] Log ở định dạng JSON cho staging và production.

* [ ] Mỗi request và job có:

  * Request ID.
  * Correlation ID.
  * Trace ID nếu có.
  * Service name.
  * Module name.
  * Environment.
  * Duration.

* [ ] API và worker sử dụng cùng logging abstraction.

* [ ] Tích hợp metrics endpoint cho Prometheus hoặc cơ chế tương đương.

* [ ] Chuẩn bị OpenTelemetry cho distributed tracing.

* [ ] Chuẩn bị cấu hình:

  * Grafana.
  * Loki.
  * Prometheus.
  * Tempo nếu sử dụng tracing backend.

* [ ] Tạo dashboard hoặc provisioning skeleton cho:

  * API request.
  * Error rate.
  * API latency.
  * BullMQ queue depth.
  * Failed jobs.
  * Job duration.
  * Redis.
  * PostgreSQL.
  * Worker health.

* [ ] Có global exception logging nhưng không làm lộ dữ liệu nhạy cảm.

### 16. Health check and graceful shutdown

* [ ] Tạo health endpoint.

* [ ] Phân biệt:

  * Liveness.
  * Readiness.

* [ ] Kiểm tra tối thiểu:

  * PostgreSQL.
  * Redis.
  * BullMQ.
  * S3 khi phù hợp.

* [ ] API và worker hỗ trợ graceful shutdown.

* [ ] Khi worker shutdown:

  * Không nhận job mới.
  * Chờ job đang chạy trong giới hạn cấu hình.
  * Đóng queue connection đúng cách.

* [ ] Khi API shutdown:

  * Ngừng nhận request mới.
  * Đóng database, Redis và telemetry connection đúng cách.

### 17. Frontend workspace

* [ ] Khởi tạo frontend monorepo hoặc workspace với hai ứng dụng:

```text
apps/
├── public-web/
└── admin-web/
```

* [ ] Hai ứng dụng có thể:

  * Start độc lập.
  * Build độc lập.
  * Test độc lập.
  * Deploy độc lập.

* [ ] Khởi tạo các shared packages:

```text
packages/
├── ui/
├── design-system/
├── api-client/
├── auth/
├── query/
├── forms/
├── validation/
├── editor-core/
├── analytics/
├── observability/
├── seo/
├── i18n/
├── types/
├── utilities/
├── config/
├── eslint-config/
└── typescript-config/
```

* [ ] Không để public website phụ thuộc source nội bộ của admin website.
* [ ] Không để admin website phụ thuộc source nội bộ của public website.
* [ ] Code dùng chung phải được đưa vào package có public API rõ ràng.
* [ ] Thiết lập alias và module boundary.

### 18. Public website structure

* [ ] Khởi tạo route group:

```text
app/
├── (marketing)/
├── (cards)/
├── (commerce)/
├── (account)/
└── (auth)/
```

* [ ] Chuẩn bị route skeleton cho:

  * Trang chủ.
  * Mẫu thiệp.
  * Chi tiết mẫu thiệp.
  * Tạo thiệp.
  * Xem thiệp.
  * Quà kỷ niệm.
  * Chi tiết sản phẩm.
  * Đặt làm riêng.
  * Giỏ hàng.
  * Thanh toán.
  * Tra cứu đơn.
  * Tài khoản.
  * Đăng nhập và đăng ký.
  * Nội dung và chính sách.

* [ ] Thiết lập:

  * Root layout.
  * Error page.
  * Not found page.
  * Loading state.
  * Metadata.
  * Sitemap.
  * Robots.
  * Manifest.
  * Global styles.

### 19. Admin website structure

* [ ] Khởi tạo route group cho authentication và dashboard.

* [ ] Chuẩn bị route skeleton cho:

  * Tổng quan.
  * Mẫu thiệp.
  * Danh mục thiệp.
  * Tài nguyên thiết kế.
  * Sản phẩm.
  * Danh mục quà.
  * Tùy chọn sản phẩm.
  * Kho hàng.
  * Đơn hàng.
  * Đặt làm riêng.
  * Sản xuất.
  * Khách hàng.
  * Nội dung.
  * Khuyến mãi.
  * Đánh giá.
  * Hỗ trợ.
  * Thông báo.
  * Báo cáo.
  * Nhân viên.
  * Cài đặt.

* [ ] Thiết lập dashboard layout.

* [ ] Thiết lập authorization guard ở route level.

* [ ] Chuẩn bị permission abstraction cho menu và action.

### 20. Frontend technical foundation

* [ ] Tích hợp Tailwind CSS.
* [ ] Tích hợp shadcn/ui.
* [ ] Tích hợp Radix UI.
* [ ] Tạo design token dùng chung.
* [ ] Tích hợp TanStack Query.
* [ ] Tạo query client và provider dùng lại.
* [ ] Tạo query key convention.
* [ ] Tích hợp React Hook Form.
* [ ] Tích hợp Zod.
* [ ] Tạo reusable form field và API error mapping.
* [ ] Tạo API client package từ Swagger/OpenAPI.
* [ ] Chuẩn bị request interceptor.
* [ ] Chuẩn bị single-flight refresh token flow.
* [ ] Chuẩn bị authentication state.
* [ ] Chuẩn bị SSR authenticated fetch thông qua Next.js server layer hoặc BFF.
* [ ] Không để access token trong localStorage.
* [ ] Tạo shared error boundary và notification/toast.
* [ ] Tạo cấu hình SEO dùng chung cho public website.
* [ ] Tạo observability hook hoặc adapter cho frontend.

### 21. Code quality

* [ ] Bật TypeScript strict mode.

* [ ] Bật tối thiểu:

  * `strict`.
  * `noImplicitAny`.
  * `strictNullChecks`.
  * `noUncheckedIndexedAccess`.
  * `exactOptionalPropertyTypes`.
  * `noImplicitOverride`.
  * `noFallthroughCasesInSwitch`.
  * `useUnknownInCatchVariables`.

* [ ] Thiết lập ESLint.

* [ ] Thiết lập Prettier.

* [ ] Thiết lập lint-staged.

* [ ] Thiết lập Husky.

* [ ] Thiết lập commitlint.

* [ ] Sử dụng Conventional Commits.

* [ ] Thiết lập import sorting.

* [ ] Cấm circular dependency nếu có thể.

* [ ] Thiết lập architecture test hoặc dependency rule.

* [ ] Không cho phép import xuyên module ngoài public API.

### 22. Testing foundation

* [ ] Thiết lập unit test.

* [ ] Thiết lập integration test.

* [ ] Thiết lập backend E2E test.

* [ ] Thiết lập frontend component test nếu áp dụng.

* [ ] Thiết lập Playwright cho E2E.

* [ ] Thiết lập test database hoặc container.

* [ ] Thiết lập test Redis cho BullMQ.

* [ ] Có test minh họa cho:

  * Một backend use case.
  * Một repository adapter.
  * Một API endpoint.
  * Một BullMQ publisher.
  * Một BullMQ processor.
  * Retry hoặc failed job.
  * Một frontend component.
  * Một React Hook Form schema.
  * Một public route.
  * Một admin route.

* [ ] Test không phụ thuộc trực tiếp vào hạ tầng production.

* [ ] Có fixture và factory có thể tái sử dụng.

### 23. Docker and local development

* [ ] Tạo Dockerfile cho:

  * Backend API.
  * Backend worker.
  * Backend realtime nếu chạy độc lập.
  * Backend scheduler nếu chạy độc lập.
  * Public website.
  * Admin website.

* [ ] Dockerfile sử dụng multi-stage build.

* [ ] Không chạy container production bằng root nếu không cần thiết.

* [ ] Tạo Docker Compose cho local:

  * PostgreSQL.
  * Redis.
  * S3-compatible storage hoặc AWS configuration mock phù hợp.
  * API.
  * Worker.
  * Public website.
  * Admin website.
  * Observability services khi bật profile.

* [ ] Hỗ trợ profile hoặc file compose riêng cho:

  * Infrastructure.
  * Development.
  * Observability.

* [ ] Có script chờ dependency sẵn sàng.

* [ ] Có health check cho container.

* [ ] Có volume phù hợp cho dữ liệu local.

* [ ] Không chứa secret production trong Docker image.

### 24. CI pipeline

* [ ] Tạo GitHub Actions hoặc CI tương đương cho pull request.

* [ ] Pipeline thực hiện:

  * Install dependencies.
  * Validate lockfile.
  * ESLint.
  * Prettier check.
  * TypeScript typecheck.
  * Unit test.
  * Integration test.
  * Architecture test.
  * Build.
  * Dependency scan.
  * Secret scan.
  * Container hoặc filesystem scan.

* [ ] Backend và frontend có pipeline riêng.

* [ ] Public website và admin website có thể build độc lập.

* [ ] API và worker có thể build độc lập.

* [ ] CI cache dependency đúng cách.

* [ ] CI không bỏ qua lỗi test hoặc typecheck.

* [ ] Pull request không được merge khi required checks thất bại.

### 25. Release and production pipeline

* [ ] Sử dụng branch convention:

```text
main
develop
feature/*
fix/*
release/v*
hotfix/v*
```

* [ ] Production deployment chỉ được thực hiện từ:

```text
release/vX.Y.Z
hotfix/vX.Y.Z
```

* [ ] Pipeline kiểm tra tên branch theo Semantic Versioning.

* [ ] Pipeline trích xuất version từ branch.

* [ ] Docker image được gắn tag:

  * Release version.
  * Commit SHA.

* [ ] Không chỉ sử dụng tag `latest`.

* [ ] Docker image đã kiểm thử tại staging phải được promote nguyên trạng lên production.

* [ ] Không build lại image riêng cho production.

* [ ] Production deployment sử dụng immutable image digest nếu registry hỗ trợ.

* [ ] Pipeline production có manual approval.

* [ ] Migration production chạy bằng job riêng.

* [ ] Chỉ tạo Git tag sau khi deployment production thành công.

* [ ] Sau deployment thành công:

  * Merge release branch vào `main`.
  * Merge release branch ngược về `develop`.

* [ ] Có release manifest ghi nhận:

  * Release version.
  * Repository.
  * Commit SHA.
  * Docker image.
  * Image digest.
  * Migration version.
  * Thời gian deploy.
  * Người phê duyệt.

* [ ] Có rollback workflow theo release version.

* [ ] Rollback sử dụng image digest đã tồn tại, không build image mới.

### 26. Documentation

* [ ] Tạo tài liệu:

  * System context.
  * Container diagram.
  * Backend module boundaries.
  * Frontend package boundaries.
  * Clean Architecture rules.
  * BullMQ conventions.
  * Configuration conventions.
  * Database migration guide.
  * S3 upload flow.
  * Authentication flow.
  * Realtime event convention.
  * Logging convention.
  * Testing guide.
  * Local development guide.
  * Deployment guide.
  * Release process.
  * Rollback process.

* [ ] Tạo ADR cho các quyết định chính:

  * Modular monolith.
  * Hai repository backend và frontend.
  * BullMQ là background job implementation hiện tại.
  * Không tích hợp RabbitMQ/Kafka trong giai đoạn khởi tạo.
  * Tách API và worker process.
  * Frontend gồm public và admin trong cùng workspace.
  * Production deployment theo versioned release branch.

* [ ] Tài liệu hướng dẫn bổ sung queue và job mới phải có ví dụ hoàn chỉnh.

## Acceptance criteria

1. Hai repository `backend` và `frontend` được khởi tạo và có thể cài đặt dependency thành công từ môi trường sạch.

2. Backend được tổ chức theo NestJS workspace với tối thiểu các application:

```text
api
worker
realtime
scheduler
cli
```

3. API và worker có thể build và chạy độc lập.

4. Public website và admin website có thể build và chạy độc lập.

5. Backend module tuân theo bốn layer:

```text
domain
application
infrastructure
presentation
```

6. Domain layer không import NestJS, TypeORM, Redis, BullMQ, AWS SDK, Socket.IO hoặc HTTP DTO.

7. Có architecture rule hoặc test phát hiện import sai layer hoặc import trực tiếp source nội bộ của module khác.

8. Mỗi business module có public entry point rõ ràng.

9. Không có thư mục `common` hoặc `utils` dùng làm nơi chứa không kiểm soát các thành phần không liên quan.

10. Configuration module tập trung được triển khai và validation toàn bộ environment variable khi bootstrap.

11. API, worker, scheduler và CLI sử dụng chung typed configuration thay vì tự đọc `process.env`.

12. PostgreSQL và TypeORM được cấu hình tập trung và dùng lại giữa các application process.

13. Production TypeORM configuration không bật `synchronize`.

14. Migration có thể create, generate, run và revert bằng documented command.

15. Redis được cấu hình thành platform module dùng lại.

16. BullMQ được tích hợp thành công và sử dụng Redis connection từ configuration layer.

17. Có ít nhất một queue mẫu hoạt động end-to-end:

```text
API publish job
→ Redis/BullMQ
→ worker nhận job
→ processor xử lý
→ trạng thái completed hoặc failed được ghi nhận
```

18. Business use case publish background job thông qua interface hoặc injection token, không inject BullMQ Queue trực tiếp.

19. Queue producer và processor sử dụng chung job contract có version.

20. Có cấu hình mặc định cho retry, backoff, retention và concurrency.

21. Có thể override BullMQ configuration theo từng queue hoặc từng job.

22. Có handling riêng cho retryable và non-retryable errors.

23. Có ít nhất một test cho retry hoặc failed job.

24. Có correlation ID xuyên suốt từ HTTP request đến background job log.

25. Có logging cho vòng đời job và không ghi payload nhạy cảm ngoài ý muốn.

26. Có metric hoặc cơ chế quan sát queue depth, failed jobs và job duration.

27. Có health check cho PostgreSQL, Redis và BullMQ.

28. RabbitMQ không được cài đặt hoặc bootstrap trong phạm vi Epic này.

29. Kafka không được cài đặt hoặc bootstrap trong phạm vi Epic này.

30. Việc bổ sung message broker khác trong tương lai không yêu cầu thay đổi business use case đã sử dụng queue abstraction.

31. AWS S3 adapter có thể tạo presigned upload URL và presigned download URL.

32. Business module sử dụng storage abstraction thay vì phụ thuộc trực tiếp AWS SDK.

33. Có luồng mẫu upload file trực tiếp lên S3 và publish BullMQ job để xử lý file sau khi upload hoàn tất.

34. Socket.IO được khởi tạo và realtime event được publish thông qua abstraction.

35. Có Swagger/OpenAPI cho backend API.

36. OpenAPI document có thể được export và frontend API client có thể được generate từ document đó.

37. Structured logging được áp dụng thống nhất cho API và worker.

38. API request và background job log có request ID hoặc correlation ID phù hợp.

39. Có liveness và readiness endpoint.

40. API và worker thực hiện graceful shutdown và đóng connection đúng cách.

41. Frontend workspace có `public-web`, `admin-web` và các shared package cần thiết.

42. Public và admin không import trực tiếp source nội bộ của nhau.

43. Tailwind CSS, shadcn/ui và Radix UI được cấu hình dùng lại.

44. TanStack Query provider và query key convention được thiết lập.

45. React Hook Form và Zod được tích hợp với một form mẫu có validation và hiển thị API error.

46. Access token không được lưu trong localStorage hoặc sessionStorage.

47. TypeScript strict mode được bật cho cả backend và frontend.

48. ESLint, Prettier, Husky, lint-staged và commitlint hoạt động.

49. Unit test, integration test và E2E test có thể chạy bằng documented commands.

50. Docker Compose có thể khởi động các dependency local tối thiểu:

```text
PostgreSQL
Redis
S3-compatible storage hoặc storage development tương đương
```

51. API, worker, public website và admin website có Dockerfile sử dụng multi-stage build.

52. CI chạy lint, format check, typecheck, test, build và security scan.

53. Production workflow chỉ chấp nhận source từ `release/vX.Y.Z` hoặc `hotfix/vX.Y.Z`.

54. Pipeline từ chối release branch không đúng định dạng Semantic Versioning.

55. Docker image được gắn version và commit SHA.

56. Staging và production sử dụng cùng một Docker image digest cho cùng release.

57. Production deployment có manual approval.

58. Git tag chỉ được tạo sau khi production deployment và smoke test thành công.

59. Có release manifest và rollback workflow theo release version.

60. README và tài liệu kiến trúc mô tả đầy đủ cách:

* Chạy local.
* Tạo module mới.
* Thêm configuration mới.
* Thêm queue mới.
* Thêm background job mới.
* Tạo migration.
* Chạy test.
* Build Docker.
* Tạo release.
* Rollback release.

61. Tất cả secret chỉ được cung cấp qua environment hoặc secret manager và không được commit vào repository.

62. Không có lỗi TypeScript, lint hoặc test trong pipeline sau khi hoàn thành Epic.

## Out of scope

* Triển khai đầy đủ nghiệp vụ tạo và chỉnh sửa thiệp.
* Triển khai đầy đủ nghiệp vụ quà tặng, giỏ hàng, thanh toán hoặc đơn hàng.
* Triển khai đầy đủ trình thiết kế thiệp.
* Triển khai payment gateway thực tế.
* Tích hợp đơn vị vận chuyển thực tế.
* Tích hợp RabbitMQ.
* Tích hợp Kafka.
* Triển khai transactional outbox dành cho RabbitMQ hoặc Kafka.
* Triển khai event streaming.
* Triển khai distributed transaction.
* Tách module thành microservice.
* Triển khai service mesh.
* Triển khai Kubernetes nếu chưa được lựa chọn làm hạ tầng chính thức.
* Triển khai malware scanner thực tế.
* Triển khai image processing nghiệp vụ hoàn chỉnh.
* Triển khai card rendering nghiệp vụ hoàn chỉnh.
* Triển khai email hoặc SMS provider production.
* Triển khai push notification production.
* Triển khai MFA hoàn chỉnh.
* Triển khai passkey hoặc WebAuthn.
* Triển khai phân quyền nghiệp vụ đầy đủ cho toàn bộ website admin.
* Triển khai dashboard Grafana production hoàn chỉnh; Epic chỉ yêu cầu nền tảng, provisioning và dashboard cơ bản.
* Thực hiện pentest độc lập.
* Hoàn thiện toàn bộ yêu cầu compliance và pháp lý.
* Nhập dữ liệu sản phẩm, mẫu thiệp hoặc nội dung production.
* Thiết kế giao diện hoàn chỉnh cho tất cả public và admin pages.
* Tối ưu hiệu năng theo lưu lượng production thực tế.
* Cam kết khả năng thay nóng BullMQ bằng broker khác; Epic chỉ yêu cầu business layer không phụ thuộc trực tiếp vào BullMQ và configuration có khả năng mở rộng.

## Scope amendments (approved by user, 2026-08-02)

These explicitly amend the original requirements embedded above for this task's effective
requirements — recorded here (the sole file `context.lock.json.requirements` currently locks,
`change_cycle: 0`, no separate addendum cycle open) per the user's direct instruction to update the
directive files rather than open a formal `ai/bin/request-change` cycle (which cannot run while
`state.yaml.status` is `changes_requested_by_codex`, a state that script does not accept).

1. **Branch convention (supersedes the original main/develop git-flow model embedded above, §"Sử dụng
   branch convention"):** both `apps/backend` and `apps/frontend` repositories use a **single-branch
   model** — `master` is the sole long-lived branch. Neither repository has ever had a `main` or
   `develop` branch (confirmed via `git branch -a`), so `release.yml`/`deploy-production.yml`/CI
   trigger lists and the post-tag merge step must target `master` only, not `main`/`develop`.
   `docs/adr/0007-versioned-release-branch-deployment.md` and `docs/guides/{deployment,
   release-process}.md` (both repos) have been updated to reflect this and are the authoritative
   description of the branch/merge flow going forward.
2. **AC #56/#58/#59 (deployment infrastructure) — clarified, not waived:** the actual production
   infrastructure target (Kubernetes/ECS/VM/PaaS/...) was never chosen anywhere in the original requirements above, so the steps that would apply a promoted image digest to a real running
   environment remain `TODO` placeholders in `release.yml`/`deploy-production.yml`/
   `rollback-production.yml` (both repos) — this is a pending infrastructure decision, out of this
   task's scope to make unilaterally. Everything around that gap that *can* be implemented in code
   has been (build/tag/push, digest tracking and cross-check between staging/production requests,
   mandatory smoke-test gating, release manifest, rollback reading the correct prior manifest,
   branch merge per amendment 1 above) and has been validated across 17 Codex review cycles.
   AC #57 (manual production approval) is met at the mechanism level (`environment: production` is
   correctly declared in the workflow); configuring actual required reviewers on that GitHub
   Environment is a one-time operational action outside what any workflow YAML in this repo can
   itself prove.

## Constraints

- Không quản lý worktree/branch (chưa có worktree cho task này — thao tác khởi tạo được thực hiện trực tiếp trong `apps/` theo chỉ định tường minh của người dùng, xem ghi chú ngoại lệ ở trên).
- Không commit hoặc push.
- Không đọc secret.
- Không tạo git repository mới trong `apps/backend` hoặc `apps/frontend` (chỉ tạo cấu trúc thư mục/file).
