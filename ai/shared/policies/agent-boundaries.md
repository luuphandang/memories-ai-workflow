# Agent Boundaries

## Claude

Được sửa source trong worktree writable đã khai báo. Không được quản lý Git/worktree, tự accept task hoặc sửa knowledge base trực tiếp.

## Codex

Chỉ review, không sửa source. Không được xem technical pass là user acceptance.

## Script

Được tạo hồ sơ, lock context, chạy command, lưu baseline, cập nhật trạng thái và báo cáo. Không tự tạo/xóa worktree, checkout branch, commit hoặc push.

Integration layer là ngoại lệ hẹp: được tạo và xóa clone tạm trong thư mục temporary để
kiểm tra combined tree trên exact target SHA. Clone này không phải registered task worktree,
không được push/merge vào repository nguồn và phải được cleanup sau validation.

## Người dùng/developer

- Tạo và quản lý Git worktree.
- Điền yêu cầu và requirement addendum.
- Kiểm tra kết quả thực tế.
- Quyết định accept hoặc tạo change cycle.
- Review knowledge update trước khi apply.
