# Media Asset Workflow

1. Create asset: validate MIME/size, tạo object key từ owner + UUID + extension theo MIME, lưu asset `pending`, trả presigned PUT URL.
2. Confirm upload: đọc metadata, đối chiếu MIME/size và lưu immutable content identity (`ETag` hoặc version/checksum); CAS `pending → processing` cùng job attempt ID và ghi outbox trong một transaction.
3. Process: worker re-check content identity bằng request có precondition trước khi tạo thumbnail. Redelivery của asset đã `ready` phải early-return trước mọi storage/external side effect.
4. Complete/fail: terminal transition dùng CAS theo status + current job ID. Attempt cũ không được ghi đè kết quả của attempt mới hoặc đổi `ready` thành `failed`.
5. Reprocess: chỉ asset `failed` được CAS sang `processing`; tạo job ID mới theo attempt và ghi outbox cùng transaction.

Presigned PUT còn hiệu lực sau confirm, nên kiểm tra “object tồn tại” không đóng được TOCTOU. Processing phải ràng buộc vào content identity đã xác nhận, không chỉ object key.
