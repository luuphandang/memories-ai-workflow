# Glossary

- **Implementer**: Claude, agent thay đổi source code.
- **Reviewer**: Codex, agent review độc lập ở chế độ read-only.
- **Technical pass**: validation bắt buộc pass và Codex verdict là `pass`.
- **User acceptance**: xác nhận rõ ràng của người dùng rằng cycle hiện hành đã đáp ứng yêu cầu.
- **Change cycle**: một vòng correction hoặc requirement change có hồ sơ riêng.
- **Correction**: yêu cầu sửa trước khi user acceptance.
- **Requirement change**: yêu cầu mới sau khi task đã completed.
- **Baseline**: snapshot output của cycle trước, chỉ dùng làm lịch sử/đối chiếu.
- **Effective requirements**: yêu cầu gốc cộng các addendum theo thứ tự cycle.
- **Reopened**: task completed được mở lại và tiếp tục trên worktree đã đăng ký.
- **Context lock**: danh sách tài liệu, hash và trạng thái repository tại thời điểm chuẩn bị.
- **Knowledge base**: `ai/shared`, `ai/repos`, `ai/domains`; chỉ chứa kiến thức bền vững đã xác minh.
- **Runtime**: log/output cục bộ trong `worktrees/<ID>/.ai` và `ai/runtime`.
- **Capability**: functionality semantic có producer, consumer, contract fingerprint và version.
- **Resource lock**: quyền đọc/ghi resource; độc lập với trách nhiệm tạo capability.
- **Plan Patch**: mutation proposal có base version, được Plan Reconciler áp dụng atomically.
- **Partially blocked**: task còn slice runnable dù một số slice chờ dependency.
- **Merge ready**: integration manifest còn fresh trên exact source/target/dependency snapshot.
