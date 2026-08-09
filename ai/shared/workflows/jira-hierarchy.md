# Jira Hierarchy: Epic → Story → Task

## Epic

Mô tả mục tiêu kinh doanh lớn, phạm vi tổng quát và các story con. Epic thường không trực tiếp chạy pipeline code nếu chưa có worktree.

## Story

Mô tả một capability có giá trị cho người dùng/hệ thống, thuộc một epic. Story có thể được triển khai trực tiếp hoặc chia thành task.

## Task

Đơn vị thực thi kỹ thuật nhỏ nhất trong workflow này. Task phải có scope, acceptance criteria, repo/worktree và validation rõ ràng.

## Quan hệ bắt buộc

- `story.parent_id` trỏ đến epic.
- `task.parent_id` trỏ đến story.
- `task.epic_id` trỏ trực tiếp đến epic để truy vấn nhanh.
- ID và quan hệ Jira thật: `[BỔ SUNG THEO TÍNH NĂNG]`.
- Quy tắc mapping loại issue tùy chỉnh của công ty: chưa thiết lập trong dự án hiện tại — dự án hiện dùng đúng 3 loại mặc định Epic/Story/Task như mô tả ở trên, chưa tích hợp với 1 Jira instance thật có custom issue type nào khác.
