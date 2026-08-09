# Media Asset Decisions

- Status transition được thực thi bằng conditional update ở repository; không dùng `findById → mutate → save` cho transition có concurrent writer.
- `currentJobId` là attempt identity: terminal writer phải chứng minh nó đang sở hữu attempt hiện hành. `null` nghĩa là xóa cột; `undefined` nghĩa là không thay đổi trong TypeORM update.
- Idempotency được kiểm tra trước side effect và xác nhận lại ở bước CAS. Trạng thái terminal tốt (`ready`) không bị downgrade bởi redelivery hoặc final-failure callback cũ.
- Direct upload bị ràng buộc MIME, size và content identity. AWS/S3 operation errors được phân loại ưu tiên theo HTTP metadata khi SDK không cung cấp exception class ổn định cho operation đó.
