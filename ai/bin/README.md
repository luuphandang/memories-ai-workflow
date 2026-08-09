# Script Reference

- `ai`: CLI tổng hợp.
- `bootstrap`: liên kết cấu hình local.
- `self-check`: xác thực cấu hình; `--smoke` chạy pipeline mô phỏng trong workspace tạm.
- `create-task`: tạo bộ file Jira epic/story/task, acceptance và thư mục changes.
- `register-worktree`: đăng ký worktree do developer đã tạo.
- `prepare-context`: kiểm tra tài liệu/worktree, nạp các requirement addendum và tạo context lock.
- `prepare-plan`: phân rã checkbox requirement thành vertical slices và tạo `execution-plan.json` cho cycle hiện hành.
- `classify-skills`: đề xuất skill theo repository/nội dung; chỉ sửa `task.yaml` khi có `--apply`.
- `run-claude`: gọi Claude implementer cho cycle hiện hành; lưu checkpoint/log theo attempt và resume phiên bị gián đoạn khi có session ID.
- `run-claude` đồng thời bắt buộc skill hash, handoff skill evidence và các deterministic implementation checks.
- `run-task`: tự động lặp implement → validate → review → request-fixes; tự xếp validation failure cho attempt sau và dừng ở user acceptance hoặc trạng thái cần can thiệp.
- `validate`: chạy command deterministic.
- `run-codex-review`: chạy wiring/acceptance evidence gates rồi gọi Codex read-only với review skill bắt buộc.
- `request-fixes`: tạo danh sách fix theo `review.fail_on` và acceptance/validation bị thiếu.
- `finalize-task`: sinh báo cáo theo `report.*`, từ chối dry-run validation và chuyển task đạt gate sang `awaiting_user_acceptance`.
- `accept-task`: ghi xác nhận người dùng và chuyển task sang `completed`.
- `request-change`: tạo correction hoặc post-completion requirement-change cycle, lưu baseline và tái sử dụng worktree đã đăng ký.
- `update-knowledge`: lập kế hoạch hoặc áp dụng update sau khi task đã được người dùng xác nhận.
- `rebuild-indexes`: sinh chỉ mục trạng thái.
- `metrics`: tổng hợp attempt, resume, duration và token usage do CLI cung cấp.

Chạy `./ai/bin/ai --help` để xem command.
