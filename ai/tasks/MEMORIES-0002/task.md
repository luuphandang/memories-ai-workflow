# MEMORIES-0002: [AUTH] Implement Account, User Profile and Portal Authorization Foundation

## Jira

* Type: `epic`
* Parent: `-`
* Epic: `MEMORIES-0002`

## Goal

Triển khai nền tảng quản lý danh tính, xác thực và phân quyền dùng chung cho toàn bộ hệ thống LUUMORY, thay thế dữ liệu đăng nhập mock hiện tại.

Hệ thống phải đáp ứng các mục tiêu:

* Xây dựng `Account` làm định danh đăng nhập trung tâm.
* Xây dựng `UserProfile` để lưu thông tin cá nhân dùng chung cho mọi tài khoản.
* Sử dụng cùng một Account để đăng nhập vào:

  * Website public.
  * Website admin.
* Chuyển đăng nhập từ `email + password` sang `phone + password`.
* Kiểm tra permission để xác định Account có được truy cập từng portal hay không.
* Giữ nguyên cơ chế JWT hiện tại:

  * Access token lưu trong memory.
  * Refresh token lưu trong cookie `HttpOnly`.
* Chuẩn bị kiến trúc để hỗ trợ đăng nhập bằng Google, Apple, Facebook trong tương lai.
* Chuẩn bị nền tảng RBAC gồm Role và Permission.
* Triển khai API CRUD cho Account và UserProfile.
* Chuẩn hóa audit metadata trên các entity.
* Sử dụng request context để lưu trữ actor, permission và metadata của request.
* Tuân thủ architecture, design pattern, module boundary và coding convention hiện tại của hệ thống.

Kết quả của epic phải loại bỏ hoàn toàn dữ liệu xác thực mock và tạo nền tảng dùng chung cho cả người dùng public, nhân viên và quản trị viên.

## Background

LUUMORY có hai ứng dụng sử dụng chung hệ thống xác thực:

```text
public-web
admin-web
```

Hai ứng dụng không sử dụng hai loại Account riêng biệt.

Một Account có thể:

* Chỉ truy cập website public.
* Chỉ truy cập website admin.
* Truy cập cả hai website.
* Không được truy cập portal nào nếu Account bị khóa hoặc thiếu quyền cần thiết.

Khả năng truy cập từng portal được xác định bằng permission.

Ví dụ:

```text
portal.public.access
portal.admin.access
```

Account chỉ đại diện cho danh tính, trạng thái đăng nhập và quyền truy cập hệ thống.

Thông tin cá nhân không thuộc Account mà được lưu trong `UserProfile`.

`Customer` không được sử dụng làm hồ sơ chung của tất cả tài khoản vì:

* Người dùng đăng nhập public chưa chắc đã phát sinh nghiệp vụ khách hàng.
* Nhân viên và quản trị viên không phải là Customer.
* Một người có thể có Account và UserProfile nhưng chưa có Customer.
* Customer chỉ được tạo khi phát sinh nghiệp vụ thương mại, CRM hoặc thành viên.

Mô hình tổng thể:

```text
Account
   │
   ├── AuthIdentity
   ├── RefreshSession
   ├── AccountRole
   │
   └── UserProfile
           │
           ├── Customer
           └── Staff
```

Trong phạm vi epic này chỉ triển khai:

```text
Account
AuthIdentity
UserProfile
RefreshSession
Role
Permission
AccountRole
RolePermission
```

`Customer` và `Staff` là các model nghiệp vụ mở rộng, không thuộc phạm vi triển khai hiện tại.

## Current system

Hệ thống hiện tại đã có:

* Cấu trúc project backend và frontend.
* Một số shared abstractions cho Entity, Repository và Use Case.
* Dữ liệu người dùng mock.
* Đăng nhập mock bằng `email + password`.
* Cơ chế phát hành JWT.
* Access token lưu trong memory phía client.
* Refresh token lưu trong cookie.
* Luồng refresh access token cơ bản.
* Auth guard hoặc middleware nền tảng.

Hệ thống hiện chưa có:

* Account domain model chính thức.
* UserProfile domain model chính thức.
* AuthIdentity abstraction.
* Database migration cho Account và UserProfile.
* Xác thực bằng số điện thoại.
* Phone normalization.
* Portal authorization.
* Role và Permission foundation hoàn chỉnh.
* Request context dùng chung.
* Audit metadata tự động.
* API CRUD Account và UserProfile.
* Cơ chế revoke session khi Account bị khóa hoặc xóa.
* Test đầy đủ cho authentication và authorization.

## Scope

### 1. Module boundary

* [ ] Sử dụng module `identity-access` để quản lý:

  * Account.
  * AuthIdentity.
  * Authentication.
  * RefreshSession.
  * Role.
  * Permission.
  * AccountRole.
  * RolePermission.
  * Portal authorization.
* [ ] Sử dụng module `user-profiles` để quản lý UserProfile.
* [ ] Không đặt UserProfile trong module `customers`.
* [ ] Module `customers` chỉ được sử dụng cho nghiệp vụ khách hàng trong tương lai.
* [ ] Module `staff` chỉ được sử dụng cho nghiệp vụ nhân viên trong tương lai.
* [ ] Module khác chỉ truy cập Account và UserProfile thông qua public API hoặc application contract.
* [ ] Không sử dụng TypeORM relation trực tiếp xuyên module.

Cấu trúc đề xuất:

```text
libs/modules/
├── identity-access/
│   └── src/
│       ├── domain/
│       │   ├── accounts/
│       │   ├── auth-identities/
│       │   ├── sessions/
│       │   ├── roles/
│       │   └── permissions/
│       ├── application/
│       ├── infrastructure/
│       └── presentation/
│
├── user-profiles/
│   └── src/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       └── presentation/
│
├── customers/
└── staff/
```

### 2. Account domain model

* [ ] Khai báo `Account` aggregate/entity trong module `identity-access`.
* [ ] Account kế thừa Entity hoặc AggregateRoot abstraction hiện tại.
* [ ] Account có tối thiểu:

  * `id`.
  * `status`.
  * `tokenVersion`.
  * Audit metadata.
* [ ] Account status hỗ trợ tối thiểu:

  * `ACTIVE`.
  * `INACTIVE`.
  * `LOCKED`.
* [ ] Account không chứa thông tin hồ sơ cá nhân.
* [ ] Account không chứa email hoặc địa chỉ.
* [ ] Account không trả credential trong API response.
* [ ] Account inactive, locked hoặc deleted không được đăng nhập.
* [ ] Account bị vô hiệu hóa không được refresh token.

### 3. AuthIdentity model

* [ ] Khai báo `AuthIdentity` trong module `identity-access`.
* [ ] Một Account có thể có nhiều AuthIdentity.
* [ ] AuthIdentity có tối thiểu:

  * `id`.
  * `accountId`.
  * `provider`.
  * `identifier`.
  * `providerSubject`.
  * `passwordHash`.
  * `verifiedAt`.
  * Audit metadata.
* [ ] Provider hỗ trợ:

  * `LOCAL`.
  * `GOOGLE`.
  * `APPLE`.
  * `FACEBOOK`.
* [ ] Chỉ triển khai đầy đủ provider `LOCAL` trong epic này.
* [ ] Với provider LOCAL:

  * `identifier` là số điện thoại đã normalize.
  * `passwordHash` là bắt buộc.
* [ ] Với social provider:

  * `providerSubject` được dùng để định danh tài khoản phía nhà cung cấp.
  * Không thêm các cột riêng như `googleId`, `facebookId`, `appleId` vào Account.
* [ ] Không lưu plain text password.
* [ ] Không trả passwordHash qua API.
* [ ] Không ghi credential vào log.
* [ ] Có unique constraint phù hợp cho:

  * `provider + identifier`.
  * `provider + providerSubject`.

Quan hệ:

```text
Account 1 ───── n AuthIdentity
```

### 4. UserProfile domain model

* [ ] Khai báo `UserProfile` trong module `user-profiles`.
* [ ] UserProfile có tối thiểu:

  * `id`.
  * `accountId`.
  * `fullName`.
  * `email`.
  * `avatarId`.
  * `dateOfBirth`.
  * `address`.
  * Audit metadata.
* [ ] `accountId` có unique constraint.
* [ ] Mỗi Account chỉ có tối đa một UserProfile.
* [ ] Email chỉ là thông tin liên hệ.
* [ ] Email không được sử dụng làm login identifier.
* [ ] Email được normalize về lowercase trước khi lưu.
* [ ] Email có thể nullable nếu nghiệp vụ không bắt buộc.
* [ ] UserProfile không chứa password hoặc permission.
* [ ] Không tạo TypeORM relation trực tiếp từ UserProfile sang Account.
* [ ] Kiểm tra Account tồn tại thông qua application contract.

Quan hệ:

```text
Account 1 ───── 1 UserProfile
```

### 5. Customer và Staff boundary

* [ ] Không tạo Customer tự động khi tạo Account.
* [ ] Không coi mọi Account đăng nhập public là Customer.
* [ ] Không coi tài khoản admin là Customer.
* [ ] Tài liệu architecture phải mô tả:

  * UserProfile là hồ sơ chung.
  * Customer là hồ sơ nghiệp vụ khách hàng.
  * Staff là hồ sơ nghiệp vụ nhân viên.
* [ ] Customer hoặc Staff sau này liên kết với:

  * `accountId`.
  * Hoặc `userProfileId`.
* [ ] Không triển khai Customer hoặc Staff trong epic này.

Luồng tương lai:

```text
Account
   └── UserProfile
          ├── Customer
          └── Staff
```

### 6. Auditable entity foundation

* [ ] Bổ sung hoặc hoàn thiện AuditableEntity abstraction.
* [ ] Các entity cần audit có:

  * `createdBy`.
  * `createdAt`.
  * `updatedBy`.
  * `updatedAt`.
  * `deletedBy`.
  * `deletedAt`.
* [ ] Database sử dụng tên cột:

  * `created_by`.
  * `created_at`.
  * `updated_by`.
  * `updated_at`.
  * `deleted_by`.
  * `deleted_at`.
* [ ] Timestamp sử dụng timezone-aware type.
* [ ] Không cho client truyền audit fields.
* [ ] Audit actor được lấy từ request context.
* [ ] Query mặc định bỏ qua bản ghi đã soft delete.
* [ ] Không lặp lại khai báo audit columns trong từng ORM entity.

### 7. Database migration

* [ ] Tạo migration cho:

  * `identity.accounts`.
  * `identity.auth_identities`.
  * `identity.refresh_sessions`.
  * `identity.roles`.
  * `identity.permissions`.
  * `identity.account_roles`.
  * `identity.role_permissions`.
  * `profile.user_profiles`.
* [ ] Không sử dụng schema `customer` cho UserProfile.
* [ ] Schema đề xuất cho UserProfile là:

  * `profile`.
  * Hoặc schema tương đương theo convention hiện tại.
* [ ] Tạo index cho:

  * Auth identity identifier.
  * Provider subject.
  * Account status.
  * UserProfile account ID.
  * Soft-delete fields.
* [ ] Unique index phải xử lý đúng soft delete.
* [ ] Không bật `synchronize: true`.
* [ ] Migration hỗ trợ rollback trong development và test.
* [ ] Seed Role và Permission phải idempotent.

### 8. Transaction tạo Account

* [ ] Triển khai use case tạo Account trong một transaction.
* [ ] Luồng tạo Account gồm:

  1. Normalize số điện thoại.
  2. Kiểm tra identifier trùng.
  3. Hash password.
  4. Tạo Account.
  5. Tạo LOCAL AuthIdentity.
  6. Tạo UserProfile.
  7. Gán default role.
* [ ] Nếu bất kỳ bước nào thất bại, toàn bộ transaction phải rollback.
* [ ] Không để tồn tại:

  * Account không có LOCAL AuthIdentity.
  * Account không có UserProfile.
  * AuthIdentity không có Account.
* [ ] Có application error riêng cho:

  * Phone đã tồn tại.
  * Account không tồn tại.
  * UserProfile đã tồn tại.
  * Provider không được hỗ trợ.
  * Dữ liệu không hợp lệ.

### 9. Login bằng phone và password

* [ ] Thay đổi login request từ:

```json
{
  "email": "user@example.com",
  "password": "..."
}
```

thành:

```json
{
  "phone": "0912345678",
  "password": "...",
  "portal": "PUBLIC"
}
```

Hoặc admin:

```json
{
  "phone": "0912345678",
  "password": "...",
  "portal": "ADMIN"
}
```

* [ ] Portal sử dụng enum:

  * `PUBLIC`.
  * `ADMIN`.
* [ ] Không cho client truyền permission cần kiểm tra.
* [ ] Backend tự map portal sang permission.
* [ ] Mapping tối thiểu:

```text
PUBLIC → portal.public.access
ADMIN  → portal.admin.access
```

* [ ] Chuẩn hóa phone trước khi query.
* [ ] Hỗ trợ default region Việt Nam qua configuration.
* [ ] Xác thực credential thông qua LOCAL authentication provider.
* [ ] Không trả lỗi khác nhau giữa:

  * Phone không tồn tại.
  * Password không đúng.
* [ ] Không cho Account inactive, locked hoặc deleted đăng nhập.
* [ ] Sau khi credential hợp lệ, hệ thống phải kiểm tra portal permission.
* [ ] Chỉ tạo refresh session sau khi portal authorization thành công.
* [ ] Không phát token nếu Account không có quyền truy cập portal.
* [ ] Không giữ fallback login bằng email.
* [ ] Xóa dữ liệu và logic mock authentication.

### 10. Phân biệt authentication và authorization

Luồng đăng nhập phải được chia rõ thành:

#### Authentication

* [ ] Tìm LOCAL AuthIdentity theo phone đã normalize.
* [ ] Xác minh password.
* [ ] Kiểm tra Account status.
* [ ] Xác định Account đã được xác thực.

#### Portal authorization

* [ ] Resolve Role và Permission của Account.
* [ ] Xác định permission tương ứng với portal.
* [ ] Kiểm tra Account có permission truy cập portal.
* [ ] Nếu thiếu permission:

  * Không tạo refresh session.
  * Không phát access token.
  * Trả lỗi truy cập phù hợp.
* [ ] Không hard-code role trong login use case.
* [ ] Không xử lý theo kiểu:

```ts
if (role === 'ADMIN') {
  // allow admin login
}
```

* [ ] Phải kiểm tra permission:

```ts
authorizationService.hasPermission(
  accountId,
  'portal.admin.access',
);
```

### 11. Authentication provider abstraction

* [ ] Khai báo `AuthenticationProvider` port.
* [ ] Provider contract hỗ trợ:

  * Xác định provider.
  * Validate credential.
  * Resolve normalized identity.
  * Resolve Account.
* [ ] Triển khai Provider Registry hoặc Factory.
* [ ] Login use case không chứa switch/case theo từng provider.
* [ ] JWT service không phụ thuộc vào provider cụ thể.
* [ ] Refresh session service không phụ thuộc vào provider cụ thể.
* [ ] Chỉ implement LocalAuthenticationProvider trong epic này.
* [ ] Google, Apple và Facebook chỉ cần contract và provider code.

### 12. RBAC foundation

* [ ] Khai báo các model:

  * Role.
  * Permission.
  * AccountRole.
  * RolePermission.
* [ ] Role sử dụng code ổn định.
* [ ] Permission sử dụng code ổn định.
* [ ] Role chỉ là nhóm các permission.
* [ ] Không dùng display name làm business identifier.
* [ ] Permission tối thiểu:

```text
portal.public.access
portal.admin.access

account.create
account.read
account.update
account.delete
account.change-status
account.change-password

user-profile.create
user-profile.read
user-profile.update
user-profile.delete

role.read
role.assign
permission.read
```

* [ ] Có default role cho Account public.
* [ ] Default role được cấu hình, không hard-code trong use case.
* [ ] Có guard, decorator hoặc policy evaluator theo convention hiện tại.
* [ ] Các API Account và UserProfile phải khai báo permission.
* [ ] Không controller nào hard-code role.
* [ ] Request context chứa Role và Permission đã resolve.
* [ ] Chưa triển khai CRUD Role và Permission hoàn chỉnh.

Role mẫu:

```text
PUBLIC_USER
└── portal.public.access

ADMIN
├── portal.admin.access
├── account.read
└── user-profile.read

SUPER_ADMIN
├── portal.admin.access
├── account.*
├── user-profile.*
├── role.*
└── permission.*
```

### 13. JWT payload và session

* [ ] JWT payload có tối thiểu:

  * `sub`: Account ID.
  * `userProfileId`.
  * `sessionId`.
  * `portal`.
  * `authProvider`.
* [ ] Chỉ thêm Role hoặc Permission vào token nếu phù hợp với policy hiện tại.
* [ ] Nếu permission có thể thay đổi trong khi token còn hạn, phải có cơ chế:

  * Token version.
  * Permission version.
  * Hoặc resolve permission lại ở protected request.
* [ ] Token phát cho PUBLIC không được tự động sử dụng để truy cập ADMIN nếu audience/portal không hợp lệ.
* [ ] Token phải có audience hoặc portal claim phù hợp.
* [ ] Admin API phải kiểm tra đúng audience/portal.
* [ ] Public API không được coi token admin là mặc nhiên hợp lệ nếu policy yêu cầu tách audience.
* [ ] Access token tiếp tục lưu trong memory.
* [ ] Refresh token tiếp tục lưu trong cookie HttpOnly.
* [ ] Refresh session phải gắn với portal.
* [ ] Một Account có thể có nhiều session cho các portal và thiết bị khác nhau.
* [ ] Account bị khóa hoặc xóa phải revoke toàn bộ session.
* [ ] Có thể revoke riêng session theo portal hoặc device.

### 14. Request context

* [ ] Triển khai request context bằng AsyncLocalStorage, `nestjs-cls` hoặc abstraction tương đương.
* [ ] Context có tối thiểu:

  * `requestId`.
  * `correlationId`.
  * `accountId`.
  * `userProfileId`.
  * `sessionId`.
  * `portal`.
  * `authProvider`.
  * `roles`.
  * `permissions`.
  * `ipAddress`.
  * `userAgent`.
  * `requestedAt`.
* [ ] Middleware tạo request metadata.
* [ ] Authentication guard bổ sung authenticated Account.
* [ ] Authorization guard bổ sung permission context.
* [ ] Không truyền HTTP Request object xuyên application layer.
* [ ] Các request đồng thời không được lẫn context.
* [ ] Có system context cho:

  * Worker.
  * Scheduler.
  * CLI.
  * Background job.
* [ ] System actor phải được phân biệt với Account actor.

### 15. Audit behavior

* [ ] Khi create:

  * `createdBy` lấy từ context.
  * `createdAt` lấy từ server clock.
* [ ] Khi update:

  * `updatedBy` lấy từ context.
  * `updatedAt` lấy từ server clock.
* [ ] Khi soft delete:

  * `deletedBy` lấy từ context.
  * `deletedAt` lấy từ server clock.
* [ ] Client không được truyền actor hoặc timestamp.
* [ ] Audit metadata được lưu cùng transaction.
* [ ] Không đưa password, token hoặc cookie vào audit log.
* [ ] Correlation ID được đưa vào log và event metadata.

### 16. Account CRUD API

* [ ] Triển khai API:

  * Tạo Account.
  * Lấy danh sách Account.
  * Lấy chi tiết Account.
  * Cập nhật Account.
  * Thay đổi trạng thái.
  * Thay đổi phone.
  * Thay đổi/reset password.
  * Soft delete Account.
* [ ] Không cập nhật password qua generic update DTO.
* [ ] Không cập nhật phone qua generic update DTO.
* [ ] List API hỗ trợ:

  * Pagination.
  * Filter status.
  * Filter provider.
  * Search phone.
  * Sort theo whitelist.
* [ ] Account response không chứa password hash.
* [ ] Xóa Account phải:

  * Soft delete Account.
  * Soft delete AuthIdentity.
  * Soft delete UserProfile.
  * Revoke refresh sessions.
* [ ] Mọi API được bảo vệ bằng permission phù hợp.

Route đề xuất:

```text
POST   /accounts
GET    /accounts
GET    /accounts/:accountId
PATCH  /accounts/:accountId
PATCH  /accounts/:accountId/status
PATCH  /accounts/:accountId/phone
PATCH  /accounts/:accountId/password
DELETE /accounts/:accountId
```

### 17. UserProfile CRUD API

* [ ] Triển khai API:

  * Tạo UserProfile.
  * Lấy danh sách UserProfile.
  * Lấy chi tiết UserProfile.
  * Cập nhật UserProfile.
  * Soft delete UserProfile.
* [ ] Không cho tạo nhiều profile cho một Account.
* [ ] Không cho client đổi `accountId` qua update DTO.
* [ ] List API hỗ trợ:

  * Pagination.
  * Search full name.
  * Search email.
  * Search phone thông qua identity-access query contract.
  * Sort theo whitelist.
* [ ] Không trả trực tiếp ORM entity.
* [ ] Không cho Account tiếp tục hoạt động nếu UserProfile bị xóa mà policy yêu cầu profile bắt buộc.
* [ ] Mọi API được bảo vệ bằng permission phù hợp.

Route đề xuất:

```text
POST   /user-profiles
GET    /user-profiles
GET    /user-profiles/:userProfileId
PATCH  /user-profiles/:userProfileId
DELETE /user-profiles/:userProfileId
```

### 18. Frontend integration

> **Đã loại khỏi phạm vi epic này kể từ `changes/cycle-001/requirement-addendum.md`** (quyết định người dùng: MEMORIES-0002 chỉ còn backend-only). Checkbox bên dưới được đánh dấu hoàn tất (loại khỏi kế hoạch triển khai tự động) để giữ nguyên nội dung yêu cầu gốc làm lịch sử tham khảo, không phải xác nhận đã triển khai. Xem addendum để biết chi tiết thay thế AC36/AC39.

* [x] Cập nhật form login public.
* [x] Cập nhật form login admin.
* [x] Thay email bằng phone.
* [x] Public web gửi:

```json
{
  "phone": "...",
  "password": "...",
  "portal": "PUBLIC"
}
```

* [x] Admin web gửi:

```json
{
  "phone": "...",
  "password": "...",
  "portal": "ADMIN"
}
```

* [x] Không cho người dùng tự chọn portal trên giao diện.
* [x] Portal được xác định bởi application đang thực hiện login.
* [x] Input phone sử dụng:

  * `type="tel"`.
  * `inputMode="tel"`.
  * Autofill phù hợp.
* [x] Access token tiếp tục lưu trong memory.
* [x] Không lưu token vào localStorage hoặc sessionStorage.
* [x] Refresh token không được đọc bởi JavaScript.
* [x] Cập nhật API client, schema validation và generated types.
* [x] Xóa mock user khỏi frontend.
* [x] Hiển thị lỗi phù hợp khi:

  * Credential không hợp lệ.
  * Account bị khóa.
  * Account không có quyền truy cập portal.

### 19. Validation và security

* [ ] Phone bắt buộc với LOCAL provider.
* [ ] Password bắt buộc với LOCAL provider.
* [ ] Password tuân thủ password policy tập trung.
* [ ] Full name bắt buộc khi tạo UserProfile.
* [ ] Email được validate khi có giá trị.
* [ ] Mọi string input có giới hạn độ dài.
* [ ] Không mass assignment các trường hệ thống.
* [ ] Login endpoint có rate limit.
* [ ] Không cho phép account enumeration.
* [ ] Không log credential.
* [ ] Refresh cookie sử dụng:

  * HttpOnly.
  * Secure trong môi trường phù hợp.
  * SameSite theo configuration.
  * Path và domain tối thiểu.
* [ ] Refresh endpoint áp dụng CSRF/origin protection hiện tại.
* [ ] Protected request kiểm tra Account status.
* [ ] Admin API kiểm tra `portal.admin.access`.
* [ ] Không đưa thông tin cá nhân không cần thiết vào JWT.

### 20. Tests

* [ ] Unit test Account.
* [ ] Unit test AuthIdentity.
* [ ] Unit test UserProfile.
* [ ] Unit test phone normalization.
* [ ] Unit test LocalAuthenticationProvider.
* [ ] Unit test login use case.
* [ ] Unit test portal authorization.
* [ ] Unit test permission evaluator.
* [ ] Integration test Account repository.
* [ ] Integration test AuthIdentity repository.
* [ ] Integration test UserProfile repository.
* [ ] Integration test transaction tạo Account.
* [ ] Integration test audit fields.
* [ ] Integration test unique phone.
* [ ] E2E login public thành công.
* [ ] E2E login admin thành công.
* [ ] E2E Account chỉ có public permission không đăng nhập được admin.
* [ ] E2E Account có admin permission đăng nhập được admin.
* [ ] E2E credential sai.
* [ ] E2E Account inactive.
* [ ] E2E Account locked.
* [ ] E2E Account deleted.
* [ ] E2E refresh token theo portal.
* [ ] E2E revoke session khi Account bị khóa hoặc xóa.
* [ ] E2E Account CRUD theo permission.
* [ ] E2E UserProfile CRUD theo permission.
* [ ] Test hai request đồng thời không lẫn context.
* [ ] Frontend test login public.
* [ ] Frontend test login admin.
* [ ] Frontend test token chỉ lưu trong memory.

### 21. Documentation

* [ ] Cập nhật authentication flow.
* [ ] Cập nhật portal authorization flow.
* [ ] Cập nhật module boundaries.
* [ ] Cập nhật ERD.
* [ ] Mô tả Account, AuthIdentity và UserProfile.
* [ ] Mô tả sự khác nhau giữa:

  * UserProfile.
  * Customer.
  * Staff.
* [ ] Mô tả phone normalization.
* [ ] Mô tả password policy.
* [ ] Mô tả permission naming convention.
* [ ] Mô tả request context lifecycle.
* [ ] Mô tả audit metadata.
* [ ] Mô tả cách thêm authentication provider.
* [ ] Mô tả cách thêm portal mới.
* [ ] Cập nhật `.env.example`.
* [ ] Không thêm secret thật vào repository.

## Acceptance criteria

1. Account được sử dụng làm principal xác thực duy nhất cho cả public-web và admin-web.

2. Không tạo Account riêng cho public và admin.

3. UserProfile được đặt trong module `user-profiles`, không nằm trong module `customers`.

4. Customer không được tạo tự động khi tạo Account.

5. Account, AuthIdentity và UserProfile được triển khai đầy đủ theo các layer hiện tại.

6. Một Account có thể có nhiều AuthIdentity.

7. Một Account chỉ có tối đa một UserProfile.

8. LOCAL AuthIdentity sử dụng phone đã normalize và password hash.

9. Login bằng email không còn hoạt động.

10. Public web đăng nhập với portal `PUBLIC`.

11. Admin web đăng nhập với portal `ADMIN`.

12. Backend tự map portal sang permission tương ứng.

13. Account phải có `portal.public.access` để đăng nhập public nếu hệ thống áp dụng kiểm soát explicit cho public portal.

14. Account phải có `portal.admin.access` để đăng nhập admin.

15. Account thiếu permission portal không được phát token hoặc tạo refresh session cho portal đó.

16. Không controller hoặc use case nào hard-code role để kiểm tra quyền truy cập portal.

17. Role chỉ là nhóm permission.

18. Account inactive, locked hoặc deleted không thể login hoặc refresh.

19. Access token tiếp tục được lưu trong memory.

20. Refresh token tiếp tục được lưu trong HttpOnly cookie.

21. Refresh session được gắn với portal.

22. JWT hoặc session có thể phân biệt public và admin portal.

23. Token public không thể truy cập admin API nếu không hợp lệ về audience hoặc portal.

24. Password không được lưu dưới dạng plain text.

25. Password hash không xuất hiện trong API response, log hoặc audit record.

26. Account, AuthIdentity và UserProfile có đầy đủ audit fields.

27. Audit actor được lấy từ request context.

28. Hai request đồng thời không bị lẫn context.

29. Tạo Account, AuthIdentity, UserProfile và default role được thực hiện trong cùng transaction.

30. Account CRUD API hoạt động và được bảo vệ bằng permission.

31. UserProfile CRUD API hoạt động và được bảo vệ bằng permission.

32. Xóa hoặc khóa Account làm mất hiệu lực session hiện tại.

33. Không sử dụng TypeORM relation trực tiếp xuyên module.

34. Không trả ORM entity trực tiếp từ controller.

35. Swagger/OpenAPI được cập nhật.

36. API client frontend được cập nhật hoặc regenerate thành công.

37. Migration chạy thành công trên database trống.

38. Seed Role và Permission chạy nhiều lần không tạo dữ liệu trùng.

39. Mock authentication được xóa khỏi backend và frontend.

40. Unit test, integration test, E2E test, lint, typecheck và build đều thành công.

## Out of scope

* Tích hợp Google OAuth thực tế.
* Tích hợp Apple Sign In thực tế.
* Tích hợp Facebook Login thực tế.
* OTP số điện thoại.
* Xác minh số điện thoại.
* Quên mật khẩu qua SMS hoặc email.
* Multi-factor authentication.
* Passkey hoặc WebAuthn.
* Account linking giữa nhiều provider.
* CRUD Role và Permission hoàn chỉnh.
* Giao diện quản trị Role và Permission.
* Data scope nâng cao.
* Attribute-based access control.
* Tạo model Customer.
* Tạo model Staff.
* CRM hoặc loyalty program.
* Import hàng loạt Account.
* Xóa vật lý Account hoặc UserProfile.
* Thay đổi chiến lược lưu access token và refresh token hiện tại.
