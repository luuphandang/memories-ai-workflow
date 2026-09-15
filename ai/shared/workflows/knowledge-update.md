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
Claude soạn nội dung áp dụng được → Codex duyệt kỹ thuật → người dùng xác nhận completed
→ acceptance transaction kiểm tra path/schema → script tự động áp dụng
```

Không áp dụng knowledge update ở trạng thái `awaiting_user_acceptance`, vì người dùng vẫn có thể yêu cầu correction. Khi task được mở lại sau completion, knowledge mới của change cycle chỉ áp dụng sau lần xác nhận tiếp theo.

Nội dung liên quan source code phải được xác minh và thay marker `[BỔ SUNG THEO DỰ ÁN]`.
Nội dung liên quan ticket phải được xác minh và thay marker `[BỔ SUNG THEO TÍNH NĂNG]`.

`known issue có cách nhận diện` lưu tại `ai/shared/quality/known-issues/<skill-name>.md`
(tối đa một file mỗi skill). `prepare-context` tự nạp file này vào `context.lock.json` cho
task nào yêu cầu đúng skill đó, nên nội dung phải nêu rõ cách nhận diện lỗi thay vì mô tả
chung chung. Update nhắm vào `known-issues/*.md` bắt buộc có dòng `Fixture: <path-tới-file>`
trỏ tới regression fixture đã tồn tại trong repo; `update-knowledge --apply --strict` chặn
entry thiếu dòng này hoặc trỏ tới file không tồn tại.

Plan-only hiển thị mọi entry cùng trạng thái approval. Implementer phải xuất nội dung hoàn chỉnh với `append`, `replace` hoặc `create`; reviewer chỉ duyệt entry áp dụng trực tiếp được. Khi acceptance chạy, `update-knowledge --apply --strict` preflight toàn bộ entry đã duyệt rồi tự động áp dụng. Entry `proposal`, content rỗng hoặc còn marker không được phép đi qua finalization/acceptance. `append` bỏ qua nội dung đã tồn tại nguyên vẹn để rerun không nhân đôi section.

`ai/bin/update-knowledge` áp dụng các entry đã được duyệt vào nguồn kiến thức canonical
trong `ai/shared/`, `ai/repos/` và `ai/domains/` sau khi task `completed` và được nghiệm
thu. Không có bước publish sang kho nhớ ngoài.
