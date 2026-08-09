# MEMORIES-0002 — Requirement Addendum cycle 2

## Quan hệ với yêu cầu trước

Tài liệu này bổ sung cho `task.md` và các addendum cycle trước. Khi có xung đột được mô tả rõ, nội dung của cycle này có ưu tiên cao hơn.

## Phạm vi thay đổi

- [x] Bổ sung API đăng ký tài khoản công khai `POST /auth/register` vào module `identity-access`, đặt trong `AuthController` (cùng nhóm với `/auth/login`, `/auth/refresh`, `/auth/logout`).
- [x] API đăng ký không có guard xác thực (route công khai/unauthenticated), nhưng vẫn có rate limit như `/auth/login`.
- [x] API đăng ký chỉ tạo Account cho portal `PUBLIC`, chỉ hỗ trợ provider `LOCAL`.
- [x] API đăng ký tái sử dụng luồng transaction tạo Account đã mô tả ở `task.md` mục 8 (normalize phone → check trùng identifier → hash password → tạo Account → tạo LOCAL AuthIdentity → tạo UserProfile → gán default role), không định nghĩa lại luồng riêng.
- [x] Sau khi đăng ký thành công, hệ thống tự động đăng nhập: phát access token trong response body và set refresh token cookie `HttpOnly`, tương đương kết quả `POST /auth/login` với `portal: "PUBLIC"` cho Account vừa tạo.
- [x] `execution-plan.json` cần có slice/task tương ứng cho `POST /auth/register` khi `prepare-plan` chạy lại cho cycle này.

## Đặc tả API đăng ký (`POST /auth/register`)

### Route

```text
POST /auth/register
```

- Không guard xác thực (`@Public()` hoặc tương đương theo convention hiện tại của `AuthController`).
- Áp dụng rate limit tương đương `/auth/login` (mục 19 của `task.md`).

### Request body

```json
{
  "phone": "0912345678",
  "password": "...",
  "fullName": "Nguyễn Văn A",
  "email": "user@example.com"
}
```

- `phone`: bắt buộc. Chuẩn hóa theo cùng quy tắc phone normalization đã dùng cho login (mục 9 `task.md`), hỗ trợ default region Việt Nam qua configuration.
- `password`: bắt buộc, tuân thủ password policy tập trung (mục 19 `task.md`).
- `fullName`: bắt buộc (UserProfile yêu cầu `fullName` theo mục 4 và mục 19 `task.md`).
- `email`: tùy chọn (nullable theo mục 4 `task.md`); nếu có, validate định dạng và normalize lowercase trước khi lưu; email không phải login identifier.
- Client **không được truyền**: `portal`, `role`, `permission`, `accountId`, hoặc bất kỳ audit/system field nào. Server luôn tạo Account cho portal `PUBLIC` và gán default role được cấu hình (`PUBLIC_USER` theo mục 12 `task.md`), không cho phép override.

### Luồng xử lý

1. Normalize số điện thoại.
2. Kiểm tra `phone` (identifier LOCAL) đã tồn tại chưa; nếu trùng, trả lỗi nghiệp vụ "Phone đã tồn tại" (tái sử dụng application error đã định nghĩa ở mục 8 `task.md`).
3. Hash password.
4. Trong một transaction:
   - Tạo Account với `status = ACTIVE`.
   - Tạo LOCAL AuthIdentity (`identifier` = phone đã normalize, `passwordHash`).
   - Tạo UserProfile (`fullName`, `email` nếu có).
   - Gán default role `PUBLIC_USER` (có `portal.public.access`) qua `AccountRole`.
5. Nếu bất kỳ bước nào thất bại, rollback toàn bộ transaction (không để tồn tại Account thiếu AuthIdentity/UserProfile/role — theo đúng ràng buộc mục 8 `task.md`).
6. Sau khi transaction thành công, thực hiện portal authorization cho `PUBLIC` (Account vừa tạo phải có `portal.public.access` qua default role) và phát hành session/token giống luồng login: tạo refresh session gắn với portal `PUBLIC`, trả access token trong response body, set refresh token cookie `HttpOnly`.

### Response

- Không trả `passwordHash` hoặc bất kỳ credential nào.
- Không trả ORM entity trực tiếp.
- Body thành công chứa tối thiểu: thông tin Account (không gồm credential), `userProfileId`, và access token — cùng cấu trúc với response của `POST /auth/login` cho portal `PUBLIC`.

### Ràng buộc bảo mật (kế thừa mục 19 `task.md`)

- Không mass assignment các trường hệ thống (status, role, permission, audit fields).
- Không log credential (phone không bị coi là credential nhưng password/passwordHash tuyệt đối không log).
- Refresh cookie tuân thủ HttpOnly/Secure/SameSite/Path/domain như luồng login.
- Không đưa thông tin cá nhân không cần thiết vào JWT.

## Acceptance criteria bổ sung/thay thế

Các mục sau bổ sung thêm vào danh sách acceptance criteria của `task.md` (tiếp theo AC40), áp dụng cùng mức độ bắt buộc như các AC gốc:

1. **AC41**: Tồn tại API công khai `POST /auth/register` cho phép người dùng chưa xác thực tự tạo Account mà không cần quyền quản trị.
2. **AC42**: API đăng ký chỉ tạo Account cho portal `PUBLIC`; không có cách nào qua API đăng ký để tạo Account có `portal.admin.access`.
3. **AC43**: API đăng ký chỉ hỗ trợ provider `LOCAL`; client không thể chỉ định provider khác.
4. **AC44**: API đăng ký tái sử dụng transaction tạo Account ở mục 8 `task.md` — Account, LOCAL AuthIdentity, UserProfile và default role được tạo trong cùng một transaction; lỗi ở bất kỳ bước nào đều rollback toàn bộ.
5. **AC45**: Client gọi API đăng ký không thể truyền `portal`, `role`, `permission`, `accountId` hoặc audit fields; các giá trị này luôn do server quyết định.
6. **AC46**: Đăng ký với `phone` đã tồn tại trả về lỗi nghiệp vụ rõ ràng, không tạo Account trùng, không rollback một phần.
7. **AC47**: API đăng ký áp dụng đầy đủ validation của mục 19 `task.md`: phone/password bắt buộc, password policy, fullName bắt buộc, email validate khi có, giới hạn độ dài string, rate limit.
8. **AC48**: Sau khi đăng ký thành công, response trả access token và set refresh token cookie `HttpOnly`, hiệu lực tương đương kết quả đăng nhập thành công cho portal `PUBLIC` (không cần gọi thêm `/auth/login`).
9. **AC49**: Response của API đăng ký không chứa `passwordHash` hoặc bất kỳ credential nào; không trả ORM entity trực tiếp.
10. **AC50**: Swagger/OpenAPI được cập nhật để mô tả `POST /auth/register`, bao gồm request/response schema và các mã lỗi.
11. **AC51**: Có unit test cho use case đăng ký (hoặc use case tạo Account dùng chung nếu tái sử dụng), integration test cho transaction đăng ký, và E2E test: đăng ký thành công → tự động có token hợp lệ cho portal PUBLIC → đăng ký với phone trùng bị từ chối.

## Nội dung bị thay thế hoặc không còn áp dụng

- Không có nội dung nào của `task.md` gốc hoặc `changes/cycle-001/requirement-addendum.md` bị thay thế. Đây là bổ sung thuần túy (điền vào khoảng trống yêu cầu), không mâu thuẫn với quyết định backend-only đã chốt ở cycle 1.
- Mục 16 `task.md` ("Account CRUD API") giữ nguyên: `POST /accounts` tiếp tục là thao tác admin-only, có permission `account.create`, không bị thay thế hay gộp chung với API đăng ký công khai.

## Ngoài phạm vi của cycle này

- Xác minh số điện thoại (OTP) khi đăng ký — vẫn nằm trong "Out of scope" của `task.md` gốc.
- Đăng ký qua Google/Apple/Facebook — vẫn ngoài phạm vi epic theo mục 11 và "Out of scope" của `task.md` gốc.
- Xác minh email, quên mật khẩu qua SMS/email — vẫn ngoài phạm vi theo `task.md` gốc.
- Đăng ký tài khoản ADMIN/Staff qua API công khai — không được phép, ngoài phạm vi vĩnh viễn (chỉ tạo qua `POST /accounts` bởi quản trị viên có quyền).
- Toàn bộ frontend (bao gồm form đăng ký) — vẫn ngoài phạm vi theo `changes/cycle-001/requirement-addendum.md` (epic backend-only).

## Ghi chú kỹ thuật

- Vị trí source/module liên quan: `libs/modules/identity-access/src/presentation/http/auth.controller.ts` (thêm route `register`), `libs/modules/identity-access/src/application/` (tái sử dụng hoặc mở rộng use case tạo Account đã có ở mục 8 `task.md`), `libs/modules/identity-access/src/presentation/http/account.controller.ts` (không đổi — vẫn admin-only).
- Constraint kỹ thuật đã xác minh: `account.controller.ts` (`POST /accounts`, dòng ~64-67) hiện áp `@RequirePortal('ADMIN')` + `@RequirePermissions('account.create')` ở toàn bộ route; `auth.controller.ts` hiện chỉ có `login`/`refresh`/`logout`, không có `register` — xác nhận qua đọc trực tiếp source trong `worktrees/MEMORIES-0002/backend/libs/modules/identity-access/src/presentation/http/`.
