# MEMORIES-0002 — Requirement Addendum cycle 1

## Quan hệ với yêu cầu trước

Tài liệu này bổ sung cho `task.md` và các addendum cycle trước. Khi có xung đột được mô tả rõ, nội dung của cycle này có ưu tiên cao hơn.

## Phạm vi thay đổi

- [x] Loại bỏ toàn bộ yêu cầu frontend ra khỏi epic MEMORIES-0002. Epic này từ cycle 1 trở đi là **backend-only**.
- [x] `task.md` mục 18 "Frontend integration" (toàn bộ checklist) không còn là deliverable bắt buộc của epic này.
- [x] AC36 và AC39 được thu hẹp phạm vi — xem mục "Acceptance criteria bổ sung/thay thế" bên dưới.
- [x] Slice `frontend-integration` trong execution plan bị loại bỏ khi `prepare-plan` chạy lại cho cycle này.

## Acceptance criteria bổ sung/thay thế

1. **AC36 (thay thế)**: Swagger/OpenAPI backend phản ánh đúng các endpoint auth/account/user-profile hiện có (không còn yêu cầu "API client frontend được cập nhật hoặc regenerate" — không có frontend trong scope).
2. **AC39 (thay thế)**: Mock authentication được xóa khỏi **backend** (chỉ backend — vế "và frontend" của AC39 gốc không còn áp dụng).
3. Không có acceptance criteria mới nào được thêm cho frontend trong cycle này hay các cycle sau của epic MEMORIES-0002.

## Nội dung bị thay thế hoặc không còn áp dụng

- Toàn bộ `task.md` mục 18 "Frontend integration" (dòng ~706-747): không còn áp dụng cho epic này.
- Phần "và frontend" trong AC39 gốc (dòng 905): không còn áp dụng.
- Phần "API client frontend" trong AC36 gốc (dòng 899): không còn áp dụng, thay bằng yêu cầu Swagger/OpenAPI backend ở trên.
- Bất kỳ review finding nào ở cycle trước liên quan riêng tới "Frontend integration" (vd. slice `frontend-integration` trong review.json/execution-plan.json cycle 1) không còn cần khắc phục.

## Ngoài phạm vi của cycle này

- Toàn bộ frontend (login form, API client, token storage trên client...) — chuyển sang epic/task khác trong tương lai, không thuộc MEMORIES-0002.
- Các mục vốn đã "Out of scope" trong `task.md` gốc (OAuth/OTP/MFA/passkey/Role-Permission CRUD UI/Customer-Staff model...) tiếp tục ngoài phạm vi như cũ.

## Ghi chú kỹ thuật

- Vị trí source/module liên quan: không có thay đổi source code bắt buộc từ addendum này — đây thuần túy là thu hẹp phạm vi requirement/AC, không phải fix bug.
- Constraint kỹ thuật đã xác minh: `task.yaml` chỉ đăng ký worktree `backend` (không có `frontend`) — nhất quán với quyết định backend-only này.
