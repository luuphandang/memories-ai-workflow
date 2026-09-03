# Implementation Workflow

1. Xác minh Jira hierarchy, required skills, scope assessment và `execution-plan.json`.
2. Xác minh đúng worktree, branch, SHA và dirty state; không tạo worktree.
3. Đọc `task.md`, sau đó chỉ đọc các requirement document được liệt kê trong
   `context.lock.json.requirements`; không glob lại addendum lịch sử đã consolidation.
4. Với active cycle, chỉ đọc `user-request.md` và bằng chứng được context lock/resolver liệt kê.
5. Đọc context `initial`; chỉ mở `on-demand` khi cần.
6. Mapping acceptance criteria hiệu lực → vertical slice → file/module/test dự kiến; chỉ mở một slice tại một thời điểm.
7. Ghi và cập nhật `implementation-progress.json` sau từng milestone để phiên sau có thể tiếp tục mà không đọc/suy luận lại toàn bộ.
   Agent không được tự chuyển `execution-plan.json.slices[].status`; orchestrator chỉ đánh dấu
   completed sau quick validation. Handoff hợp lệ chuyển sang `implementation_ready_for_validation`
   để mọi lần restart tiếp tục từ validation, không implement lại slice.
8. Thực hiện thay đổi nhỏ, có thể review; giữ nguyên phần không liên quan.
9. Chạy lint/typecheck/test/build theo `commands.yaml`.
10. Tự review diff, loại bỏ debug code và thay đổi ngoài scope.
11. Sau thay đổi cuối cùng có thể ảnh hưởng evidence, cập nhật manifest chuẩn tại
    `ai/tasks/<TASK-ID>/evidence/provenance.json`, rồi chạy bước sync của
    `validate-evidence-provenance` để publish atomically vào runtime validation; không duy trì
    hai manifest thủ công.
12. Ghi `implementation.json`, nêu rõ change cycle đang xử lý.
13. Ghi `applied_skills` cùng hash đã khóa và deterministic checks đã hoàn tất.

Kiến trúc/module/convention cụ thể: chỉ dùng đúng các tài liệu repo/domain và hash đã khóa
trong `context.lock.json`; mở rộng on-demand qua resolver rồi khóa lại context trước khi áp dụng.
Luồng nghiệp vụ và trường hợp biên: `[BỔ SUNG THEO TÍNH NĂNG]`.
