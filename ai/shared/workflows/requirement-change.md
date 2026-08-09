# Requirement Change Workflow

Quy trình này xử lý hai loại thay đổi mà không làm mất lịch sử yêu cầu.

## Loại 1 — Correction trước khi nghiệm thu

Dùng khi Claude đã triển khai, validation đã chạy và Codex đã review nhưng người dùng phát hiện kết quả chưa chính xác.

```text
awaiting_user_acceptance
→ request-change(kind=correction)
→ changes/cycle-NNN/{user-request,requirement-addendum}
→ prepare-context → implement → validate → review → report
→ awaiting_user_acceptance
```

## Loại 2 — Requirement change sau khi đã completed

Dùng khi người dùng đã xác nhận task hoàn thành nhưng yêu cầu thay đổi vì nghiệp vụ, thiết kế, tích hợp hoặc điều kiện bên ngoài.

```text
completed
→ request-change(kind=requirement_change)
→ kiểm tra lại đúng worktree path + branch đã đăng ký
→ reopened (không tạo worktree mới)
→ prepare-context → implement → validate → review → report → accept
```

## Thứ tự ưu tiên yêu cầu

1. Policy an toàn.
2. `task.md` ban đầu.
3. Các `requirement-addendum.md` theo thứ tự cycle tăng dần.
4. Addendum mới hơn ghi đè nội dung cũ khi xung đột được nêu rõ.
5. Source code thực tế chỉ quyết định cách triển khai, không tự thay đổi nghiệp vụ.

## Hồ sơ mỗi cycle

```text
changes/cycle-NNN/
├── metadata.yaml
├── user-request.md
├── requirement-addendum.md
├── attachments/README.md
└── baseline/
    ├── implementation.json
    ├── review.json
    ├── final-report.md
    ├── acceptance.yaml
    └── validation/
```

`user-request.md` lưu lời phản hồi và bằng chứng. `requirement-addendum.md` là yêu cầu chuẩn hóa mà Claude và Codex bắt buộc dùng.
