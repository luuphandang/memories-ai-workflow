# Script Reference

- `ai`: CLI tổng hợp.
- `bootstrap`: liên kết cấu hình local.
- `self-check`: xác thực cấu hình; `--smoke` chạy pipeline mô phỏng trong workspace tạm.
- `create-task`: tạo bộ file Jira epic/story/task, acceptance và thư mục changes.
- `register-worktree`: đăng ký worktree do developer đã tạo.
- `prepare-context`: kiểm tra tài liệu/worktree, nạp các requirement addendum và tạo context lock.
- `prepare-plan`: phân rã checkbox requirement thành vertical slices và tạo `execution-plan.json` cho cycle hiện hành.
- `classify-skills`: đề xuất skill theo repository/nội dung; chỉ sửa `task.yaml` khi có `--apply`.
- `manage-codegraph`: tạo/sync/kiểm tra CodeGraph index cho mọi worktree của task; MCP
  được sinh động theo task cho Claude và Codex, không sửa global agent config.
- `run-claude`: gọi Claude implementer cho cycle hiện hành; lưu checkpoint/log theo attempt và resume phiên bị gián đoạn khi có session ID.
- `run-claude` đồng thời bắt buộc skill hash, handoff skill evidence và các deterministic implementation checks.
- `run-task`: tự động lặp implement → validate → review → request-fixes; tự chuyển validation/
  contract failure thành structured checklist + fix request cho attempt sau và dừng ở user
  acceptance hoặc blocker bên ngoài thật sự.
- `validate`: chạy command deterministic.
- `run-codex-review`: chạy wiring/acceptance evidence gates rồi gọi Codex read-only với review skill bắt buộc.
- `request-fixes`: tạo danh sách fix theo `review.fail_on` và acceptance/validation bị thiếu,
  kèm sidecar máy đọc được `correction-scope-review-<cycle>.json` (finding, acceptance
  criteria, slice bị ảnh hưởng khi xác định được, risk category, có cần full-plan fallback
  hay không và lý do). `run-claude` dùng sidecar này để giới hạn phiên correction vào đúng
  slice bị ảnh hưởng (+ dependency trực tiếp) thay vì luôn mở lại toàn bộ plan; correction
  nhạy cảm (auth/security/migration/...) hoặc không xác định được slice luôn fallback về
  full-plan, lý do được ghi vào `state.yaml` và metrics.
- `finalize-task`: sinh báo cáo theo `report.*`, từ chối dry-run validation và chuyển task đạt gate sang `awaiting_user_acceptance`.
- `accept-task`: chỉ nhận report đã finalize cho đúng implementation/change/review cycle; ghi
  xác nhận và report theo transaction có rollback nếu tái tạo report thất bại.
- `request-change`: tạo correction hoặc post-completion requirement-change cycle, lưu baseline và tái sử dụng worktree đã đăng ký.
- `update-knowledge`: lập kế hoạch hoặc áp dụng update sau khi task đã được người dùng xác nhận; `accept-task` tự gọi `--apply --strict` để áp dụng toàn bộ entry đã duyệt và rollback acceptance nếu preflight thất bại.
- `consolidate-requirements`: khi task ở trạng thái `completed`, archive draft/manifest cũ
  (nếu có), gọi Claude soạn một `task.md` gộp các requirement addendum của các cycle đã
  được chấp nhận thành `requirements-consolidation-draft.md`, kèm
  `requirements-consolidation-manifest.json` ghi sha256 của `task.md` nguồn, từng addendum
  và draft sinh ra; không tự ghi đè `task.md`.
- `apply-requirements-consolidation`: yêu cầu cả draft lẫn manifest, đối chiếu lại toàn bộ
  sha256/`task_id`/cycle trong manifest với trạng thái hiện tại — từ chối áp dụng nếu
  `task.md`, addendum nguồn hoặc chính draft đã bị sửa, hoặc manifest thuộc cycle khác. Nếu
  hợp lệ: yêu cầu `--approved-by` không rỗng, backup `task.md` cũ cùng draft/manifest vào
  `task-md-history/` (giữ nguyên để audit, không xóa), ghi đè `task.md` và đánh dấu cycle đã
  gộp trong `state.yaml`.
- `rebuild-indexes`: sinh chỉ mục trạng thái.
- `metrics`: tổng hợp attempt, resume, duration và token usage do CLI cung cấp.

Chạy `./ai/bin/ai --help` để xem command.

## Token-efficient orchestration

`ai task run` chạy đúng một execution-plan slice trong mỗi Claude session mới,
dùng quick validation giữa các slice và chỉ chạy full validation trước review.
Handoff slice thành công dùng trạng thái `implementation_ready_for_validation`; rerun/restart
tự tiếp tục ở validation. Status của execution-plan thuộc quyền orchestrator và mọi thay đổi
status do implementer tạo sẽ bị khôi phục trước khi pipeline tiếp tục.
Session nhận compact slice-context bundle và không bị workflow áp đặt giới hạn số
agent turn. Các ngưỡng context được cấu hình bằng `AI_WARN_CONTEXT_TOKENS` và
`AI_MAX_CONTEXT_TOKENS`.

Review tự dùng delta mode cho correction không nhạy cảm; auth, security, API
contract, database, migration, transaction và concurrency luôn được nâng lên full.
Delta chỉ được chọn khi review liền trước là một full review (không bao giờ có hai
delta liên tiếp); delta không bao giờ tự authorize report/user acceptance — luôn cần
một full review đạt `pass` theo sau. Delta pass luôn được theo sau bởi một final full
review. Có thể ép mode qua `ai task review <ID> --mode full|delta`.

Correction sau review chỉ mở lại đúng slice bị finding ảnh hưởng (+ dependency trực
tiếp) khi `correction-scope-review-<cycle>.json` xác định được rõ ràng; slice khác giữ
nguyên evidence cũ. Không xác định được, hoặc finding thuộc nhóm nhạy cảm, thì fallback
về toàn bộ execution plan.

`ai metrics <ID>` báo input, cache creation/read, output, turns, cost và tổng theo
slice — cho cả Claude (implement) và Codex (review, qua `codex exec --json`). Fix
request chỉ giữ đoạn lỗi giới hạn và trỏ về artifact đầy đủ; validation summary chỉ
giữ output đầy đủ (12000 ký tự) cho command thất bại, command đã pass chỉ giữ tail
ngắn.

`implement`/`review` chỉ đọc `task.md` cùng requirement addendum của các cycle
*chưa* được gộp (`requirements_consolidated_through_cycle` trong `state.yaml`);
`report` vẫn liệt kê toàn bộ lịch sử addendum để giữ audit trail đầy đủ. Dùng
`consolidate-requirements` + `apply-requirements-consolidation` để gộp addendum đã
chấp nhận vào `task.md`, tránh mỗi session phải đọc lại toàn bộ lịch sử requirement
của task nhiều cycle.
