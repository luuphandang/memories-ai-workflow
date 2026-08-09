# User Acceptance Workflow

Codex `pass` chỉ xác nhận chất lượng kỹ thuật theo bộ yêu cầu hiện hành. Nó không thay thế quyết định nghiệm thu của người dùng.

## Luồng chuẩn

```text
Claude implement → validation → Codex pass → report
→ awaiting_user_acceptance
   ├─ user accept → completed → knowledge update có thể áp dụng
   └─ user requests correction → changes_requested_by_user
      → Claude sửa → validation → Codex review → awaiting_user_acceptance
```

## Nguyên tắc

- `completed` chỉ được thiết lập bằng lệnh `ai task accept`.
- Trước khi xác nhận, người dùng có thể tạo change cycle loại `correction`.
- Kết quả cũ phải được lưu trong `changes/cycle-NNN/baseline/` trước khi chạy vòng mới.
- Review/validation cũ không được dùng làm bằng chứng cho vòng yêu cầu mới.
- Knowledge base chỉ được áp dụng sau khi người dùng xác nhận vòng hiện hành.
