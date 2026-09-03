# Task Lifecycle

```text
backlog → ready → prepared → implementing → implementation_ready_for_validation → validating → reviewing
                                              ↑             │
                                              └─ changes_requested_by_codex
                                              └─ changes_requested_by_validation
reviewing + gates pass → awaiting_user_acceptance
awaiting_user_acceptance ├─ accept → completed
                         └─ request correction → changes_requested_by_user
completed ── request requirement change ──→ reopened
reopened/changes_requested_by_user → prepared → implementing → ...
Any active state → interrupted (có thể retry/resume) | needs_input | blocked | failed
```

## Điều kiện chuyển trạng thái

- `ready`: yêu cầu tối thiểu và quan hệ Jira hợp lệ.
- `prepared`: context đã khóa hash, worktree hợp lệ, base/current SHA đã ghi.
- `implementing`: Claude đang thay đổi code.
- `implementation_ready_for_validation`: handoff của slice hiện hành đã hợp lệ; orchestrator
  phải resume từ validation và tuyệt đối không gọi lại implementer cho cùng handoff.
- `validating`: validation deterministic đang chạy.
- `reviewing`: có handoff và kết quả validation để Codex đánh giá.
- `changes_requested_by_codex`: Codex có finding cần sửa.
- `changes_requested_by_validation`: deterministic validation đã tạo checklist lỗi và chờ implementer sửa/retest.
- `awaiting_user_acceptance`: validation pass, Codex pass, báo cáo đã sinh nhưng người dùng chưa xác nhận.
- `changes_requested_by_user`: người dùng yêu cầu chỉnh sửa trước khi nghiệm thu.
- `completed`: người dùng đã xác nhận vòng hiện hành.
- `reopened`: task completed được mở lại do thay đổi yêu cầu, tiếp tục trên worktree đã đăng ký.
- `interrupted`: phiên implement bị ngắt do timeout, quota hoặc session limit; chạy lại `implement` để resume session nếu có, nếu không thì phục hồi từ checkpoint và Git diff.
- `needs_input`: thiếu thông tin có ảnh hưởng đáng kể, cần phản hồi người dùng.
- `blocked`: thiếu quyền/phụ thuộc hoặc vượt số vòng review cho phép.
- `failed`: lỗi pipeline hoặc hồ sơ task không hợp lệ.

`review_cycle` đếm mọi lần gọi reviewer và được reset khi bắt đầu change cycle mới;
`review_cycles_total` giữ tổng lịch sử. `fix_cycle` chỉ tăng khi một fix request thực sự được
tạo và là counter dùng cho `review.max_fix_cycles` (fallback tương thích: `max_cycles`).
