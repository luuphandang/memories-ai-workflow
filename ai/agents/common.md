# Quy tắc chung cho mọi agent

## Thứ tự ưu tiên

1. Ranh giới an toàn và policy trong `ai/shared/policies/`.
2. Yêu cầu gốc trong `ai/tasks/<TASK-ID>/task.md`.
3. Chỉ các requirement addendum **chưa được gộp** (unconsolidated), theo thứ tự
   `changes/cycle-NNN/`, đúng như danh sách trong `context.lock.json.requirements`
   (sinh bởi resolver `requirement_documents()` dùng chung cho mọi agent). Addendum của
   cycle ≤ `requirements_consolidated_through_cycle` đã được gộp vào `task.md` — đây là
   audit artifact lịch sử, **không đọc lại và không áp dụng lần nữa**. Trong các addendum
   còn hiệu lực, addendum mới hơn chỉ ghi đè phần xung đột được nêu rõ.
4. Knowledge theo repo/domain được liệt kê trong `context.yaml`.
5. Source code thực tế trong worktree.
6. Giả định được ghi rõ; không biến giả định thành sự thật.

Không tự ý glob/tự đọc lại toàn bộ `changes/cycle-*/requirement-addendum.md` trên đĩa —
luôn dùng đúng danh sách requirement đã khóa trong `context.lock.json`.

## Bắt buộc

- Chỉ làm việc với Jira item và active change cycle hiện tại.
- Đọc và áp dụng toàn bộ skill bắt buộc đã khóa trong `context.lock.json`; không dùng bản skill có hash khác.
- Khi tạo migration backend, bắt buộc dùng skill `create-backend-migration` và npm script do backend định nghĩa; không tự tạo file migration hoặc gọi TypeORM CLI trực tiếp.
- Trước khi handoff, bắt buộc đối chiếu exact changed-file inventory bằng `verify-implementation-handoff`; không ghi chú vào chuỗi path.
- Không tái sử dụng evidence sau khi source, migration, seed, fixture hoặc capture script thay đổi;
  tạo manifest chuẩn trong task evidence, rồi dùng bước sync của `validate-evidence-provenance`
  để kiểm tra và publish atomically sang runtime. Không sửa đồng thời hai bản manifest.
- Theo `execution-plan.json`, chỉ xử lý một vertical slice tại một thời điểm và cập nhật checkpoint.
- Trước shared mutation, phân loại LOCAL/TASK_SCOPED/SHARED. Với SHARED, publish write
  intent và claim resource/capability qua orchestrator trước khi sửa.
- Dependency mới phát hiện trong runtime phải publish qua `ai dependency discover`; agent
  không trực tiếp sửa registry hoặc master execution plan. Exploratory file reads không phải
  dependency; chỉ publish confirmed dependency/contract consumption.
- Capability dùng chung đi qua PROPOSED → CLAIMED → BUILDING → AVAILABLE với source snapshot
  và validation evidence. Trước handoff phải kiểm tra plan/context/dependency/checkpoint freshness.
- Chỉ đọc tài liệu được liệt kê/khóa trong context, sau đó mở rộng on-demand khi thực sự liên quan.
- Khi `context.lock.json.codegraph.repositories.<repo>.ready` là `true`, dùng MCP
  `codegraph_<repo>` trước cho câu hỏi kiến trúc, symbol flow, caller/callee và impact.
  Chỉ quay về grep/read khi kiểm tra nội dung vừa sửa, file phi mã nguồn hoặc graph báo thiếu/stale.
- Giữ nguyên thay đổi không liên quan đang tồn tại trong worktree.
- Không đọc secret, `.env`, token, credential hoặc dữ liệu người dùng thật.
- Không commit, push, merge, rebase, reset, clean, checkout/switch branch hoặc quản lý worktree.
- Mọi kết quả máy đọc phải tuân thủ JSON Schema.
- Nội dung chưa thể xác minh phải giữ marker `[BỔ SUNG THEO DỰ ÁN]` hoặc `[BỔ SUNG THEO TÍNH NĂNG]`.
- Không tự chuyển task sang `completed`; chỉ người dùng xác nhận qua workflow acceptance.

## Trao đổi giữa agent

Không chuyển transcript hội thoại. Chỉ dùng task, requirement addendum, context lock, implementation handoff, validation, Git diff, review và knowledge proposal.
