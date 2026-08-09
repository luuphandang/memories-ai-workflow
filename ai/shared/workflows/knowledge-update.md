# Knowledge Update Workflow

Chỉ lưu kiến thức có giá trị lâu dài:

- quy tắc nghiệp vụ đã xác minh
- quyết định kiến trúc
- command build/test chính xác
- convention repo
- API/data contract
- source map quan trọng
- known issue có cách nhận diện

Không lưu transcript, log dài, toàn bộ diff, suy luận tạm thời hoặc lỗi một lần.

```text
Claude đề xuất → Codex duyệt kỹ thuật → người dùng xác nhận completed
→ script kiểm tra path/schema → developer xem diff → script áp dụng
```

Không áp dụng knowledge update ở trạng thái `awaiting_user_acceptance`, vì người dùng vẫn có thể yêu cầu correction. Khi task được mở lại sau completion, knowledge mới của change cycle chỉ áp dụng sau lần xác nhận tiếp theo.

Nội dung liên quan source code phải được xác minh và thay marker `[BỔ SUNG THEO DỰ ÁN]`.
Nội dung liên quan ticket phải được xác minh và thay marker `[BỔ SUNG THEO TÍNH NĂNG]`.

Plan-only hiển thị mọi entry cùng trạng thái approval để người duyệt không phải sửa JSON trước khi thấy kế hoạch. Khi áp dụng, mỗi entry `proposal` được ghi ra một file riêng có số thứ tự; nhiều proposal cùng target không được ghi đè lẫn nhau. Entry đã sẵn sàng cập nhật knowledge chính thức phải dùng `append`, `replace` hoặc `create` và chỉ đặt `approved: true` sau khi nội dung đã được biên tập. `append` bỏ qua nội dung đã tồn tại nguyên vẹn để rerun không nhân đôi section.
