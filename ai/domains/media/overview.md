# Media Asset Domain — Overview

Media asset được tạo ở trạng thái `pending`, client upload trực tiếp bằng presigned S3 URL, rồi confirm để chuyển sang `processing` và enqueue thumbnail job qua transactional outbox. Kết quả xử lý chuyển asset sang `ready` hoặc `failed`; asset lỗi có thể được reprocess bằng attempt mới.

Source chính nằm tại `libs/modules/media`: domain entity và repository port trong `src/domain/media-asset`, use case trong `src/application/use-cases`, TypeORM adapter trong `src/infrastructure/persistence`, HTTP API trong `src/presentation/http`.

Trạng thái là invariant nghiệp vụ, không chỉ là progress display. Mọi writer đồng thời phải tuân thủ transition hợp lệ và attempt ownership.
