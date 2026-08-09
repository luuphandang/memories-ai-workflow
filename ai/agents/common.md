# Quy tắc chung cho mọi agent

## Thứ tự ưu tiên

1. Ranh giới an toàn và policy trong `ai/shared/policies/`.
2. Yêu cầu gốc trong `ai/tasks/<TASK-ID>/task.md`.
3. Các requirement addendum theo thứ tự `changes/cycle-NNN/`; cycle mới hơn ghi đè phần xung đột được nêu rõ.
4. Knowledge theo repo/domain được liệt kê trong `context.yaml`.
5. Source code thực tế trong worktree.
6. Giả định được ghi rõ; không biến giả định thành sự thật.

## Bắt buộc

- Chỉ làm việc với Jira item và active change cycle hiện tại.
- Đọc và áp dụng toàn bộ skill bắt buộc đã khóa trong `context.lock.json`; không dùng bản skill có hash khác.
- Theo `execution-plan.json`, chỉ xử lý một vertical slice tại một thời điểm và cập nhật checkpoint.
- Chỉ đọc tài liệu được liệt kê/khóa trong context, sau đó mở rộng on-demand khi thực sự liên quan.
- Giữ nguyên thay đổi không liên quan đang tồn tại trong worktree.
- Không đọc secret, `.env`, token, credential hoặc dữ liệu người dùng thật.
- Không commit, push, merge, rebase, reset, clean, checkout/switch branch hoặc quản lý worktree.
- Mọi kết quả máy đọc phải tuân thủ JSON Schema.
- Nội dung chưa thể xác minh phải giữ marker `[BỔ SUNG THEO DỰ ÁN]` hoặc `[BỔ SUNG THEO TÍNH NĂNG]`.
- Không tự chuyển task sang `completed`; chỉ người dùng xác nhận qua workflow acceptance.

## Trao đổi giữa agent

Không chuyển transcript hội thoại. Chỉ dùng task, requirement addendum, context lock, implementation handoff, validation, Git diff, review và knowledge proposal.
