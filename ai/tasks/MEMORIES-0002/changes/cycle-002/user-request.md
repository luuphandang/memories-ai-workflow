# MEMORIES-0002 — Yêu cầu thay đổi cycle 2

## Loại thay đổi

`correction`

## Người dùng phát hiện/yêu cầu

Người dùng phát hiện hệ thống xác thực hiện tại (cả `task.md` gốc lẫn implementation trong worktree) không có API đăng ký tài khoản công khai (public self-service registration). Yêu cầu bổ sung mô tả đầy đủ cho API đăng ký vào tài liệu hướng dẫn của epic MEMORIES-0002.

## Kết quả hiện tại

`task.md` chỉ mô tả hai đường tạo Account:

- Mục 8 "Transaction tạo Account" định nghĩa luồng tạo Account dùng chung (normalize phone → check trùng → hash password → tạo Account → tạo LOCAL AuthIdentity → tạo UserProfile → gán default role), nhưng không gắn với một API endpoint cụ thể nào.
- Mục 16 "Account CRUD API" chỉ định nghĩa `POST /accounts` như một thao tác quản trị: yêu cầu authenticated + `@RequirePermissions('account.create')` + `@RequirePortal('ADMIN')`.

Đối chiếu với implementation thực tế trong `worktrees/MEMORIES-0002/backend/libs/modules/identity-access/src/presentation/http/`:

- `account.controller.ts` (`@Controller('accounts')`) áp guard `JwtAuthGuard`, `PortalGuard`, `PermissionsGuard` và `@RequirePortal('ADMIN')` ở class-level; route `POST /accounts` (dòng ~64-67) yêu cầu permission `account.create`. Đây là thao tác admin tạo Account hộ người khác, không phải self-registration.
- `auth.controller.ts` (`@Controller('auth')`) chỉ có ba route: `POST /auth/login` (không guard, dùng để đăng nhập), `POST /auth/refresh` (guard `OriginGuard`), `POST /auth/logout` (guard `JwtAuthGuard`). Không có route `register`/`signup`.
- Grep toàn bộ `identity-access/src` cho `register|signup|sign-up` chỉ khớp chuỗi lỗi "already registered" trong `create-account.use-case.ts` — không có controller/route/DTO nào cho đăng ký công khai.

Kết luận: một người dùng ẩn danh (chưa có Account) hiện **không có cách nào tự tạo tài khoản**. Cách duy nhất để có Account là được một quản trị viên đã có quyền `account.create` tạo hộ qua `POST /accounts` trên portal ADMIN — không phù hợp với luồng người dùng public tự đăng ký trên `public-web`.

## Kết quả mong muốn

Bổ sung vào `task.md` (thông qua addendum của cycle này) mô tả đầy đủ một API đăng ký công khai `POST /auth/register`, cho phép người dùng chưa xác thực tự tạo Account cho portal `PUBLIC`, tái sử dụng luồng transaction đã có ở mục 8, và tuân thủ toàn bộ validation/security đã định nghĩa ở mục 19. Sau khi đăng ký thành công, hệ thống tự động đăng nhập (phát access token trong response + set refresh token cookie), tương đương kết quả của `POST /auth/login` với `portal: "PUBLIC"`. Chi tiết đầy đủ xem `requirement-addendum.md` của cycle này.

## Lý do thay đổi

Đây là một khoảng trống trong yêu cầu gốc (không phải lỗi triển khai sai): `task.md` mô tả luồng login bằng phone/password và luồng admin tạo Account, nhưng bỏ sót luồng người dùng public tự đăng ký — vốn là tiền đề bắt buộc để luồng login public có Account để đăng nhập trong thực tế.

## Bằng chứng

- Screenshot/video/log/tài liệu: không áp dụng — phát hiện qua rà soát trực tiếp `task.md` và source code trong `worktrees/MEMORIES-0002/backend/libs/modules/identity-access/src/presentation/http/account.controller.ts` và `auth.controller.ts`.
- Cách tái hiện: gọi bất kỳ route nào dưới `/accounts` mà không có JWT hợp lệ + permission `account.create` sẽ bị từ chối; không tồn tại route nào khác để tạo Account mà không cần quyền quản trị.

## Mức độ ảnh hưởng

- `task.md`: cần bổ sung mô tả API đăng ký (mục mới hoặc mở rộng mục 9/16) và các acceptance criteria liên quan — xem `requirement-addendum.md`.
- `execution-plan.json`: cần thêm slice/task cho `POST /auth/register` khi `prepare-plan` chạy lại cho cycle này.
- Source code: cần thêm route, DTO, use case (hoặc tái sử dụng use case tạo Account ở mục 8) trong module `identity-access` — thuộc phạm vi triển khai của cycle này, không thực hiện trong tài liệu này.
- Không ảnh hưởng tới quyết định backend-only đã chốt ở `changes/cycle-001/requirement-addendum.md`.
