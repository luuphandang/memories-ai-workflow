# Worktree Policy

- `worktrees/<TASK-ID>/` là task workspace, không phải Git repository.
- Mỗi thư mục con có tên repo là một Git worktree độc lập.
- Tên repo trong worktree phải giữ nguyên tên repo gốc.
- `ai task create` tạo và đăng ký đồng thời worktree `backend` và `frontend`.
- Branch có dạng `{{type}}/<TASK-ID>-<title-kebab-case>`.
- Epic bắt đầu từ `origin/master`; story từ remote branch của epic cha; task từ remote
  branch của story cha.
- Command sao chép `.env` từ `apps/<repo>/.env` sang worktree (giữ bản nguồn cho task sau),
  rồi chạy `npm install` trong từng repo. Không ghi secret vào hồ sơ task hoặc log.
- Requirement đầu vào của user nằm tại `worktrees/<TASK-ID>/docs/`.
- Một Jira task có thể liên quan nhiều repo.
- Runtime dùng chung của task nằm tại `worktrees/<TASK-ID>/.ai/`.
- Không đặt `.ai/` bên trong repo worktree để tránh lẫn vào source diff.
- Khi task đã `completed` được mở lại, phải tiếp tục dùng đúng worktree path và branch đã đăng ký; `request-change` không tạo worktree mới.
- Nếu worktree đã bị xóa hoặc branch đã đổi, task chuyển `blocked` để developer xử lý thủ công; script không tự phục hồi hay checkout.

Nhánh dài hạn duy nhất của cả hai repo là `master`; hierarchy dùng các branch cha ngắn hạn
theo quy tắc trên, không dùng `develop`/`staging`/`release/*`.
