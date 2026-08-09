# Báo cáo MEMORIES-0001 — Initialize Project Architecture and Folder Structure

## Kết quả kỹ thuật

- Trạng thái workflow: `completed`
- Implementation cycle: `1`
- Change cycle hiện hành: `0`
- Claude implementation: `implemented`
- Codex verdict: `pass`
- User acceptance: `accepted`

Người dùng đã xác nhận vòng hiện hành.

## Yêu cầu hiệu lực

- `ai/tasks/MEMORIES-0001/task.md`

## Nội dung triển khai

Round 34 (review_cycle 33 -> 34, sau khi tăng max_cycles 33->34): sửa 1 finding major của review lần 33 trong BullMqMetricsCollector — cùng lớp race lifecycle đã sửa cho OutboxRelay/FailureReconciliationService ở round 33 nhưng bị bỏ sót cho chính collector này. onModuleDestroy() trước đó chỉ clearInterval() — không dừng/chặn 1 lượt collect() đang chạy dở (đang await getJobCounts() cho queue đầu tiên). Lượt collect() đó có thể tiếp tục sang queue TIẾP THEO sau khi BullMqQueueFactory đã snapshot/đóng các queue đã cache của nó ở phase beforeApplicationShutdown (chạy SAU onModuleDestroy) — gọi getQueue() cho 1 queue chưa từng được cache tại thời điểm đó sẽ tạo ra 1 kết nối Redis MỚI mà factory không bao giờ đóng, hoặc đua lệnh với 1 queue đang bị đóng. Sửa bằng đúng pattern cooperative-cancellation + deadline đã dùng cho OutboxRelay.pollOnce/FailureReconciliationService.sweepOnce: thêm cờ shuttingDown (kiểm tra trước mỗi queue trong vòng lặp collect(), dừng ngay nếu true), thêm collectOnce() theo dõi promise đang chạy (currentCollect) để interval gọi thay vì gọi collect() trực tiếp, và onModuleDestroy() giờ async — set shuttingDown=true rồi await currentCollect (nếu có) đua với BULLMQ_SHUTDOWN_TIMEOUT_MS qua raceAgainstDeadline (dùng lại helper có sẵn). Thêm ConfigService vào constructor để đọc shutdownTimeoutMs, giống hệt OutboxRelay/FailureReconciliationService. Thêm 2 test hồi quy: (1) xác nhận collect() không gọi getQueue() cho queue thứ 2 sau khi onModuleDestroy() báo hiệu huỷ trong lúc queue đầu tiên còn đang chờ getJobCounts(); (2) xác nhận onModuleDestroy() không chờ quá deadline khi 1 lượt getJobCounts() không bao giờ resolve. Toàn bộ typecheck/lint/170 unit test (37 suite)/depcruise/10 e2e test đều pass; xác minh thêm bằng build+boot thật worker chống lại Postgres/Redis/MinIO throwaway container thật, curl /metrics thành công, kill -TERM thoát sạch ngay lập tức.

## Repository đã thay đổi

### backend

- `libs/platform/storage/src/upload-validation.ts (thêm IMAGE_UPLOAD_RULES + extensionForMimeType dùng chung giữa create và confirm)`
- `libs/modules/media/src/application/use-cases/create-media-asset.use-case.ts (object key có phần mở rộng đúng từ MIME type; validate MIME/size trước khi cấp presigned URL)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (dùng IMAGE_UPLOAD_RULES dùng chung thay vì mảng rule tự khai riêng)`
- `libs/modules/media/src/application/use-cases/get-media-asset.use-case.ts (mới — cho phép client hỏi trạng thái asset sau confirm-upload)`
- `libs/modules/media/src/application/contracts/generate-thumbnail.job.ts (jobId đổi dấu ':' sang '-' vì BullMQ từ chối custom Id chứa ':')`
- `libs/modules/media/src/presentation/http/media.controller.ts (thêm GET /media/:id; @ApiResponse cho cả 3 endpoint; round 3: thêm @ApiParam(mediaAssetId, uuid) cho confirmUpload/get)`
- `libs/modules/media/src/presentation/http/create-media-asset.dto.ts (@ApiProperty cho từng field)`
- `libs/modules/media/src/presentation/http/media-asset-response.dto.ts (mới — 3 response DTO có @ApiProperty)`
- `libs/modules/media/src/media.module.ts (đăng ký GetMediaAssetUseCase)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts (thêm type: 'varchar' tường minh cho 2 cột optional)`
- `libs/platform/database/src/typeorm-options.factory.ts (round 3: bỏ hẳn glob, dùng autoLoadEntities:true — glob round-2 không hoạt động trong image webpack-bundled thật, xác nhận bằng build+run Docker thật)`
- `libs/platform/database/src/data-source.ts (cùng sửa glob '*.orm-entity.ts' cho CLI migration — file này KHÔNG đổi ở round 3 vì DataSource CLI luôn chạy từ source qua ts-node, không bị ảnh hưởng bởi webpack bundling)`
- `libs/platform/database/test/typeorm-options.factory.spec.ts (round 3: test đổi sang assert autoLoadEntities===true và entities===undefined)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (sửa logic đếm retry: recordRetries()/isFinalAttempt() ghi nhận đúng 1 lần dù job fail-rồi-thành-công hay fail-hẳn)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (mới)`
- `libs/platform/cache/src/redis-client.shutdown.ts (mới — OnApplicationShutdown gọi redis.quit())`
- `libs/platform/cache/src/cache.module.ts (đăng ký RedisClientShutdown)`
- `libs/platform/cache/test/redis-client.shutdown.spec.ts (mới)`
- `libs/platform/realtime/src/redis-emitter-client.shutdown.ts (mới, tương tự cho REALTIME_REDIS_CLIENT)`
- `libs/platform/realtime/src/realtime.module.ts (đăng ký RealtimeRedisClientShutdown)`
- `libs/platform/realtime/src/redis-io.adapter.ts (override close(server) đóng luôn pubClient/subClient)`
- `libs/platform/realtime/test/redis-emitter-client.shutdown.spec.ts (mới)`
- `apps/worker/src/app.module.ts (thêm SecurityModule.register() — thiếu nên worker crash khi boot thật; đăng ký WorkerMetricsServer)`
- `apps/worker/src/worker-metrics.server.ts (mới — http.createServer riêng cho /metrics, không dùng chung Nest app để tránh lộ route business)`
- `apps/worker/test/worker-metrics.server.spec.ts (mới)`
- `apps/scheduler/src/app.module.ts (thêm SecurityModule.register() — cùng lỗi thiếu như worker)`
- `apps/api/src/configure-app.ts (mới — tách helmet/cors/prefix/ValidationPipe/GlobalExceptionFilter dùng chung giữa main.ts và e2e test; round 3: tách riêng applyGlobalPrefix() để export-openapi.ts dùng lại)`
- `apps/api/src/main.ts (dùng configureApp thay vì lặp lại inline)`
- `apps/api/src/export-openapi.ts (bỏ process.exit(0) — app.close() giờ tự kết thúc sạch sau khi Redis/RedisIoAdapter có shutdown hook; round 3: gọi applyGlobalPrefix() trước buildOpenApiDocument để schema xuất ra ghi đúng '/api/v1/media' thay vì '/media')`
- `apps/api/test/health.e2e-spec.ts (áp dụng configureApp để giống production)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (mới — E2E thật: 2 Nest app context (api+worker) cùng Postgres/Redis/MinIO thật, đi hết luồng create->upload->confirm->worker->GET ready)`
- `docker/docker-compose.yml (worker: thêm port 9464 + healthcheck /metrics)`
- `.github/workflows/release.yml (staging smoke test bắt buộc — exit 1 nếu thiếu URL thay vì exit 0; thêm migrationVersion vào staging-digests.json)`
- `.github/workflows/deploy-production.yml (production smoke test bắt buộc; thêm bước xác minh version+commitSha trong staging-digests.json khớp input/github.sha; manifest field 'images' -> 'build')`
- `.github/workflows/rollback-production.yml (smoke test bắt buộc; đọc .build.digests/.build.migrationVersion thay vì .images)`
- `ai/repos/backend/commands.yaml (test-e2e: required false -> true) — file này thuộc ai/ không phải backend repo, ghi chú cho đầy đủ ngữ cảnh`
- `libs/platform/queue/src/contracts/background-job-handler.ts (round 4: thêm JobFailureContext + handleFinalFailure? optional trên BackgroundJobHandler)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 4: isFinalAttempt nhận thêm error, coi UnrecoverableError là final dù attemptsMade < max; thêm notifyFinalFailure() gọi handler.handleFinalFailure với try/catch riêng)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 4: thêm test cho UnrecoverableError + notifyFinalFailure)`
- `libs/modules/media/src/presentation/jobs/generate-thumbnail.handler.ts (round 4: implement handleFinalFailure — markFailed với message gốc khi non-retryable, chuỗi chung chung khi retry hết lượt)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (round 4: thêm markFailed(mediaAssetId, reason))`
- `libs/modules/media/src/domain/media-asset/media-asset.ts (round 4: markFailed() thêm guard không ghi đè khi đã 'ready')`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 4: đối chiếu metadata.contentType/contentLength với asset.mimeType/sizeBytes, lỗi media_asset_metadata_mismatch nếu lệch)`
- `libs/modules/media/test/{media-asset.spec.ts,generate-thumbnail.handler.spec.ts,confirm-media-upload.use-case.spec.ts} (round 4: thêm test cho các case mới)`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts (mới — test markFailed)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (round 4: sizeBytes khai báo giờ khớp đúng Buffer.byteLength thật, tránh tự vi phạm check đối chiếu metadata mới thêm)`
- `docs/guides/release-process.md (round 4: mô tả đúng luồng deploy-production.yml hiện hành, không còn nhắc input digest đã bị xóa)`
- `libs/modules/media/src/domain/media-asset/media-asset.repository.ts (round 5: thêm transitionStatus(id, expectedStatus, next) — CAS nguyên tử, mở rộng interface từ Repository<MediaAsset> thuần)`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts (round 5: implement transitionStatus qua UPDATE ... WHERE id=? AND status=? của TypeORM)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (round 5: execute()/markFailed() dùng transitionStatus thay vì findById+mutate+save)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 5: từ chối confirm khi asset không còn 'pending' — lỗi media_asset_already_confirmed)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 5: notifyFinalFailure() theo dõi bằng Set pendingFinalFailures + retry tối đa 3 lần backoff tuyến tính; onApplicationShutdown() await hết pendingFinalFailures trước khi đóng worker)`
- `libs/modules/media/test/{generate-thumbnail.use-case.spec.ts,confirm-media-upload.use-case.spec.ts} (round 5: viết lại/mở rộng test cho CAS + reject re-confirm)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 5: thêm test retry-rồi-thành-công, retry-hết-lượt, và onApplicationShutdown chờ pending failures; round 6: sửa test có lỗi vòng lặp vô hạn do tự bookkeeping Set không dọn dẹp đúng)`
- `apps/cli/src/app.module.ts (round 6: thêm SecurityModule.register() — cùng lỗi đã sửa cho worker/scheduler nhưng bỏ sót CLI)`
- `apps/cli/src/commands/reprocess-job.command.ts (round 6: viết lại — tự load bucket/objectKey từ MediaAsset, jobId attempt-scoped không chứa ':')`
- `apps/cli/test/reprocess-job.command.spec.ts (mới)`
- `libs/modules/media/src/media.module.ts (round 6: export MEDIA_ASSET_REPOSITORY — trước đó exports:[] khiến provider không inject được từ ngoài module dù cùng DI container)`
- `libs/modules/media/src/public-api.ts (round 6: export MediaAssetRepository (type)/MEDIA_ASSET_REPOSITORY/GENERATE_THUMBNAIL_JOB_NAME — ngoại lệ hẹp, có chủ đích cho ops tooling)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 6: đổi thứ tự publish-trước-rồi-save, không còn save-trước-rồi-publish)`
- `libs/modules/media/test/confirm-media-upload.use-case.spec.ts (round 6: thêm test publish thất bại thì asset vẫn pending)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 6: onApplicationShutdown đóng worker trước, drain pendingFinalFailures theo vòng lặp sau)`
- `libs/platform/database/src/typeorm-unit-of-work.ts (round 7: TypeOrmQueryRunnerContext đổi sang AsyncLocalStorage — sửa bug concurrency thật của mã scaffold cũ, chưa từng được dùng thật trước đây)`
- `libs/platform/database/test/typeorm-unit-of-work.spec.ts (mới — test cách ly 2 transaction đồng thời + commit/rollback)`
- `libs/platform/queue/src/outbox/{outbox.contract.ts,outbox-message.orm-entity.ts,typeorm-outbox.repository.ts,outbox-relay.service.ts} (mới — transactional outbox: port, entity, TypeORM impl transaction-aware, relay poller 2s chỉ chạy ở apps/worker)`
- `libs/platform/queue/src/bullmq/bullmq.module.ts (round 7: đăng ký TypeOrmModule.forFeature([OutboxMessageOrmEntity]), OUTBOX_REPOSITORY, OutboxRelay chỉ khi role='worker')`
- `libs/platform/queue/src/public-api.ts (round 7: export outbox.contract)`
- `libs/platform/queue/test/outbox-relay.service.spec.ts (mới)`
- `libs/platform/database/src/migrations/1722520000000-CreateOutboxMessages.ts (mới, đã chạy thật thành công trên Postgres)`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts (round 7: save/transitionStatus/findById/delete giờ join ambient transaction qua TypeOrmQueryRunnerContext khi có)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 7: viết lại — markProcessing + outbox.enqueue trong 1 UnitOfWork.withTransaction, không còn gọi BackgroundJobPublisher trực tiếp)`
- `libs/modules/media/src/application/use-cases/reprocess-media-asset.use-case.ts (mới — CAS failed->processing + outbox.enqueue trong 1 transaction, jobId attempt-scoped)`
- `libs/modules/media/src/media.module.ts (round 7: đăng ký ReprocessMediaAssetUseCase, export thay cho MEDIA_ASSET_REPOSITORY thô ở round 6)`
- `libs/modules/media/src/public-api.ts (round 7: export ReprocessMediaAssetUseCase thay vì MediaAssetRepository/MEDIA_ASSET_REPOSITORY/GENERATE_THUMBNAIL_JOB_NAME)`
- `apps/cli/src/commands/reprocess-job.command.ts (round 7: viết lại lần 2 — chỉ gọi ReprocessMediaAssetUseCase, không tự lắp payload/repository nữa)`
- `apps/cli/test/reprocess-job.command.spec.ts (round 7: viết lại theo constructor mới)`
- `libs/modules/media/test/confirm-media-upload.use-case.spec.ts (round 7: viết lại theo outbox/unitOfWork mock)`
- `libs/modules/media/test/reprocess-media-asset.use-case.spec.ts (mới)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (round 7: thêm test thật — xoá object khỏi MinIO ép asset 'failed', khôi phục object, gọi ReprocessMediaAssetUseCase thật, xác nhận quay lại 'ready')`
- `libs/platform/queue/src/outbox/outbox.contract.ts (round 8: EnqueueOutboxMessageInput/OutboxMessage thêm correlationId?/actorId?)`
- `libs/platform/queue/src/outbox/outbox-message.orm-entity.ts (round 8: thêm cột correlation_id/actor_id)`
- `libs/platform/database/src/migrations/1722520000000-CreateOutboxMessages.ts (round 8: ALTER thêm 2 cột mới — bảng chưa từng release nên sửa migration tại chỗ thay vì thêm migration mới)`
- `libs/platform/queue/src/outbox/typeorm-outbox.repository.ts (round 8: enqueue/listUnpublished đọc-ghi correlationId/actorId)`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts (round 8: viết lại — truyền correlationId/actorId vào jobPublisher.publish; bọc try/catch toàn bộ pollOnce (kể cả recordFailure tự lỗi); currentPoll được await đúng lúc onApplicationShutdown)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 8: capture CorrelationContext.correlationId() trước khi enqueue)`
- `libs/modules/media/src/application/use-cases/reprocess-media-asset.use-case.ts (round 8: cùng capture correlationId + actorId=asset.ownerId)`
- `libs/platform/queue/test/outbox-relay.service.spec.ts (round 8: thêm test cho correlationId passthrough, listUnpublished/recordFailure reject, shutdown await currentPoll)`
- `libs/modules/media/test/{confirm-media-upload.use-case.spec.ts,reprocess-media-asset.use-case.spec.ts} (round 8: cập nhật assertion enqueue có actorId)`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (mới, round 9 — quét Queue.getFailed() mỗi 60s, chỉ trong apps/worker, gọi lại handleFinalFailure cho job fail trong 10 phút gần nhất)`
- `libs/platform/queue/src/bullmq/bullmq.module.ts (round 9: đăng ký FailureReconciliationService khi role='worker')`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts (mới, round 9)`
- `libs/modules/media/src/domain/media-asset/media-asset.ts (them currentJobId prop + getter; markProcessing(jobId?) ghi nhan attempt so huu processing)`
- `libs/modules/media/src/domain/media-asset/media-asset.ts (thêm currentJobId prop + getter; markProcessing(jobId?) ghi nhận attempt sở hữu processing)`
- `libs/modules/media/src/domain/media-asset/media-asset.repository.ts (transitionStatus nhận MediaAssetStatusExpectation{status,jobId} thay vì status đơn; MediaAssetStatusTransition thêm jobId để set current_job_id)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts (thêm cột current_job_id varchar nullable)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.mapper.ts (map currentJobId 2 chiều domain<->ORM)`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts (transitionStatus: WHERE thêm current_job_id khi expected.jobId có; SET current_job_id khi next.jobId có)`
- `libs/platform/database/src/migrations/1722510000000-CreateMediaAssets.ts (sửa tại chỗ — thêm cột current_job_id character varying; bảng này chưa từng được release ngoài test DB của chính task này)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (thêm GenerateThumbnailInput{payload,jobId} để giữ UseCase<TRequest,TResponse> 1-tham-số; execute/markFailed giờ require jobId và truyền vào transitionStatus.expected)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (hoist jobId; asset.markProcessing(jobId) thay vì markProcessing() không tham số)`
- `libs/modules/media/src/application/use-cases/reprocess-media-asset.use-case.ts (transitionStatus next thêm jobId — attempt-scoped jobId đã tạo sẵn được lưu vào current_job_id ngay lúc CAS Failed->Processing)`
- `libs/modules/media/src/presentation/jobs/generate-thumbnail.handler.ts (truyền envelope.jobId vào execute({payload,jobId}) và markFailed(...,envelope.jobId))`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (viết lại: bỏ RECONCILIATION_WINDOW_MS và giới hạn 500-job-đầu; phân trang toàn bộ failed set qua nhiều getFailed() call, remove() job sau khi reconcile thành công làm checkpoint bền vững; sweepOnce() tự quản lý currentSweep, không còn flag 'sweeping' riêng)`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts (pollOnce() tự quản lý currentPoll thay vì setInterval callback gán vô điều kiện; bỏ flag 'polling' riêng)`
- `libs/platform/queue/src/public-api.ts (export FailureReconciliationService để e2e test có thể gọi sweepOnce() trực tiếp qua @memories/platform/queue)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (thêm e2e test thật: failed -> reprocess -> FailureReconciliationService.sweepOnce() cho job cũ -> vẫn 'processing' đúng -> cuối cùng 'ready')`
- `libs/modules/media/test/media-asset.spec.ts (test markProcessing(jobId) ghi currentJobId; không đụng khi đã Ready)`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts (cập nhật toàn bộ assertion transitionStatus sang {status,jobId}; thêm 2 test attempt-scoped: stale jobId không thể ghi đè attempt mới cho cả execute và markFailed)`
- `libs/modules/media/test/generate-thumbnail.handler.spec.ts (cập nhật assertion markFailed/execute thêm jobId; thêm test 'passes envelope jobId through')`
- `libs/modules/media/test/reprocess-media-asset.use-case.spec.ts (cập nhật assertion transitionStatus sang {status:Failed} / {status:Processing,jobId:result.jobId})`
- `libs/modules/media/test/confirm-media-upload.use-case.spec.ts (thêm assertion save() nhận currentJobId đúng bằng generateThumbnailJobId)`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts (viết lại toàn bộ cho hành vi phân trang không giới hạn + remove() checkpoint; thêm 2 test hồi quy cho shutdown race)`
- `libs/platform/queue/test/outbox-relay.service.spec.ts (thêm 1 test hồi quy cho shutdown race — currentPoll không bị ghi đè bởi tick sau)`
- `libs/platform/queue/src/registry/queue.registry.ts (media queue: thêm defaultJobOptions.removeOnFail:false — tắt BullMQ tự trim theo số lượng, chỉ dọn dẹp qua FailureReconciliationService.job.remove() sau khi reconcile thành công)`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (cập nhật doc comment: làm rõ tại sao 1 ledger Postgres mới KHÔNG bền vững hơn — job cần reconcile chỉ tồn tại vì Postgres đang down đúng lúc đó, ghi vào 1 bảng Postgres khác cũng thất bại tương tự; điều thật sự bền vững là Redis, với điều kiện removeOnFail không tự trim)`
- `libs/platform/queue/test/queue.registry.spec.ts (test: media queue có defaultJobOptions.removeOnFail === false)`
- `libs/platform/queue/test/bullmq.publisher.spec.ts (test: override removeOnFail:false ở queue thắng platform default, xác nhận dùng `??` chứ không phải `||` nên `false` không bị coi là 'absent')`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (thay skip-Set bằng cursor chỉ tiến qua job được giữ lại (kept) mỗi trang; reconcileJob không còn remove() job của handler không có handleFinalFailure — để nguyên cho removeOnFail policy của chính queue quản lý)`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts (thêm test hồi quy: 500 poison job + 1 job hợp lệ ở vị trí 500 vẫn được xét; xác nhận job không có handleFinalFailure hook không bị remove(); cập nhật test 'skips handlers with no hook' thành 'leaves untouched, not removed')`
- `apps/backend/.github/workflows/ci.yml (thêm 'master' vào pull_request.branches và push.branches — repository thực tế chỉ có nhánh master, CI trước đó chưa từng chạy trên luồng phát triển hiện hành)`
- `libs/platform/queue/src/outbox/outbox.contract.ts (listUnpublished thêm tham số offset tùy chọn, dùng để phân trang qua các message còn chưa publish)`
- `libs/platform/queue/src/outbox/typeorm-outbox.repository.ts (listUnpublished truyền offset vào TypeORM's skip)`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts (performPoll() viết lại: phân trang bằng cursor chỉ tiến qua message còn CHƯA publish (kept) mỗi batch, giống pattern FailureReconciliationService.reconcileQueue — sửa đúng bug 1 batch poison chặn vĩnh viễn các message mới hơn)`
- `libs/platform/queue/test/outbox-relay.service.spec.ts (thêm test hồi quy: 20 poison message + 1 message hợp lệ ở vị trí 20 vẫn được publish, xác nhận listUnpublished được gọi với offset đúng)`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (dùng queue.getJobs(['failed'],start,end,true) — oldest-first — thay vì queue.getFailed() (newest-first), đóng nguy cơ starvation khi có failure mới liên tục chèn vào trong lúc sweep đang chạy)`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts (cập nhật toàn bộ mock/assertion từ queue.getFailed(start,end) sang queue.getJobs(['failed'],start,end,true))`
- `apps/scheduler/src/scheduled-tasks.service.ts (XÓA — jobId chứa ':' bị BullMQ từ chối, job name không có handler nào đăng ký, không có business module 'report' thật nào backing nó; chưa bao giờ chạy thành công qua 14 round)`
- `apps/scheduler/src/app.module.ts (bỏ đăng ký ScheduledTasksService đã xóa; giữ ScheduleModule.forRoot() sẵn sàng cho recurring job thật trong tương lai; thêm doc comment giải thích)`
- `apps/backend/.github/workflows/deploy-production.yml (gộp 2 bước 'merge vào main' + 'merge ngược vào develop' thành 1 bước duy nhất 'merge vào master' — repository chỉ có 1 nhánh)`
- `apps/backend/docs/guides/deployment.md (mô tả deploy-production.yml khớp đúng single-branch model: merge vào master, không còn main/develop)`
- `apps/backend/docs/guides/release-process.md (bước 1 và bước 6: cắt release/hotfix từ master, merge vào master — không còn nhắc main/develop như 2 nhánh riêng)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (Pending->Processing giờ dùng transitionStatus CAS bên trong transaction thay vì markProcessing()+save() không điều kiện; CAS thất bại ném media_asset_already_confirmed, không enqueue)`
- `libs/modules/media/test/confirm-media-upload.use-case.spec.ts (cập nhật assertion sang transitionStatus; thêm test hồi quy race condition: CAS trả false -> ném lỗi, không enqueue)`
- `libs/modules/media/src/domain/media-asset/media-asset.repository.ts (MediaAssetStatusTransition.failureReason: string|null|undefined — null xóa tường minh)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts (failureReason đổi type string|null|undefined để TypeORM chấp nhận update SET NULL)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.mapper.ts (toDomain chuẩn hóa raw.failureReason null->undefined)`
- `libs/modules/media/src/application/use-cases/reprocess-media-asset.use-case.ts (CAS Failed->Processing giờ truyền failureReason:null để xóa lý do thất bại cũ)`
- `libs/modules/media/test/reprocess-media-asset.use-case.spec.ts (cập nhật assertion transitionStatus thêm failureReason:null)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (thêm assertion: settled.failureReason là undefined sau khi reprocess thành công tới ready)`
- `docs/adr/0007-versioned-release-branch-deployment.md (Decision section: main/develop -> master, ghi rõ single-branch model)`
- `apps/backend/.github/workflows/ci.yml (trigger: [main,develop,master]/[develop,master] -> chỉ [master])`
- `libs/platform/configuration/src/config/bullmq.config.ts (thêm shutdownTimeoutMs, mặc định 10s qua BULLMQ_SHUTDOWN_TIMEOUT_MS)`
- `libs/platform/configuration/src/schemas/env.schema.ts (thêm validation cho BULLMQ_SHUTDOWN_TIMEOUT_MS)`
- `.env.example (thêm BULLMQ_SHUTDOWN_TIMEOUT_MS=10000)`
- `libs/platform/queue/src/bullmq/shutdown-deadline.ts (mới — helper raceAgainstDeadline dùng chung cho cả 3 service)`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (onApplicationShutdown giờ bound bởi shutdownTimeoutMs qua raceAgainstDeadline)`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts (onApplicationShutdown giờ bound bởi shutdownTimeoutMs qua raceAgainstDeadline)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (onApplicationShutdown giờ bound bởi shutdownTimeoutMs qua raceAgainstDeadline; fallback worker.close(true) nếu graceful close không kịp; pendingFinalFailures drain loop cũng bound theo cùng deadline)`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts, libs/platform/queue/test/outbox-relay.service.spec.ts, libs/platform/queue/test/bullmq.worker.retries.spec.ts (cập nhật constructor injection configService; thêm test hồi quy: promise không bao giờ resolve vẫn shutdown đúng deadline)`
- `apps/backend/.github/workflows/deploy-production.yml (sửa git fetch/checkout master: dùng refs/remotes/origin/master + checkout -B thay vì fetch/checkout ngầm định)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (tắt hẳn OutboxRelay's timer tự động trong beforeAll; publish CHỈ qua pollOnce() tường minh — loại bỏ hoàn toàn race điều kiện với timer tự nhiên, không chỉ thu hẹp)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (onApplicationShutdown viết lại: worker.pause() trước, race deadline; close(pauseTimedOut) đúng 1 lần duy nhất với budget mới nếu pause() đã hết deadline gốc; pendingFinalFailures drain loop cũng nhận deadline mới tương tự khi cần)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (viết lại test force-close: mock mô phỏng đúng cơ chế cache của BullMQ thật — throw nếu close() gọi quá 1 lần — xác nhận pause() được gọi trước và close(true) chỉ gọi đúng 1 lần)`
- `apps/backend/.github/workflows/deploy-production.yml (actions/checkout thêm fetch-depth: 0 để có đủ merge-base cho git merge; thêm permissions: contents: write ở cấp job)`
- `apps/backend/.github/workflows/deploy-production.yml (permissions thêm actions: read — bị mất mặc định khi khai báo permissions tường minh ở round 20, cần cho gh run list/gh run download)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (onApplicationShutdown viết lại: dùng ĐÚNG 1 deadline tổng duy nhất cho pause+close+drain, không cấp lại cửa sổ shutdownTimeoutMs đầy đủ mới ở mỗi bước — tránh tổng thời gian thành bội số của timeout cấu hình)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (thêm test hồi quy: pause+close+pending write đều treo cùng lúc, xác nhận tổng thời gian sát 1 lần shutdownTimeoutMs, không phải bội số)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (onApplicationShutdown dùng Promise.allSettled thay vì Promise.all cho cả pause() và close() — 1 rejection không còn làm raceAgainstDeadline reject theo và thoát sớm khỏi toàn bộ hàm)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (thêm test hồi quy: pause() reject thật, xác nhận close(true) vẫn được gọi và pendingFinalFailures vẫn drain, shutdown vẫn resolve)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (thêm worker.on('error',...) cho mỗi worker; thay worker.pause() mặc định bằng pause(true) + tự theo dõi activeJobCount (tăng ở 'active', giảm ở 'completed'/'failed') để quyết định force-close, không còn phụ thuộc BullMQ's whenCurrentJobsFinished/reconnect logic; sleep() helper thêm .unref() cho timer polling)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (viết lại 3 test shutdown khớp thiết kế pause(true)+activeJobCount mới thay vì race trực tiếp promise của pause())`
- `libs/platform/queue/src/public-api.ts (export thêm BullMqWorkerRunner để e2e test truy cập worker thật)`
- `libs/platform/realtime/src/redis-io.adapter.ts (close() dùng Promise.allSettled thay vì Promise.all, log riêng lỗi từng client, luôn gọi super.close(server) bất kể kết quả quit())`
- `libs/platform/realtime/test/redis-io.adapter.close.spec.ts (mới — test hồi quy: 1 client quit() reject vẫn đóng Socket.IO server và xác nhận client còn lại)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (thêm test: emit 'error' thật trên BullMQ Worker thật của suite hiện có không crash process — tái dùng workerModuleRef sẵn có thay vì tạo app riêng để tránh leak handle)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 24: onApplicationShutdown bắt kết quả Promise.allSettled(pause(true)) — bất kỳ rejection nào cũng force-close; activeJobCount tách thành processWithActiveJobTracking() bao quanh processor callback thay vì dựa vào listener 'completed'/'failed', tránh kẹt vĩnh viễn khi job stalled/mất lock)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 24: sửa test pause-rejection sai trước đó (đòi close(false), giờ đúng close(true)); thêm test không force-close khi mọi thứ ổn; thêm test processWithActiveJobTracking decrement dù handler reject không qua event BullMQ nào)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 25: tách registerWorkerListeners() khỏi onModuleInit để test được trực tiếp; activeJobCount++ chuyển sang listener 'active' (fire tại thời điểm fetch/commit job, đóng khoảng hở quiescence với pause(true)); notifyFinalFailure() bọc handlerRegistry.resolve() trong try/catch riêng — không bao giờ trả về promise reject; drain loop pendingFinalFailures đổi Promise.all sang Promise.allSettled)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 25: sửa test activeJobCount/processWithActiveJobTracking khớp thiết kế tăng ở 'active'/giảm ở finally; thêm test registerWorkerListeners tăng đúng lúc 'active' fire qua EventEmitter giả lập; thêm test notifyFinalFailure resolve (không unhandled rejection) khi job không có handler đăng ký)`
- `.github/workflows/release.yml (round 26: thêm concurrency group theo branch để tránh 2 run chồng lấn ghi đè tag mutable; đổi cách lấy digest sang --metadata-file của chính lần build/push thay vì imagetools inspect lại tag sau khi push)`
- `libs/platform/configuration/src/config/redis.config.ts (round 26: thêm shutdownTimeoutMs, đọc từ REDIS_SHUTDOWN_TIMEOUT_MS, mặc định 5000ms)`
- `libs/platform/configuration/src/schemas/env.schema.ts (round 26: thêm REDIS_SHUTDOWN_TIMEOUT_MS)`
- `.env.example (round 26: thêm REDIS_SHUTDOWN_TIMEOUT_MS=5000)`
- `libs/platform/cache/src/redis-client.shutdown.ts (round 26: race quit() với shutdownTimeoutMs, fallback sang disconnect() nếu không settle kịp)`
- `libs/platform/cache/test/redis-client.shutdown.spec.ts (round 26: thêm test disconnect() fallback khi quit() treo)`
- `libs/platform/realtime/src/redis-emitter-client.shutdown.ts (round 26: cùng pattern race quit()/fallback disconnect() như cache module)`
- `libs/platform/realtime/test/redis-emitter-client.shutdown.spec.ts (round 26: thêm test disconnect() fallback khi quit() treo)`
- `libs/platform/realtime/src/redis-io.adapter.ts (round 26: close() tách quitWithDeadline() riêng cho từng client pub/sub, race deadline + fallback disconnect(), super.close() luôn được gọi sau)`
- `libs/platform/realtime/test/redis-io.adapter.close.spec.ts (round 26: thêm test disconnect() fallback khi 1 quit() treo, xác nhận Socket.IO teardown vẫn chạy)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 26: activeJobCount đổi thành activeJobIds (Set<string>), listener 'completed'/'failed' giờ cũng xóa id (idempotent) — phủ nhánh BullMQ bỏ qua processor callback hoàn toàn qua getUnrecoverableErrorMessage)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 26: cập nhật mọi test khớp activeJobIds; thêm test xác nhận 'failed' listener xóa id khi processor callback không bao giờ được gọi — mô phỏng deferred-failure/maxStartedAttempts)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 27: xóa hẳn processWithActiveJobTracking — Worker constructor gọi thẳng this.process(job); activeJobIds đổi thành activeJobKeys namespace theo queueName; chỉ xóa key khi 'completed'/'failed' THẬT SỰ fire, không còn xóa khi processor callback settle)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 27: viết lại toàn bộ test activeJobKeys — key namespace theo queue, chỉ xóa qua completed/failed, thêm test 2 queue cùng job.id không gộp nhầm, thêm test job key không bị xóa khi chỉ processor callback settle)`
- `libs/platform/configuration/src/config/observability.config.ts (round 27: thêm metricsShutdownTimeoutMs, đọc từ METRICS_SHUTDOWN_TIMEOUT_MS, mặc định 5000ms)`
- `libs/platform/configuration/src/schemas/env.schema.ts (round 27: thêm METRICS_SHUTDOWN_TIMEOUT_MS)`
- `.env.example (round 27: thêm METRICS_SHUTDOWN_TIMEOUT_MS=5000)`
- `apps/worker/src/worker-metrics.server.ts (round 27: onApplicationShutdown race server.close() với metricsShutdownTimeoutMs, fallback server.closeAllConnections() khi hết hạn)`
- `apps/worker/test/worker-metrics.server.spec.ts (round 27: thêm test giữ 1 HTTP connection active khi shutdown, xác nhận closeAllConnections() force-đóng trong deadline)`
- `.github/workflows/deploy-production.yml (round 27: thêm concurrency group production-deploy-rollback, cancel-in-progress: false)`
- `.github/workflows/rollback-production.yml (round 27: cùng concurrency group với deploy-production.yml để tuần tự hóa mọi thay đổi production)`
- `libs/platform/queue/src/bullmq/bullmq.worker.ts (round 28: THIẾT KẾ LẠI TRIỆT ĐỂ — xóa hẳn activeJobKeys/activeJobKey()/processWithActiveJobTracking/waitForNoActiveJobs; thêm whenWorkerQuiescent() gọi worker.whenCurrentJobsFinished(false) — barrier THẬT của chính BullMQ, thay cho mọi cơ chế tự theo dõi qua event trước đây)`
- `libs/platform/queue/test/bullmq.worker.retries.spec.ts (round 28: viết lại toàn bộ describe onApplicationShutdown — mock whenCurrentJobsFinished thay vì activeJobKeys; xóa các test round 24-26 không còn áp dụng)`
- `.github/workflows/deploy-production.yml (round 28: SỬA LỖ HỔNG SHELL INJECTION — toàn bộ inputs.version/inputs.approved_by chuyển sang job-level env: RELEASE_VERSION/APPROVED_BY, mọi script chỉ dùng biến shell đã quote; thêm validate SemVer bằng regex là bước đầu tiên; github.ref_name đổi sang $GITHUB_REF_NAME)`
- `.github/workflows/rollback-production.yml (round 28: cùng fix shell injection — ROLLBACK_VERSION/APPROVED_BY qua job-level env:, validate SemVer đầu tiên)`
- `.github/test/workflow-security.spec.ts (mới — round 28: test hồi quy quét 2 file deploy-production.yml/rollback-production.yml, xác nhận mọi ${{ inputs.* }} chỉ xuất hiện dưới dạng khai báo env: sạch, không bao giờ trong thân run: script)`
- `.github/test/tsconfig.json (mới — round 28: tsconfig riêng cho .github/test/, vì TypeScript's default include bỏ qua thư mục bắt đầu bằng dấu chấm)`
- `.eslintrc.cjs (round 28: parserOptions.project thành mảng [tsconfig.json, '.github/test/tsconfig.json'] để lint được file test mới)`
- `package.json (round 28: lint/lint:fix/format/format:check thêm glob riêng ".github/**/*.ts"; typecheck chạy thêm tsc -p .github/test/tsconfig.json)`
- `libs/platform/database/src/migrations/1722530000000-AddConfirmedEtagToMediaAssets.ts (mới — round 29: thêm cột confirmed_etag nullable vào media_assets)`
- `libs/modules/media/src/domain/media-asset/media-asset.ts (round 29: thêm confirmedEtag?: string vào MediaAssetProps + getter — ETag của object tại thời điểm confirm-upload validate thành công)`
- `libs/modules/media/src/domain/media-asset/media-asset.repository.ts (round 29: thêm confirmedEtag?: string vào MediaAssetStatusTransition)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts (round 29: thêm cột confirmed_etag)`
- `libs/modules/media/src/infrastructure/persistence/media-asset.mapper.ts (round 29: map confirmedEtag cả 2 chiều)`
- `libs/modules/media/src/infrastructure/persistence/typeorm-media-asset.repository.ts (round 29: transitionStatus áp dụng next.confirmedEtag khi được truyền)`
- `libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts (round 29: ghi confirmedEtag: metadata.etag vào CAS transition Pending->Processing)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (round 29: SỬA LỖ HỔNG TOCTOU — so sánh metadata.etag hiện tại với asset.confirmedEtag đã lưu, fail closed nếu không khớp hoặc thiếu, trước khi xử lý/chuyển ready)`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts (round 29: cập nhật fixture có confirmedEtag khớp; thêm 2 test TOCTOU — etag không khớp bị từ chối, thiếu confirmedEtag cũng bị từ chối)`
- `libs/modules/media/test/confirm-media-upload.use-case.spec.ts (round 29: thêm test xác nhận confirmedEtag được ghi đúng từ metadata.etag observed)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (round 29: thêm e2e test THẬT tái tạo chính xác kịch bản TOCTOU — ghi đè object qua presigned URL mới sau confirm, xác nhận job fail đúng message và asset không bao giờ ready)`
- `libs/platform/cache/src/redis-client.shutdown.ts (round 29: sửa bug quit()-reject bị coi như thành công — phân biệt closed/rejected/timeout, disconnect() fallback cho cả rejected và timeout)`
- `libs/platform/cache/test/redis-client.shutdown.spec.ts (round 29: thêm assertion disconnect() được gọi khi quit() reject)`
- `libs/platform/realtime/src/redis-emitter-client.shutdown.ts (round 29: cùng fix quit()-reject như cache module)`
- `libs/platform/realtime/test/redis-emitter-client.shutdown.spec.ts (round 29: cùng assertion disconnect() khi reject)`
- `libs/platform/realtime/src/redis-io.adapter.ts (round 29: quitWithDeadline() cùng fix quit()-reject)`
- `libs/platform/realtime/test/redis-io.adapter.close.spec.ts (round 29: cùng assertion disconnect() khi 1 client's quit() reject)`
- `apps/worker/src/worker-metrics.server.ts (round 29: onModuleInit return sớm nếu !metricsEnabled, không tạo/bind HTTP listener)`
- `apps/worker/test/worker-metrics.server.spec.ts (round 29: thêm test METRICS_ENABLED=false không bind listener)`
- `libs/platform/security/src/security.module.ts (round 30: thêm { provide: APP_GUARD, useClass: ThrottlerGuard } — kích hoạt rate limiting đã cấu hình từ trước nhưng chưa bao giờ có tác dụng)`
- `apps/api/test/rate-limit.e2e-spec.ts (mới — round 30: e2e test thật override RATE_LIMIT_MAX_REQUESTS=3, xác nhận request thứ 4 trả 429)`
- `libs/platform/storage/src/storage.contract.ts (round 30: CreatePresignedUploadUrlInput.contentLength (bắt buộc); thêm ConditionalGetOutcome type và StoragePort.getObjectIfMatch())`
- `libs/platform/storage/src/s3-storage.adapter.ts (round 30: PutObjectCommand ký kèm ContentLength; thêm getObjectIfMatch() dùng GetObjectCommand+IfMatch, phân biệt đúng NoSuchKey (404)/PreconditionFailed (412) qua $metadata.httpStatusCode thay vì error.name/instanceof — NotFound export chỉ áp dụng cho HeadObjectCommand, không áp dụng cho GetObjectCommand)`
- `libs/modules/media/src/application/use-cases/create-media-asset.use-case.ts (round 30: truyền contentLength: input.sizeBytes vào createPresignedUploadUrl)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (round 30: thay headObject()+so etag thủ công bằng 1 lệnh getObjectIfMatch() duy nhất, atomic hơn, ngay trước ready transition)`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts (round 30: viết lại mock storage dùng getObjectIfMatch thay vì headObject; thêm test not_found/etag_mismatch/ok riêng biệt)`
- `libs/modules/media/test/create-media-asset.use-case.spec.ts (round 30: assertion createPresignedUploadUrl có thêm contentLength)`
- `apps/api/test/media-upload-flow.e2e-spec.ts (round 30: 3 lời gọi createPresignedUploadUrl hiện có thêm contentLength; thêm e2e test thật xác nhận upload sai size bị từ chối 403)`
- `libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts (round 31: thêm early-return idempotent khi asset.status === Ready, TRƯỚC mọi storage/processing side effect)`
- `libs/modules/media/test/generate-thumbnail.use-case.spec.ts (round 31: thêm test asset đã ready + object missing/changed vẫn resolve no-op, không gọi storage/transitionStatus)`
- `libs/platform/database/src/typeorm-unit-of-work.ts (round 31: bọc startTransaction()...release() trong try/finally đúng — sửa rò rỉ connection khi startTransaction() thất bại sau connect() thành công)`
- `libs/platform/database/test/typeorm-unit-of-work.spec.ts (round 31: thêm test startTransaction() reject vẫn gọi release(), không gọi rollbackTransaction() vô nghĩa)`
- `libs/platform/health/src/health.controller.ts (round 31: thêm @SkipThrottle() — health check không bao giờ bị rate-limit dù ThrottlerGuard áp dụng toàn cục qua APP_GUARD)`
- `apps/api/test/rate-limit.e2e-spec.ts (round 31: đổi target sang GET /media/:id thay vì /health/liveness, đúng theo đề xuất Codex — health đã được exempt)`
- `.github/workflows/deploy-production.yml (round 31: bước tạo tag giờ idempotent — chấp nhận tag đã tồn tại nếu trỏ đúng commit hiện tại, fail loudly nếu trỏ commit khác, cho phép resume sau khi bước merge master thất bại)`
- `libs/platform/queue/src/bullmq/bullmq-queue.factory.ts (round 32: onModuleDestroy() đua queue.close() với BULLMQ_SHUTDOWN_TIMEOUT_MS qua raceAgainstDeadline, fallback queue.disconnect() khi timeout/reject, Promise.allSettled cho nhiều queue)`
- `libs/platform/queue/test/bullmq-queue.factory.spec.ts (mới — round 32: 4 test hồi quy close() không settle/reject, allSettled không chặn queue khác, không force-disconnect khi close() thành công)`
- `libs/platform/configuration/src/config/bullmq.config.ts (round 32: thêm connection.db/tls, đọc từ BULLMQ_REDIS_DB/BULLMQ_REDIS_TLS, fallback REDIS_DB/REDIS_TLS)`
- `libs/platform/configuration/src/schemas/env.schema.ts (round 32: thêm BULLMQ_REDIS_DB/BULLMQ_REDIS_TLS dạng .optional(), không .default() — giữ đúng ngữ nghĩa fallback)`
- `.env.example (round 32: ghi chú BULLMQ_REDIS_DB/BULLMQ_REDIS_TLS nên để trống hoàn toàn, không set key rỗng, để fallback hoạt động đúng)`
- `libs/platform/queue/src/bullmq/bullmq.config.ts (round 32: toBullMqConnectionOptions() map thêm db/tls, tls: {} khi bật thay vì true)`
- `libs/platform/queue/test/bullmq.config.spec.ts (mới — round 32: test mapping db/tls)`
- `libs/platform/realtime/src/redis-io.adapter.ts (round 32: createIOServer() truyền thêm db/tls vào ioredis pub client)`
- `libs/platform/realtime/src/redis-emitter.provider.ts (round 32: thêm tls — trước đó đã có db nhưng thiếu tls)`
- `libs/platform/realtime/test/redis-io.adapter.connection.spec.ts (mới — round 32: test db/tls truyền đúng vào ioredis constructor, mock module ioredis)`
- `libs/platform/realtime/test/redis-emitter.provider.spec.ts (mới — round 32: cùng pattern test cho emitter provider)`
- `libs/platform/queue/src/bullmq/bullmq-queue.factory.ts (round 33: implements BeforeApplicationShutdown thay vì OnModuleDestroy; disconnectSafely() giờ await disconnect() trong try/catch thay vì fire-and-forget)`
- `libs/platform/queue/src/outbox/outbox-relay.service.ts (round 33: đổi từ OnApplicationShutdown sang OnModuleDestroy — dừng hẳn poll TRƯỚC khi BullMqQueueFactory đóng Queue ở phase sau)`
- `libs/platform/queue/src/bullmq/failure-reconciliation.service.ts (round 33: cùng đổi OnApplicationShutdown -> OnModuleDestroy như OutboxRelay)`
- `libs/platform/queue/src/bullmq/bullmq.events.ts (BullMqMetricsCollector) (round 33: cùng đổi OnApplicationShutdown -> OnModuleDestroy)`
- `libs/platform/queue/test/bullmq-queue.factory.spec.ts (round 33: viết lại toàn bộ — describe block + mọi lời gọi đổi sang beforeApplicationShutdown(); thêm test mới xác nhận disconnect() reject được await và swallow thay vì thoát ra ngoài)`
- `libs/platform/queue/test/outbox-relay.service.spec.ts (round 33: onApplicationShutdown -> onModuleDestroy trong cả lời gọi code lẫn tên test/comment)`
- `libs/platform/queue/test/failure-reconciliation.service.spec.ts (round 33: cùng đổi onApplicationShutdown -> onModuleDestroy như outbox-relay.service.spec.ts)`
- `libs/platform/queue/src/bullmq/bullmq.events.ts (round 34: BullMqMetricsCollector thêm shuttingDown flag + currentCollect tracking (collectOnce() wrapper) + onModuleDestroy() giờ async, await currentCollect qua raceAgainstDeadline; thêm ConfigService vào constructor)`
- `libs/platform/queue/test/bullmq.events.spec.ts (round 34: thêm fakeConfigService() helper + describe block 'BullMqMetricsCollector.onModuleDestroy' với 3 test mới — cancellation giữa các queue, deadline khi getJobCounts() không resolve, và resolve ngay khi không có collection nào đang chạy)`

### frontend

- `packages/api-client/src/media-client.ts (mới — createMediaApi() dùng operations[...] thật từ schema đã generate, chứng minh contract được dùng thật chứ không phải dead code)`
- `packages/api-client/src/index.ts (export createMediaApi + export type paths/operations/components từ generated/schema)`
- `packages/api-client/src/generated/schema.d.ts (giờ COMMIT vào git, không còn gitignore — regenerate thật từ openapi.json thật của backend sau khi sửa DTO/@ApiProperty)`
- `packages/api-client/test/media-client.spec.ts (mới — 3 test cho create/confirm/get)`
- `.gitignore (bỏ dòng loại trừ packages/api-client/src/generated/)`
- `.github/workflows/ci.yml (job generate-api-client: BACKEND_REPO_TOKEN thiếu -> fail thay vì skip; thêm bước git diff --exit-code phát hiện drift giữa schema.d.ts đã commit và bản build lại từ backend)`
- `.github/workflows/{release,deploy-production,rollback-production}.yml (cùng hardening smoke-test-bắt-buộc + xác minh version/commitSha + field 'build' như backend)`
- `README.md (cập nhật mục 'API client generation': schema.d.ts được commit, CI fail cứng khi có drift)`
- `docs/guides/release-process.md (round 4: mô tả đúng luồng deploy-production.yml hiện hành — chỉ nhận version, không nhận 2 digest input đã bị xóa)`
- `apps/frontend/.github/workflows/ci.yml (thêm 'master' vào pull_request.branches và push.branches — cùng lý do với backend)`
- `apps/frontend/.github/workflows/ci.yml (drift-check job: đổi '--branch develop' (không tồn tại) thành '--branch master' để tra cứu đúng CI run backend, sau khi round 13 khiến job này lần đầu thực sự chạy trên nhánh hiện hành)`
- `apps/frontend/.github/workflows/deploy-production.yml (cùng thay đổi với backend: gộp 2 bước merge thành 1 bước merge vào master)`
- `apps/frontend/docs/guides/deployment.md (cùng cập nhật mô tả single-branch model)`
- `apps/frontend/docs/guides/release-process.md (cùng cập nhật: cắt release/hotfix từ master, merge vào master)`
- `apps/frontend/.github/workflows/ci.yml (cùng thay đổi: trigger chỉ còn [master])`
- `apps/frontend/.github/workflows/deploy-production.yml (cùng sửa git fetch/checkout master như backend)`
- `apps/frontend/.github/workflows/deploy-production.yml (cùng thêm fetch-depth: 0 và permissions: contents: write như backend)`
- `apps/frontend/.github/workflows/deploy-production.yml (cùng thêm permissions.actions: read như backend)`
- `.github/workflows/release.yml (round 26: cùng fix digest race như backend — concurrency group theo branch + --metadata-file thay vì imagetools inspect lại tag sau khi push, áp dụng cho public-web/admin-web)`
- `.github/workflows/deploy-production.yml (round 27: cùng fix concurrency group như backend)`
- `.github/workflows/rollback-production.yml (round 27: cùng fix concurrency group như backend)`
- `.github/workflows/deploy-production.yml (round 28: cùng fix shell injection như backend)`
- `.github/workflows/rollback-production.yml (round 28: cùng fix shell injection như backend)`
- `.github/workflows/deploy-production.yml (round 31: cùng fix idempotent tag step như backend)`


## Git diff stat

### backend

```text
.env.example                                       |   9 +
 .eslintrc.cjs                                      |   5 +-
 .github/workflows/ci.yml                           |  63 +++-
 .github/workflows/deploy-production.yml            | 219 +++++++++++---
 .github/workflows/release.yml                      | 108 +++++--
 .github/workflows/rollback-production.yml          |  65 ++++-
 .gitignore                                         |   3 +
 README.md                                          |   1 +
 apps/api/src/main.ts                               |  29 +-
 apps/api/test/health.e2e-spec.ts                   |   4 +
 apps/cli/src/app.module.ts                         |   9 +
 apps/cli/src/commands/reprocess-job.command.ts     |  31 +-
 apps/scheduler/src/app.module.ts                   |  17 +-
 apps/scheduler/src/scheduled-tasks.service.ts      |  27 --
 apps/worker/src/app.module.ts                      |   9 +
 apps/worker/src/main.ts                            |   5 +
 docker/docker-compose.yml                          |   7 +
 .../0007-versioned-release-branch-deployment.md    |   7 +-
 docs/guides/deployment.md                          |   3 +-
 docs/guides/release-process.md                     |  38 ++-
 .../contracts/generate-thumbnail.job.ts            |   3 +-
 .../use-cases/confirm-media-upload.use-case.ts     | 132 +++++++--
 .../use-cases/generate-thumbnail.use-case.ts       | 112 ++++++-
 .../src/domain/media-asset/media-asset-status.ts   |   3 +-
 .../domain/media-asset/media-asset.repository.ts   |  55 +++-
 .../media/src/domain/media-asset/media-asset.ts    |  35 ++-
 .../persistence/media-asset.mapper.ts              |   8 +-
 .../persistence/media-asset.orm-entity.ts          |  20 +-
 .../persistence/typeorm-media-asset.repository.ts  |  46 ++-
 libs/modules/media/src/media.module.ts             |  21 +-
 .../src/presentation/http/media.controller.ts      |  53 +++-
 .../jobs/generate-thumbnail.handler.ts             |  20 +-
 libs/modules/media/src/public-api.ts               |   5 +
 .../test/confirm-media-upload.use-case.spec.ts     | 226 ++++++++++++--
 .../media/test/generate-thumbnail.handler.spec.ts  |  34 +++
 libs/modules/media/test/media-asset.spec.ts        |  38 ++-
 libs/platform/cache/src/cache.module.ts            |   2 +
 .../configuration/src/config/bullmq.config.ts      |  10 +
 .../src/config/observability.config.ts             |   5 +
 .../configuration/src/config/redis.config.ts       |   7 +
 .../configuration/src/schemas/env.schema.ts        |   7 +
 libs/platform/database/src/data-source.ts          |   2 +-
 .../database/src/typeorm-options.factory.ts        |  11 +-
 libs/platform/database/src/typeorm-unit-of-work.ts |  48 ++-
 .../database/test/typeorm-options.factory.spec.ts  |  12 +
 libs/platform/health/src/health.controller.ts      |   8 +
 .../platform/observability/src/metrics.registry.ts |  10 +-
 .../queue/src/bullmq/bullmq-queue.factory.ts       |  69 ++++-
 libs/platform/queue/src/bullmq/bullmq.config.ts    |   5 +
 libs/platform/queue/src/bullmq/bullmq.events.ts    | 101 ++++++-
 libs/platform/queue/src/bullmq/bullmq.module.ts    |  21 +-
 libs/platform/queue/src/bullmq/bullmq.publisher.ts |   6 +-
 libs/platform/queue/src/bullmq/bullmq.worker.ts    | 324 +++++++++++++++++++--
 .../queue/src/contracts/background-job-handler.ts  |  20 ++
 libs/platform/queue/src/public-api.ts              |   6 +
 libs/platform/queue/src/registry/queue.registry.ts |  15 +-
 libs/platform/queue/test/bullmq.publisher.spec.ts  |  48 +++
 libs/platform/queue/test/queue.registry.spec.ts    |  10 +
 libs/platform/realtime/src/realtime.module.ts      |   2 +
 .../realtime/src/redis-emitter.provider.ts         |   5 +
 libs/platform/realtime/src/redis-io.adapter.ts     |  73 ++++-
 .../security/src/global-exception.filter.ts        |   1 +
 libs/platform/security/src/public-api.ts           |   2 +
 libs/platform/security/src/security.module.ts      |  15 +-
 libs/platform/storage/src/s3-storage.adapter.ts    |  39 +++
 libs/platform/storage/src/storage.contract.ts      |  27 ++
 libs/platform/storage/src/upload-validation.ts     |  24 ++
 libs/shared/kernel/src/errors/domain-error.ts      |   5 +
 package.json                                       |  11 +-
 69 files changed, 2104 insertions(+), 317 deletions(-)
```

### frontend

```text
.github/workflows/ci.yml                  |  63 ++++++++-
 .github/workflows/deploy-production.yml   | 217 ++++++++++++++++++++++++------
 .github/workflows/release.yml             |  95 ++++++++++---
 .github/workflows/rollback-production.yml |  64 ++++++++-
 .gitignore                                |   1 +
 README.md                                 |  26 +++-
 docs/guides/deployment.md                 |   3 +-
 docs/guides/release-process.md            |  25 ++--
 packages/api-client/package.json          |   2 +-
 packages/api-client/src/index.ts          |   2 +
 10 files changed, 420 insertions(+), 78 deletions(-)
```


## Validation

| Repository | Passed | Commands |
|---|---:|---|
| backend | Yes | lint=passed, typecheck=passed, test=passed, build=passed, test-e2e=passed |
| frontend | Yes | lint=passed, typecheck=passed, test=passed, build=passed |

## Codex review

Đã review đầy đủ backend và frontend. Finding major trước đó về BullMqMetricsCollector đã được khắc phục bằng cooperative cancellation, theo dõi collection đang chạy và deadline khi shutdown, kèm test hồi quy phù hợp. Toàn bộ validation bắt buộc của cycle hiện hành đều đạt; implementation sẵn sàng chờ người dùng nghiệm thu.

- blocker: 0
- major: 0
- minor: 0
- note: 0

## Knowledge updates

- libs/platform/database — not approved — TypeORM entities glob trong toàn bộ codebase phải khớp đúng '*.orm-entity.ts'/'*.orm-entity.js' (không phải '*.entity.ts') — lỗi này khiến KHÔNG entity nào từng được nhận diện ở runtime thật trước round 2, chỉ ẩn vì chưa có test nào thực sự gọi repository qua HTTP thật.
- libs/modules/media/src/application/contracts/generate-thumbnail.job.ts — not approved — BullMQ từ chối customId chứa ':' trừ khi tách được đúng 3 phần qua split(':') (tương thích ngược với repeatable job cũ) — mọi jobId tự tạo trong dự án này nên dùng '-' làm dấu phân cách.
- TypeORM @Column / @nestjs/swagger @ApiProperty — not approved — reflect-metadata suy giảm kiểu 'X | undefined' thành Object ở design-time cho cả TypeORM @Column và @nestjs/swagger @ApiProperty — cả hai đều cần 'type' tường minh khi property là optional.
- apps/worker/src/app.module.ts, apps/scheduler/src/app.module.ts — not approved — apps/worker và apps/scheduler dùng chung BUSINESS_MODULES với apps/api nên bất kỳ guard/dependency mới nào thêm vào 1 module business (vd JwtAuthGuard cần TOKEN_SERVICE) đều phải được đưa vào SecurityModule.register() ở cả 3 app.module.ts, không chỉ apps/api — nếu không cả worker/scheduler sẽ crash ngay khi boot.
- apps/api/src/configure-app.ts — not approved — Test dựng Nest app qua Test.createTestingModule().createNestApplication() KHÔNG tự áp dụng global prefix/ValidationPipe/GlobalExceptionFilter như main.ts thật — phải gọi lại đúng logic đó (nay tách thành configure-app.ts dùng chung) để e2e test phản ánh đúng hành vi production.
- libs/platform/database/src/typeorm-options.factory.ts — not approved — `nest build` (webpack:true, monorepo mode) gộp toàn bộ app + mọi thư viện nó phụ thuộc vào MỘT file dist/apps/<app>/main.js duy nhất — không có file dist/libs/**/*.js riêng lẻ nào theo đường dẫn gốc. Bất kỳ cơ chế nào dựa vào filesystem glob để tìm class/asset theo đường dẫn thư mục gốc (kiểu dist/libs/modules/**/*.orm-entity.js) sẽ luôn thất bại trong image production thật, dù hoạt động đúng khi chạy trực tiếp từ source qua ts-node/ts-jest. Dùng cơ chế dựa trên DI graph (autoLoadEntities, hoặc providers/imports tường minh) thay vì glob khi cần hoạt động nhất quán ở cả 2 môi trường.
- apps/api/src/export-openapi.ts, apps/api/src/configure-app.ts — not approved — SwaggerModule.createDocument() chỉ phản ánh global prefix nếu app.setGlobalPrefix() đã được gọi TRƯỚC ĐÓ trên cùng app instance — bất kỳ script standalone nào build tài liệu OpenAPI qua NestFactory.create() (không đi qua main.ts's bootstrap()) phải tự gọi lại đúng bước này, nếu không tài liệu xuất ra sẽ mô tả sai đường dẫn thật.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — toBullMqError() chuyển non-retryable BackgroundJobError thành BullMQ UnrecoverableError, khiến job dừng ngay lần thử đầu tiên bất kể opts.attempts cấu hình bao nhiêu — bất kỳ logic nào coi 'job.attemptsMade >= opts.attempts' là điều kiện duy nhất để xác định 'lần thử cuối' sẽ bỏ sót trường hợp này. Phải kiểm tra thêm error instanceof UnrecoverableError.
- libs/modules/media/src/domain/media-asset/media-asset.ts — not approved — Một background job handler không bao giờ biết chắc đây có phải lần thực thi 'cuối cùng, có thẩm quyền' cho job đó hay không (BullMQ có thể redeliver job bị coi là stalled) — nên bất kỳ transition nào chuyển sang trạng thái terminal 'xấu' (failed) đều phải tự guard: không được ghi đè lên trạng thái terminal 'tốt' (ready) đã đạt được bởi một lần thực thi khác trước đó.
- libs/modules/media/src/domain/media-asset/media-asset.repository.ts — not approved — Khi 2 execution của CÙNG một job (BullMQ at-least-once delivery) có thể chạy chồng lên nhau thật sự, một transition sang trạng thái terminal (ready/failed) phải là 1 UPDATE nguyên tử có điều kiện trên chính trạng thái hiện tại (WHERE status = expected) ở tầng repository — không phải pattern findById -> mutate -> save, vốn luôn để hở 1 khoảng thời gian giữa đọc và ghi mà execution khác có thể chen vào.
- libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts — not approved — BullMQ's queue.add() với 1 jobId đã tồn tại bản ghi (ở BẤT KỲ trạng thái nào còn trong retention — completed/failed/active/waiting) sẽ KHÔNG tạo execution mới, kể cả khi job cũ đã ở trạng thái terminal 'failed' từ lâu. Bất kỳ luồng nào dùng deterministic job ID cho mục đích idempotency (tránh double-publish) phải cân nhắc: cùng cơ chế đó cũng ngăn một lần 'reprocess' hợp lệ chạy lại, trừ khi chủ động dùng job ID theo từng lần thử (attempt-scoped) hoặc xoá job cũ trước khi add lại.
- apps/cli/src/app.module.ts, apps/worker/src/app.module.ts, apps/scheduler/src/app.module.ts — not approved — MỌI application process import BUSINESS_MODULES (không chỉ apps/api) đều cần SecurityModule.register() nếu bất kỳ business module nào dùng JwtAuthGuard — đã bỏ sót apps/cli ở những round trước dù đã sửa đúng worker/scheduler, cho thấy quy tắc 'thêm dependency mới vào TẤT CẢ app.module.ts dùng BUSINESS_MODULES' cần được kiểm tra tường minh trên danh sách đầy đủ (find apps/*/src/app.module.ts), không dựa vào trí nhớ những app nào đã từng cần sửa.
- libs/modules/media/src/media.module.ts — not approved — Một provider được import vào cùng DI container (qua BUSINESS_MODULES) KHÔNG tự động injectable được từ provider khác ngoài module gốc của nó — NestJS chỉ cho phép nếu module đó khai báo provider trong mảng `exports`. `exports: []` (rỗng) là giá trị mặc định hợp lý cho 1 module chỉ tự dùng nội bộ, nhưng sẽ chặn đứng bất kỳ nhu cầu tương lai nào (như CLI ops tooling) cần inject trực tiếp 1 provider của module đó.
- libs/platform/database/src/typeorm-unit-of-work.ts — not approved — Bất kỳ 'ambient context' nào cần cách ly theo từng request/tác vụ đồng thời (transaction hiện tại, correlation ID...) PHẢI dùng AsyncLocalStorage, không được dùng field mutable đơn trên 1 singleton — dù singleton đó chỉ có 1 instance trong toàn app, field của nó vẫn bị NHIỀU async call chain đọc/ghi đồng thời. CorrelationContext đã làm đúng điều này từ đầu; TypeOrmQueryRunnerContext (scaffold cũ) đã làm sai và chỉ được phát hiện khi thực sự dùng lần đầu.
- libs/platform/queue/src/outbox/outbox.contract.ts — not approved — Bất kỳ use case nào vừa cần ghi domain state VỪA cần publish 1 background job phải dùng transactional outbox (ghi 1 outbox row trong CÙNG transaction với domain write, để 1 relay riêng publish sau) thay vì gọi BackgroundJobPublisher trực tiếp — gọi trực tiếp trước/sau DB write luôn để hở 1 khoảng có thể mất đồng bộ nếu 1 trong 2 thao tác thất bại độc lập.
- libs/platform/queue/src/outbox/outbox-relay.service.ts, libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts — not approved — Bất kỳ cơ chế nào publish/xử lý 1 tác vụ TRỄ HƠN (qua outbox relay, cron, queue riêng...) so với lúc tác vụ đó được TẠO RA sẽ chạy ngoài AsyncLocalStorage context gốc (CorrelationContext) — phải chủ động lưu lại correlationId/actorId vào chính bản ghi tác vụ đó NGAY LÚC TẠO (khi context còn tồn tại), không thể trông chờ context tự động 'theo' tác vụ sang thời điểm xử lý sau.
- libs/platform/queue/src/outbox/outbox-relay.service.ts — not approved — Bất kỳ code nào gọi 1 async function từ setInterval bằng `void fn()` phải tự đảm bảo fn() KHÔNG BAO GIỜ reject — 1 Promise bị bỏ qua bằng `void` mà reject sẽ trở thành unhandled rejection ở top-level, có thể làm crash tiến trình tuỳ cấu hình Node, bất kể try/catch bên trong fn() có vẻ đầy đủ tới đâu (phải bọc TOÀN BỘ thân hàm, không chỉ phần logic chính).
- libs/platform/queue/src/bullmq/failure-reconciliation.service.ts — not approved — Khi cần 1 cơ chế reconciliation bền vững cho 1 hướng dữ liệu, TRƯỚC KHI xây thêm 1 bảng/outbox mới, hãy kiểm tra xem hệ thống đã có sẵn 1 nguồn lưu trữ bền vững nào phù hợp chưa (ở đây: BullMQ/Redis đã tự lưu failed jobs theo removeOnFail retention) — dùng lại nguồn đó thường đơn giản hơn và tránh vấn đề 'kho lưu trữ mới cũng không ghi được khi chính hạ tầng đang gặp sự cố'. Điều kiện tiên quyết: hành động reconcile phải idempotent-an toàn để có thể gọi lại vô điều kiện theo lịch mà không cần thêm state theo dõi 'đã xử lý'.
- libs/modules/media/src/domain/media-asset/media-asset.repository.ts — not approved — Khi 1 domain object có thể được thao tác bởi nhiều 'attempt' độc lập nhưng cùng chia sẻ 1 status trung gian (ví dụ 'processing'), 1 CAS chỉ dựa trên status là KHÔNG ĐỦ để ngăn 1 attempt cũ ghi đè attempt mới — cần thêm 1 định danh attempt (jobId, version, v.v.) vào cả điều kiện WHERE lẫn giá trị SET, và bắt buộc mọi nơi gọi CAS terminal-transition phải truyền đúng định danh của attempt đang thao tác.
- libs/platform/queue/src/bullmq/failure-reconciliation.service.ts, libs/platform/queue/src/outbox/outbox-relay.service.ts — not approved — `setInterval(() => { this.current = this.doWork(); }, ms)` có 1 race: nếu doWork() tự chặn lặp (early-return khi đang chạy) thì giá trị trả về ở 1 tick sau là 1 promise ĐÃ RESOLVE ngay, và nó sẽ GHI ĐÈ this.current đang trỏ tới work THẬT SỰ còn đang chạy — code chờ shutdown (`await this.current`) sẽ chờ sai. Sửa đúng: để chính doWork() là nơi DUY NHẤT gán this.current, chỉ gán khi thật sự bắt đầu (kiểm tra giá trị hiện tại trước, return nó nếu đã có thay vì tạo promise mới), và setInterval callback chỉ gọi `void this.doWork()` không gán gì cả.
- libs/platform/queue/src/registry/queue.registry.ts, libs/platform/queue/src/bullmq/failure-reconciliation.service.ts — not approved — Khi thiết kế 1 cơ chế 'ghi lại rằng X cần được xử lý lại vì write chính đã thất bại do hạ tầng Y đang down', đừng ghi bản ghi đó vào CHÍNH hạ tầng Y — nó sẽ thất bại vì cùng lý do và không thực sự bền vững hơn. Dùng 1 nguồn lưu trữ có tính khả dụng ĐỘC LẬP với Y (ở đây: Redis độc lập với Postgres). Nếu nguồn đó có cơ chế tự dọn dẹp theo dung lượng/số lượng (removeOnFail), phải tắt nó cho đúng phần dữ liệu cần giữ tới khi được xác nhận xử lý xong, nếu không dữ liệu vẫn có thể bị mất dù chọn đúng nguồn lưu trữ.
- libs/platform/queue/src/bullmq/failure-reconciliation.service.ts — not approved — Khi phân trang qua 1 tập hợp có thể bị XÓA XEN KẼ trong lúc đang đọc (ví dụ BullMQ failed set khi vừa reconcile vừa remove()), KHÔNG dùng cursor += PAGE_SIZE cố định — 1 item bị xóa làm mọi item phía sau trượt lên 1 vị trí, nên cursor chỉ được tiến đúng bằng số lượng item GIỮ LẠI (không bị xóa) ở trang vừa đọc; nếu tất cả bị xóa, đọc lại đúng cùng cursor. Dùng 1 Set để 'bỏ qua' item đã thử vẫn có thể khiến toàn bộ phần còn lại của tập hợp không bao giờ được xét nếu nguyên 1 trang đầu không xóa được cái nào.
- libs/platform/queue/src/outbox/outbox-relay.service.ts, libs/platform/queue/src/outbox/typeorm-outbox.repository.ts — not approved — Bất kỳ truy vấn nào dạng 'ORDER BY <cột> LIMIT N' lặp lại định kỳ để xử lý 1 tập hợp record đang chờ (chưa publish/chưa reconcile/...) đều có cùng rủi ro poison-batch nếu không có offset: N record đầu liên tục thất bại sẽ chặn vĩnh viễn mọi record sau. Áp dụng cursor tiến theo số lượng record GIỮ LẠI (chưa xử lý xong) mỗi lần đọc — không phải LIMIT cố định — cho MỌI hàng đợi kiểu này trong hệ thống (BullMQ failed set, outbox unpublished set, và bất kỳ hàng đợi tương tự nào thêm sau này).
- libs/platform/queue/src/bullmq/failure-reconciliation.service.ts — not approved — BullMQ's Queue.getFailed(start,end) là alias của getJobs(['failed'],start,end,false) — asc:false nghĩa là NEWEST-FIRST, không phải oldest-first (dễ nhầm trực giác). Bất kỳ pagination nào dựa trên vị trí (cursor/offset) qua 1 tập hợp có thể có phần tử MỚI chèn vào PHÍA TRƯỚC (như failed set mặc định) đều có rủi ro starvation phần tử cũ dưới tải liên tục — luôn ưu tiên duyệt theo thứ tự oldest-first (asc:true) khi mục tiêu là đảm bảo mọi phần tử cũ cuối cùng đều được xử lý, để phần tử mới chỉ nối vào đuôi (sau cursor), không bao giờ chèn vào trước.
- apps/scheduler/src/scheduled-tasks.service.ts (đã xóa) — not approved — 1 cron job publish qua BackgroundJobPublisher mà KHÔNG có handler tương ứng được đăng ký (@RegisterBackgroundJobHandler) sẽ luôn thất bại ngay khi worker cố xử lý ('No background job handler registered'), và validation/test hiện tại (lint/typecheck/test/e2e) KHÔNG phát hiện được vì không gì thực sự invoke đường cron đó — chỉ có review thủ công/production thật mới lộ ra. Khi thêm 1 @Cron() publish job mới, luôn xác nhận: (a) jobId không chứa ':', (b) có handler thật đã đăng ký cho job name đó, (c) có ít nhất 1 test/integration path thực sự gọi hàm publish để không rơi vào tình trạng 'never actually exercised' như trường hợp này.
- apps/backend/.github/workflows/deploy-production.yml, apps/frontend/.github/workflows/deploy-production.yml, docs/guides/deployment.md, docs/guides/release-process.md (cả 2 repo) — not approved — Repository của epic này dùng single-branch model (chỉ 'master', không có main/develop) theo quyết định tường minh của người dùng — mọi workflow/tài liệu CI/CD viết mới sau này phải merge/trigger dựa trên 'master', không giả định mô hình git-flow (main+develop) mặc định.
- libs/modules/media/src/application/use-cases/confirm-media-upload.use-case.ts — not approved — Đừng bao giờ giả định 1 status transition 'chỉ xảy ra 1 lần, không có concurrent writer' chỉ vì nó LOGICALLY là bước đầu tiên trong lifecycle (ví dụ Pending->Processing) — client retry (do timeout, double-click, mất kết nối giữa chừng dù server đã xử lý xong) là kịch bản concurrent hoàn toàn thực tế cho BẤT KỲ endpoint nào, kể cả bước 'đầu tiên'. Mọi status transition ghi vào DB đều cần CAS (transitionStatus), không có ngoại lệ dựa trên vị trí trong lifecycle.
- libs/modules/media/src/domain/media-asset/media-asset.repository.ts, libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts — not approved — Khi 1 CAS cần XÓA tường minh 1 cột nullable (khác với 'không đụng tới'), dùng `string | null` cho tham số ('null' = xóa, 'undefined' = giữ nguyên) và cho phép ORM entity's property type nhận cả `null` — TypeORM's .update() coi `undefined` là 'bỏ qua field này khỏi SET clause' còn `null` literal mới thực sự sinh ra 'SET column = NULL'.
- ai/tasks/MEMORIES-0001/task.md, ai/tasks/MEMORIES-0001/context.lock.json — not approved — Khi cần ghi nhận 1 quyết định sửa đổi/làm rõ requirement mà ai/bin/request-change không thể chạy (state.yaml's status không khớp completed/awaiting_user_acceptance/reviewing), KHÔNG ghi quyết định đó vào implementation.json's decisions — Codex kiểm tra context.lock.json.requirements/change_cycle để xác định requirement nào đang hiệu lực, không đọc implementation.json như 1 nguồn requirement. Sửa trực tiếp file được liệt kê trong context.lock.json.requirements (thường là task.md) là cách duy nhất thực sự có hiệu lực trong tình huống này.
- libs/platform/queue/src/bullmq/failure-reconciliation.service.ts, libs/platform/queue/src/outbox/outbox-relay.service.ts — not approved — Bất kỳ vòng lặp 'phân trang tới khi hết backlog' nào (đặc biệt khi kết hợp với removeOnFail:false hoặc bất kỳ retention không giới hạn nào khác) đều cần 1 cờ cancellation kiểm tra TRƯỚC MỖI ĐƠN VỊ CÔNG VIỆC (job/message), không chỉ giữa các trang — nếu không, onApplicationShutdown có thể phải chờ toàn bộ backlog xử lý xong, vi phạm shutdown deadline khi backlog đủ lớn.
- libs/platform/queue/src/bullmq/shutdown-deadline.ts — not approved — Cooperative cancellation (cờ boolean kiểm tra giữa các đơn vị công việc) chỉ ngăn 1 vòng lặp BẮT ĐẦU công việc mới — không thể ngắt 1 lệnh gọi I/O ĐANG chạy nếu framework/driver bên dưới (TypeORM, ioredis, BullMQ) không có primitive cancellation thật. Khi cần đảm bảo 1 giới hạn thời gian tuyệt đối (ví dụ graceful shutdown deadline), phải kết hợp thêm Promise.race với 1 deadline timer — chấp nhận rằng lệnh gọi gốc có thể vẫn chạy ngầm sau đó, nhưng bản thân hàm chờ nó (onApplicationShutdown) sẽ luôn return đúng hạn.
- .github/workflows/deploy-production.yml (cả 2 repo) — not approved — `git fetch origin <branch>` (không chỉ định đích) trong 1 GitHub Actions job vừa checkout từ 1 nhánh KHÁC (ví dụ release/vX.Y.Z) không đảm bảo tạo/cập nhật ref cục bộ hay remote-tracking cho <branch> — phụ thuộc refspec mặc định của remote.origin.fetch mà actions/checkout có thể đã thu hẹp. Luôn fetch vào 1 ref tường minh (`git fetch origin <branch>:refs/remotes/origin/<branch>`) rồi `git checkout -B <branch> origin/<branch>` khi cần chuyển sang 1 nhánh khác giữa workflow, đặc biệt ở bước SAU KHI đã push tag/artifact quan trọng — 1 lỗi checkout ở đây để lại release dở dang không dễ re-run sạch.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's Worker.close(force) cache promise của lần gọi ĐẦU TIÊN vào this.closing — mọi lần gọi close() sau đó (dù truyền force khác) chỉ trả lại CÙNG promise cache, bỏ qua force hoàn toàn. Không bao giờ gọi close() nhiều lần với hy vọng 'nâng cấp' lên force sau — phải quyết định force/graceful TRƯỚC lần gọi close() duy nhất (ví dụ dùng pause(), method riêng không bị cache theo cơ chế này, để thăm dò trạng thái active job trước khi quyết định).
- .github/workflows/deploy-production.yml (cả 2 repo) — not approved — actions/checkout@v4 mặc định fetch-depth=1 (shallow, chỉ 1 commit) — bất kỳ bước nào sau đó cần git merge/merge-base (kể cả với 1 nhánh khác vừa fetch) đều cần fetch-depth: 0 (hoặc unshallow tường minh) trong bước checkout ban đầu, nếu không git merge có thể thất bại vì thiếu lịch sử chung, đặc biệt nguy hiểm nếu bước đó chạy SAU KHI đã push artifact quan trọng (tag, manifest) ở bước trước.
- .github/workflows/deploy-production.yml (cả 2 repo) — not approved — GitHub Actions: khai báo `permissions:` tường minh ở BẤT KỲ cấp nào (workflow hay job) khiến MỌI scope không được liệt kê mặc định thành 'none', không giữ nguyên default permissions của repo/org như khi không khai báo gì cả. Khi thêm 1 permission mới cho 1 nhu cầu cụ thể, phải rà soát lại TOÀN BỘ các lệnh khác trong cùng job (gh CLI, actions khác, v.v.) xem có cần scope nào khác không, không chỉ thêm đúng scope vừa phát sinh nhu cầu.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — Khi thiết kế 1 shutdown deadline tổng cho NHIỀU bước tuần tự (pause, close, drain, v.v.), tính đúng 1 deadline DUY NHẤT ở đầu hàm và để MỌI bước race với PHẦN CÒN LẠI của chính deadline đó — không bao giờ cấp lại 1 cửa sổ timeout đầy đủ mới cho bước sau chỉ vì bước trước đã dùng hết budget, nếu không tổng thời gian có thể thành bội số của giá trị cấu hình, phá vỡ đúng mục đích của deadline (giới hạn TỔNG thời gian chờ, không phải từng bước riêng lẻ).
- libs/platform/queue/src/bullmq/bullmq.worker.ts, libs/platform/queue/src/bullmq/shutdown-deadline.ts — not approved — raceAgainstDeadline (Promise.race giữa 1 promise và 1 deadline timer) chỉ giải quyết trường hợp promise TREO (không bao giờ settle) — nếu promise đó REJECT, Promise.race cũng reject theo ngay lập tức, ném lỗi ra ngoài bất kể deadline. Khi promise truyền vào là kết quả của Promise.all trên nhiều thao tác độc lập (ví dụ đóng nhiều worker), LUÔN dùng Promise.allSettled thay vì Promise.all trước khi đưa vào race-against-deadline — nếu không, 1 thao tác lỗi sẽ làm rớt toàn bộ chuỗi cleanup của các thao tác khác, dù mục đích ban đầu là đảm bảo TẤT CẢ đều được dọn dẹp.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — Node's EventEmitter coi 'error' là tên sự kiện ĐẶC BIỆT: phát 'error' mà không có listener nào đăng ký sẽ NÉM lỗi đó ra (throw), có thể crash process, khác với mọi sự kiện khác (chỉ im lặng nếu không ai lắng nghe). Bất kỳ EventEmitter nào từ 1 thư viện bên thứ 3 (BullMQ Worker, ioredis client, v.v.) đều PHẢI được đăng ký listener 'error' tường minh, kể cả khi chỉ để log, nếu không muốn rủi ro crash ngoài ý muốn.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's Worker.pause() (mặc định, không tham số) không chỉ 'chờ active job' đơn thuần — nó gọi whenCurrentJobsFinished() với reconnect mặc định = true, nghĩa là sau khi job xong nó tự disconnect RỒI reconnect lại blocking Redis connection. Nếu code khác (ví dụ force-close sau deadline) đóng chính connection đó trong lúc promise pause() còn đang chạy ngầm (không bị hủy, chỉ bị 'race' bỏ qua), reconnect() sau đó sẽ mở lại 1 connection đã đóng — dangling handle. Khi cần 'chờ active job xong trong 1 deadline rồi mới quyết định force-close', tự theo dõi trạng thái active job qua listener riêng (không đụng BullMQ internals) an toàn hơn nhiều so với dựa vào pause()'s built-in wait.
- libs/platform/realtime/src/redis-io.adapter.ts — not approved — Bất kỳ shutdown/teardown method nào gọi nhiều thao tác độc lập qua Promise.all rồi tiếp tục làm việc khác SAU ĐÓ (ví dụ super.close(server) sau khi đóng các Redis client) đều có cùng rủi ro: 1 thao tác lỗi làm Promise.all reject, bỏ qua hoàn toàn phần code phía sau. Luôn dùng Promise.allSettled (log riêng từng lỗi) khi các thao tác đó ĐỘC LẬP với nhau và phần code phía sau PHẢI luôn chạy bất kể kết quả.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — Promise.allSettled cho phép 1 rejection không làm cả nhóm reject, nhưng nếu KẾT QUẢ từng phần tử bị bỏ qua sau khi await, việc chuyển sang allSettled tự nó không đủ để xử lý đúng lỗi từng phần — allSettled chỉ giải quyết vấn đề 'không được throw sớm', không tự động giải quyết vấn đề 'phải làm gì với 1 rejection'. Phải luôn kiểm tra .status === 'rejected' trên từng phần tử và phản ứng phù hợp (ở đây: force-close) thay vì coi allSettled resolve xong là 'mọi thứ ổn'.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's Worker.processJob(): khi job.moveToCompleted() hoặc job.moveToFailed() tự throw (không phải lỗi kết nối — ví dụ lock bị mất/stalled giữa chừng), retryIfFailed() chỉ emit 'error' và (ở nhánh handleFailed's retry) swallow lỗi mà KHÔNG bao giờ emit 'completed' lẫn 'failed'. Bất kỳ counter/bookkeeping nào dựa vào giả định '1 trong 2 event completed/failed luôn fire đúng 1 lần mỗi attempt' đều có thể kẹt vĩnh viễn trong tình huống lock-loss này — nếu cần đếm 'có bao nhiêu attempt đang chạy', đếm quanh chính lệnh gọi processor của mình (try/finally) thay vì dựa vào event nào đó của thư viện.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's Worker.mainLoop() giữ điều kiện vòng lặp `(!this.closing && !this.paused) || asyncFifoQueue.numTotal() > 0` — nghĩa là ngay cả sau khi paused=true (kể cả pause(true)/doNotWaitActive), main loop vẫn tiếp tục xử lý các job ĐÃ được fetch/commit vào asyncFifoQueue trước đó, chỉ dừng nhận job MỚI. Bất kỳ cơ chế đếm 'có bao nhiêu job đang chạy' nào dựa vào thời điểm processor callback CỦA MÌNH bắt đầu (thay vì thời điểm BullMQ thực sự fetch/commit job, tức event 'active') đều có 1 khoảng hở quiescence: có thể có job đã được BullMQ cam kết chạy nhưng chưa kịp tăng counter. BullMQ emit 'active' đúng lúc fetch/commit (trước khi gọi processor callback), nên đó mới là tín hiệu đúng để tăng counter.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — Bất kỳ hàm async nào mà kết quả (thành công hay reject) được đưa vào 1 Set/collection chỉ gắn .finally() (không .catch()) để dọn dẹp — như notifyFinalFailure trong pendingFinalFailures — PHẢI tự đảm bảo KHÔNG BAO GIỜ reject, kể cả ở bước tra cứu/resolve đầu tiên (không chỉ ở phần gọi hook chính). Một throw đồng bộ ở BẤT KỲ đâu trong thân hàm async đó sẽ tự động trở thành promise reject, và nếu không có .catch() ở nơi tiêu thụ, đó là unhandled rejection thật — Node có thể kết thúc process vì việc này.
- .github/workflows/release.yml — not approved — Bất kỳ workflow nào push lên 1 tag MUTABLE (ví dụ tag version dùng chung cho mọi push lên cùng branch) rồi ĐỌC LẠI thông tin của chính tag đó (digest, metadata) SAU KHI push đều có 1 race nếu không có concurrency guard: 1 run khác có thể retag giữa lúc push và lúc đọc lại, khiến run hiện tại nhận nhầm thông tin của commit khác. Cách loại bỏ race triệt để là lấy thông tin trực tiếp từ OUTPUT của chính lệnh build/push (ví dụ `docker buildx build --metadata-file`), không phụ thuộc trạng thái tag sau đó; concurrency guard (`concurrency: {group, cancel-in-progress}`) theo branch/ref là phòng vệ bổ sung ngăn các run chồng lấn ngay từ đầu.
- libs/platform/cache/src/redis-client.shutdown.ts, libs/platform/realtime/src/redis-emitter-client.shutdown.ts, libs/platform/realtime/src/redis-io.adapter.ts — not approved — ioredis's `quit()` gửi lệnh QUIT và chờ phản hồi từ server, KHÔNG có command/socket timeout mặc định — nếu server còn giữ kết nối TCP nhưng không bao giờ phản hồi (treo, network partition một chiều), quit() có thể treo vô hạn. Bất kỳ graceful-shutdown path nào gọi quit() trực tiếp đều cần race nó với 1 deadline cấu hình được, fallback sang disconnect() (đóng socket cục bộ, không cần round-trip) khi hết hạn — nếu không, toàn bộ tiến trình có thể không bao giờ thoát dù các thành phần khác (BullMQ, v.v.) đã tuân thủ đúng deadline riêng của chúng.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's Worker.processJob() có nhánh getUnrecoverableErrorMessage (job.deferredFailure, hoặc job.attemptsStarted vượt opts.maxStartedAttempts) gọi handleFailed rồi return TRƯỚC callProcessJob — nghĩa là processor callback của ứng dụng KHÔNG BAO GIỜ được gọi cho nhánh này, dù 'active' đã fire trước đó. Bất kỳ cơ chế đếm/theo dõi 'job đang chạy' nào chỉ dựa vào việc processor callback của mình được gọi (dù có try/finally đầy đủ) đều bỏ sót nhánh này. Cách phủ đúng: theo dõi bằng ID (không phải counter số) trong 1 Set, xóa idempotently ở CẢ 'completed'/'failed' listener (phủ nhánh bypass processor) VÀ trong finally của chính processor callback (phủ nhánh lock-loss nơi completed/failed không bao giờ fire) — Set.delete trên id đã bị xóa là no-op nên không thể double-decrement khi cả 2 đường cùng cố xóa 1 id ở luồng bình thường.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ's processJob(): sau khi processor callback của ứng dụng resolve/reject, BullMQ còn phải chạy job.moveToCompleted/job.moveToFailed trên Redis SAU ĐÓ (không đồng thời với callback) trước khi job thực sự được coi là xong. Bất kỳ tracking nào coi 'callback đã settle' là 'job đã xong' đều bỏ sót bước finalize này — nếu nó treo (Redis không phản hồi), tracking đã sai khi báo 'không còn job nào chạy'. Tín hiệu ĐÚNG duy nhất cho 'job đã thực sự xong theo BullMQ' là sự kiện 'completed'/'failed' tự nó, fire đúng lúc bước finalize thành công.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — BullMQ job ID chỉ đảm bảo duy nhất TRONG PHẠM VI 1 QUEUE, không phải toàn cục — nhiều queue khác nhau (mỗi queue 1 Worker riêng, như QueueRegistry ở đây khởi tạo) có thể có job cùng ID (đặc biệt với ID auto-generated). Bất kỳ Set/Map nào theo dõi job theo ID mà không namespace theo tên queue đều có nguy cơ gộp nhầm 2 job khác queue thành 1.
- apps/worker/src/worker-metrics.server.ts — not approved — Node's http.Server.close() chờ MỌI active connection tự kết thúc, không có deadline mặc định — giống hệt lý do ioredis's quit() cần deadline riêng. server.closeAllConnections() (Node 18.2+) là API chính thức để force-đóng mọi connection còn lại khi cần bound thời gian shutdown của 1 HTTP server bất kỳ, không riêng gì framework NestJS.
- .github/workflows/deploy-production.yml, .github/workflows/rollback-production.yml — not approved — 2 workflow khác nhau cùng đọc/ghi 1 nhánh durable dùng chung (ví dụ release-manifests) hoặc cùng tác động lên 1 target chung (ví dụ production) đều cần CHUNG 1 concurrency group (không phải group riêng cho từng workflow) để tuần tự hóa lẫn nhau — concurrency group chỉ tuần tự hóa các run TRONG CÙNG group, nên 2 workflow file khác nhau muốn loại trừ lẫn nhau phải khai báo group tên giống hệt nhau.
- .github/workflows/deploy-production.yml, .github/workflows/rollback-production.yml — not approved — GitHub Actions expression `${{ }}` (kể cả `${{ inputs.* }}` từ workflow_dispatch) được nội suy vào TEXT của `run:` script TRƯỚC KHI shell chạy nó — không có escaping hay quoting tự động nào. Bất kỳ input do người dùng cung cấp (workflow_dispatch, issue/PR title/body, v.v.) mà bị chèn trực tiếp vào `run:` đều là 1 lỗ hổng shell/command injection thật — sửa bằng cách LUÔN đưa input qua `env:` (giá trị được truyền qua process environment, không phải string nội suy vào script text), rồi script chỉ tham chiếu qua biến shell đã quote.
- libs/platform/queue/src/bullmq/bullmq.worker.ts — not approved — Mọi nỗ lực tự xấp xỉ 'quiescence' của 1 BullMQ Worker bằng cách đếm/theo dõi các event công khai ('active'/'completed'/'failed') đều có nguy cơ còn khoảng hở so với trạng thái nội bộ thật của Worker — verified qua 4 vòng review liên tiếp tìm ra 4 khoảng hở riêng biệt. `Worker.whenCurrentJobsFinished(reconnect)` (dù là API `private` không nằm trong .d.ts) chính là promise `mainLoopRunning` mà `Worker.close()` TỰ NÓ dùng nội bộ cho graceful close — đây là nguồn sự thật duy nhất không có khoảng hở, vì không có cách nào 'chính xác hơn' bản thân thư viện. Khi 1 thư viện có sẵn 1 barrier/primitive nội bộ chính xác cho đúng nhu cầu, tự viết lại logic tương đương ở tầng ứng dụng hầu như luôn kém chính xác hơn, dù đã qua nhiều vòng sửa.
- libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts — not approved — 1 presigned PUT URL cho direct-to-S3 upload vẫn còn hiệu lực tới khi hết hạn — bất kỳ validation nào chạy SAU KHI upload xong (ví dụ 1 bước 'confirm' riêng biệt) chỉ chứng minh được trạng thái object TẠI THỜI ĐIỂM ĐÓ, không phải tại thời điểm 1 job nền chạy SAU đó thực sự xử lý nó — khoảng hở TOCTOU thật giữa 2 lần đọc. Cách đóng đúng: ràng buộc lần xử lý sau với 1 định danh nội dung bất biến (ETag/VersionId/checksum) đã quan sát được tại thời điểm validate, rồi re-check định danh đó (không chỉ 'object còn tồn tại') trước khi tin tưởng dùng object.
- libs/platform/cache/src/redis-client.shutdown.ts, libs/platform/realtime/src/redis-emitter-client.shutdown.ts, libs/platform/realtime/src/redis-io.adapter.ts — not approved — Khi thiết kế 1 Promise.race giữa 'thao tác chính' và 'deadline' để quyết định có cần fallback hay không, PHẢI phân biệt rõ outcome của thao tác chính (thành công/reject) chứ không chỉ 'có kịp trong deadline hay không' — nếu .then()/.catch() của thao tác chính đều trả về cùng 1 giá trị (ví dụ cùng `false`), logic fallback phía sau không còn cách nào phân biệt 'thành công thật' với 'thất bại nhưng không phải do timeout', dễ vô tình coi 1 rejection là thành công.
- libs/platform/security/src/security.module.ts — not approved — Import/cấu hình 1 module (ví dụ ThrottlerModule.forRootAsync) chỉ đăng ký DỮ LIỆU cấu hình — không tự động thực thi bất kỳ hành vi nào. Với @nestjs/throttler cụ thể, PHẢI đăng ký thêm { provide: APP_GUARD, useClass: ThrottlerGuard } (hoặc @UseGuards thủ công) thì cấu hình mới thực sự chặn request nào — kiểm tra 'module có được import chưa' không đủ để xác nhận 1 tính năng bảo mật thực sự hoạt động, phải kiểm tra bằng traffic thật vượt giới hạn.
- libs/platform/storage/src/s3-storage.adapter.ts — not approved — AWS SDK v3's getSignedUrl() cho PutObjectCommand: bất kỳ field nào trên command (ví dụ ContentLength) đều được đưa vào X-Amz-SignedHeaders của presigned URL, khiến server-side (S3/MinIO) từ chối request nếu header thực tế gửi lên khác giá trị đã ký — đây là cách S3-native duy nhất để presigned PUT URL thực sự ràng buộc size, không cần chuyển sang presigned POST policy (vốn có content-length-range nhưng đổi hẳn contract sang multipart form). GetObjectCommand hỗ trợ IfMatch tương tự, được server đánh giá atomic trong cùng request — cách xấp xỉ gần nhất cho 'verify rồi dùng nguyên tử' khi không có S3 object versioning.
- libs/platform/storage/src/s3-storage.adapter.ts — not approved — AWS SDK v3's @aws-sdk/client-s3 model MỖI operation's lỗi 404 thành 1 exception class RIÊNG theo operation, không dùng chung 1 class: HeadObjectCommand's 404 là `NotFound` (có export riêng), nhưng GetObjectCommand's 404 là `NoSuchKey` (KHÔNG có export riêng). `error instanceof NotFound` chỉ đúng cho HeadObjectCommand, sai (luôn false) cho GetObjectCommand dù cùng ý nghĩa 404. Với các exception không có export riêng (NoSuchKey, PreconditionFailed), kiểm tra qua error.$metadata.httpStatusCode ổn định hơn dùng error.name (không thuộc contract công khai/ổn định của SDK).
- libs/modules/media/src/application/use-cases/generate-thumbnail.use-case.ts — not approved — 1 use case tự nhận là 'idempotent với redelivery' PHẢI kiểm tra trạng thái terminal (ví dụ status === Ready) làm điều kiện early-return NGAY ĐẦU hàm, trước bất kỳ side effect nào (storage call, external API, v.v.) — không được chỉ dựa vào 1 CAS/write thất bại SAU KHI đã thực hiện side effect để phát hiện redelivery, vì side effect đó tự nó có thể throw trước khi kịp tới bước CAS (ví dụ nếu điều kiện thế giới bên ngoài đã đổi khác kể từ lần chạy thành công trước đó).
- libs/platform/database/src/typeorm-unit-of-work.ts — not approved — Với bất kỳ resource cần release/cleanup (connection pool, file handle, lock, v.v.), try/finally phải bắt đầu NGAY SAU bước thực sự chiếm dụng resource đó thành công (không phải sau MỌI bước khởi tạo tiếp theo) — nếu 1 bước khởi tạo SAU KHI đã chiếm dụng resource (ví dụ BEGIN transaction sau khi đã checkout connection) thất bại mà nằm ngoài try/finally, resource đó rò rỉ vĩnh viễn.
- .github/workflows/deploy-production.yml — not approved — Trong 1 workflow nhiều bước với side effect KHÔNG thể hoàn tác dễ dàng (tạo git tag, ghi file durable, v.v.) chạy TRƯỚC 1 bước khác có thể thất bại, mỗi bước side-effect đó phải tự kiểm tra 'đã làm việc này chưa' và bỏ qua an toàn nếu có (miễn là kết quả khớp với lần chạy hiện tại) — nếu không, workflow không thể resume sau khi bước SAU thất bại, vì rerun sẽ luôn fail ngay ở chính bước side-effect đã hoàn tất trước đó.
- libs/platform/queue/src/bullmq/bullmq-queue.factory.ts — not approved — BullMQ's Queue.close() chia sẻ CHÍNH XÁC 2 đặc điểm của Worker.close() cần fix riêng trong các round trước: cache theo lần gọi đầu tiên (gọi lại sau đó chỉ re-await cùng promise, không có tác dụng gì thêm) và cuối cùng await ioredis quit() (không có command/socket timeout mặc định). Bất kỳ chỗ nào trong codebase gọi trực tiếp queue.close() hoặc worker.close() trong shutdown hook đều cần cùng 1 kiểu xử lý (race với deadline, fallback disconnect() không bị cache) — không thể giả định 1 fix đã áp dụng cho Worker cũng tự động đúng cho mọi class khác cùng thư viện.
- libs/platform/configuration — not approved — Với dotenv/@nestjs/config: 1 dòng `KEY=` (không có giá trị) trong file .env parse thành chuỗi RỖNG (''), KHÔNG PHẢI undefined. Với field Zod kiểu z.enum(['true','false']).optional(), '' làm validate THẤT BẠI (không phải coi là unset). Với field z.coerce.number().optional(), '' được coerce THÀNH 0 (JS quirk: Number('')===0) — 1 giá trị cụ thể sai, không phải 'chưa set'. Khi 1 field code-level có logic fallback kiểu 'X ?? Y' dựa vào X thực sự là undefined, .env.example dùng cho field đó PHẢI để hẳn KHÔNG CÓ dòng key, không được viết KEY= (rỗng) — nếu không, người dùng copy nguyên .env.example sẽ vô tình 'set' field đó thành giá trị rỗng/0, phá vỡ fallback.
- libs/platform/queue/src/bullmq/bullmq-queue.factory.ts — not approved — queue.disconnect() (BullMQ) trả về Promise<void> và có thể tự reject — khác với close(), nó KHÔNG cache theo lần gọi đầu tiên nên an toàn gọi lại sau khi close() đã thua 1 deadline race, nhưng vẫn phải được await trong try/catch riêng, không được gọi fire-and-forget, nếu không rejection của nó có thể thoát ra thành unhandled promise rejection đúng lúc process đang shutdown.
- libs/platform/queue — not approved — NestJS đảm bảo thứ tự PHASE-TO-PHASE khi shutdown (onModuleDestroy toàn bộ module -> beforeApplicationShutdown toàn bộ module -> onApplicationShutdown toàn bộ module, xác minh trực tiếp trong node_modules/@nestjs/core/nest-application-context.js's close()), nhưng KHÔNG đảm bảo thứ tự giữa các provider khác nhau TRONG CÙNG 1 phase. Khi 1 provider A đóng 1 tài nguyên dùng chung (kết nối, queue, v.v.) mà provider B khác vẫn còn đang thao tác vào tài nguyên đó lúc shutdown, cách đúng để đảm bảo B luôn dừng TRƯỚC khi A đóng tài nguyên là đặt A và B ở 2 phase KHÁC NHAU (A ở phase sau B), không phải dựa vào thứ tự đăng ký provider trong cùng 1 phase.
- libs/platform/queue/src/bullmq/bullmq.events.ts — not approved — Khi thêm 1 pattern cooperative-cancellation + deadline (shuttingDown flag + in-flight promise tracking) cho 1 service tiêu thụ Queue vì lifecycle ordering với BullMqQueueFactory, phải áp dụng cho MỌI service tiêu thụ Queue tương tự — kể cả 1 service tưởng như 'chỉ đọc metrics, không side-effect quan trọng' như BullMqMetricsCollector. Nó vẫn gọi getQueue()/getJobCounts() trên cùng tập Queue mà factory quản lý vòng đời, nên vẫn dính đúng race: chỉ clearInterval() không đủ, vì 1 lượt collect() đang chạy dở có thể tiếp tục truy cập Queue sau khi bị đóng hoặc tạo kết nối mới không bao giờ được đóng.

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
