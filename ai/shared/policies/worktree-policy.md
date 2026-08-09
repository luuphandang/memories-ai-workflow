# Worktree Policy

- `worktrees/<TASK-ID>/` là task workspace, không phải Git repository.
- Mỗi thư mục con có tên repo là một Git worktree độc lập.
- Tên repo trong worktree phải giữ nguyên tên repo gốc.
- Developer tạo và xóa worktree; AI/script chỉ đăng ký, xác minh và sử dụng đường dẫn.
- Một Jira task có thể liên quan nhiều repo.
- Runtime dùng chung của task nằm tại `worktrees/<TASK-ID>/.ai/`.
- Không đặt `.ai/` bên trong repo worktree để tránh lẫn vào source diff.
- Khi task đã `completed` được mở lại, phải tiếp tục dùng đúng worktree path và branch đã đăng ký; `request-change` không tạo worktree mới.
- Nếu worktree đã bị xóa hoặc branch đã đổi, task chuyển `blocked` để developer xử lý thủ công; script không tự phục hồi hay checkout.

Quy tắc base branch theo môi trường: cả 2 repo (`backend`, `frontend`) dùng đúng 1 nhánh dài hạn `master` làm base — không có nhánh môi trường riêng biệt (không có `develop`/`staging`/`release/*`), theo mô hình release single long-lived branch đã chọn cho dự án (xem `docs/guides/release-process.md`).
Danh sách repo và base ref cho tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`.
