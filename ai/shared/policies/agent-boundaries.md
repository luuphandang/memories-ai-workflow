# Agent Boundaries

## Claude

Được sửa source trong worktree writable đã khai báo. Không được quản lý Git/worktree, tự accept task hoặc sửa knowledge base trực tiếp.

## Codex

Chỉ review, không sửa source. Không được xem technical pass là user acceptance.

## Script

Được tạo hồ sơ, lock context, chạy command, lưu baseline, cập nhật trạng thái và báo cáo. Không tự tạo/xóa worktree, checkout branch, commit hoặc push.

## Người dùng/developer

- Tạo và quản lý Git worktree.
- Điền yêu cầu và requirement addendum.
- Kiểm tra kết quả thực tế.
- Quyết định accept hoặc tạo change cycle.
- Review knowledge update trước khi apply.
