# Memories Frontend Index

- `overview.md` — mục tiêu và tech stack
- `architecture.md` — kiến trúc/UI state boundary
- `source-map.md` — vị trí source quan trọng
- `conventions.md` — coding convention
- `commands.yaml` — command deterministic
- `testing.md` — chiến lược test
- `ui-rules.md` — design system/accessibility
- `api-client-rules.md` — API/data-fetching rules
- `known-issues.md` — vấn đề đã biết

## AuthProvider (packages/auth)

`AuthContextValue` có `loginWithPhone(phone, password, portal)` và `registerLocal(input)` bên cạnh `login(email, password)` cũ (giữ lại chỉ cho `apps/admin-web`, vốn có sự lệch hợp đồng backend riêng, ngoài phạm vi sửa của MEMORIES-0005). `isAuthenticated` được suy ra từ việc có access token hay không, không dựa vào object `user` — response thật của `/auth/login`, `/auth/register`, `/auth/refresh` đều không trả `user`.

## packages/ui: Popover/PopoverItem

Primitive menu neo (anchored), không portal full-screen như `Dialog` — dùng khi cần menu nhỏ đặt cạnh trigger (ví dụ account menu) thay vì overlay toàn màn hình. Parent bắt buộc phải có `position: relative`.
