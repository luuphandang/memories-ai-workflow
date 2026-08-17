# Implementation Workflow

1. Xác minh Jira hierarchy, required skills, scope assessment và `execution-plan.json`.
2. Xác minh đúng worktree, branch, SHA và dirty state; không tạo worktree.
3. Đọc `task.md`, sau đó đọc toàn bộ `changes/cycle-*/requirement-addendum.md` theo thứ tự tăng dần.
4. Với active cycle, đọc cả `user-request.md` và bằng chứng liên quan.
5. Đọc context `initial`; chỉ mở `on-demand` khi cần.
6. Mapping acceptance criteria hiệu lực → vertical slice → file/module/test dự kiến; chỉ mở một slice tại một thời điểm.
7. Ghi và cập nhật `implementation-progress.json` sau từng milestone để phiên sau có thể tiếp tục mà không đọc/suy luận lại toàn bộ.
8. Thực hiện thay đổi nhỏ, có thể review; giữ nguyên phần không liên quan.
9. Chạy lint/typecheck/test/build theo `commands.yaml`.
10. Tự review diff, loại bỏ debug code và thay đổi ngoài scope.
11. Sau thay đổi cuối cùng có thể ảnh hưởng evidence, cập nhật manifest chuẩn tại
    `ai/tasks/<TASK-ID>/evidence/provenance.json`, rồi chạy bước sync của
    `validate-evidence-provenance` để publish atomically vào runtime validation; không duy trì
    hai manifest thủ công.
12. Ghi `implementation.json`, nêu rõ change cycle đang xử lý.
13. Ghi `applied_skills` cùng hash đã khóa và deterministic checks đã hoàn tất.

Kiến trúc/module/convention cụ thể: xem `ai/repos/backend/{architecture,conventions,api-rules,database-rules,testing,source-map}.md` (backend) và `ai/repos/frontend/{architecture,conventions,ui-rules,api-client-rules,testing,source-map}.md` (frontend) — không lặp lại nội dung ở đây, luôn đọc bản mới nhất của các file đó trước khi implement.
Luồng nghiệp vụ và trường hợp biên: `[BỔ SUNG THEO TÍNH NĂNG]`.
