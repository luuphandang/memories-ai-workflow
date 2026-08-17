# MEMORIES-0005: Implement Authorize At Public Website

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0005`

## Goal

Cho phép khách truy cập đăng ký, đăng nhập và đăng xuất ngay từ icon người dùng trên
website public. Luồng xác thực phải hỗ trợ tài khoản số điện thoại/mật khẩu và đăng nhập
qua Google, đồng thời giữ nguyên ngôn ngữ thiết kế hiện tại và tách các
thành phần dùng chung thành component có thể tái sử dụng.

## Background

Website public hiện dùng icon người dùng trên header làm điểm truy cập tài khoản. Yêu cầu
mới thay hành vi điều hướng sang trang đăng nhập bằng trải nghiệm tại chỗ:

- Khách chưa đăng nhập bấm icon người dùng sẽ thấy modal đăng nhập.
- Từ modal đăng nhập, khách chưa có tài khoản có thể chuyển sang biểu mẫu đăng ký.
- Người dùng đã đăng nhập bấm icon người dùng sẽ thấy popup tài khoản với hành động
  đăng xuất.
- Modal đăng nhập có lựa chọn đăng nhập bằng Google bên cạnh số điện thoại/
  mật khẩu.

## Current system

- Frontend là Next.js App Router; website public nằm tại
  `apps/frontend/apps/public-web`. `SiteHeader` hiện hiển thị icon người dùng nhưng điều
  hướng khách tới `/login` và người đã đăng nhập tới `/profile`.
- `public-web` đã được bọc bởi `AuthProvider` trong `app/providers.tsx`. Access token được
  giữ in-memory bằng `TokenStore`; refresh token được backend quản lý bằng HttpOnly cookie.
- Trang `/login` và package `@memories/validation` hiện dùng trường `email`, trong khi API
  backend hiện hành nhận `phone`, `password` và `portal` cho đăng nhập. Contract frontend
  phải được đồng bộ về đăng nhập bằng số điện thoại với `portal: PUBLIC`.
- Backend đã có các endpoint `POST /api/v1/auth/register`, `POST /api/v1/auth/login`,
  `POST /api/v1/auth/refresh` và `POST /api/v1/auth/logout` trong module
  `identity-access`. Đăng ký hiện tạo tài khoản PUBLIC và phiên đăng nhập; payload đã có
  `phone`, `password`, `fullName`, `email?` nhưng chưa nhận `address`.
- Hồ sơ người dùng tại module `user-profiles` đã có trường `address`, vì vậy luồng đăng ký
  cần truyền và lưu địa chỉ tùy chọn trong cùng giao dịch tạo tài khoản/hồ sơ.
- Domain đã mô hình hóa `AuthProvider`. Luồng Google OAuth thuộc phạm vi public hiện hành.
  Facebook Login bị vô hiệu hóa hoàn toàn trong phạm vi task này: không hiển thị trên UI,
  không có public entry point hoạt động và không thể tạo phiên Facebook bằng cách gọi trực
  tiếp endpoint. Mã nền tảng chưa kích hoạt có thể được giữ lại để triển khai sau.
- UI dùng design token chung và các component trong `packages/ui`; dự án đã có `Drawer`,
  `Button`, `IconButton`, form primitives và toast. Component modal/popup xác thực mới phải
  dùng token/style hiện hữu, có focus management và hỗ trợ bàn phím.

## Scope

- [ ] Đổi hành vi icon người dùng trên `SiteHeader`: mở modal xác thực khi chưa đăng nhập;
  mở popup menu tài khoản khi đã đăng nhập; áp dụng tương đương tại điểm truy cập tài
  khoản trên mobile nếu có.
- [ ] Xây modal đăng nhập gồm số điện thoại, mật khẩu, submit đăng nhập LOCAL, nút đăng
  nhập Google và lời mời/link chuyển sang đăng ký. Không hiển thị nút Facebook.
- [ ] Xây biểu mẫu đăng ký gồm số điện thoại (bắt buộc), mật khẩu (bắt buộc), xác nhận mật
  khẩu (bắt buộc), họ tên (bắt buộc) và địa chỉ (không bắt buộc); có thể chuyển lại màn
  đăng nhập mà không cần rời trang.
- [ ] Kết nối đăng nhập, đăng ký, đăng xuất với API và cập nhật `AuthProvider`/validation/
  generated contract liên quan; đăng nhập từ public web luôn yêu cầu portal `PUBLIC`.
- [ ] Mở rộng backend để tiếp nhận và lưu `address?` khi tự đăng ký, không cho client tự
  gán portal, role hoặc permission.
- [ ] Triển khai luồng đăng nhập Google ở cả backend/frontend, gồm bắt đầu
  OAuth, xử lý callback, tạo hoặc liên kết danh tính nhà cung cấp với tài khoản PUBLIC,
  phát hành phiên theo cùng chính sách token/cookie hiện có và xử lý hủy/từ chối/lỗi.
- [ ] Vô hiệu hóa Facebook Login trên public website và backend public surface: không render
  nút/link Facebook; OAuth start/callback Facebook phải không được đăng ký, không khả dụng hoặc
  fail closed mà không gọi provider, không tạo/liên kết account và không phát hành phiên.
- [ ] Tách trigger, auth modal, form đăng nhập, form đăng ký, nút social-login và account
  popup thành các component phù hợp để tái sử dụng; logic gọi API/state không lặp lại trong
  từng vị trí hiển thị.
- [ ] Bổ sung trạng thái loading, lỗi validation/API, chống submit lặp và hành vi đóng/mở
  accessible cho modal/popup.
- [ ] Test thay đổi liên quan.
- [ ] Tài liệu/knowledge update nếu phát sinh kiến thức bền vững.

## Acceptance criteria

1. Khi chưa đăng nhập, bấm icon người dùng trên website public mở modal đăng nhập thay vì
   điều hướng sang trang khác; modal có thể đóng bằng nút đóng, phím Escape và thao tác
   theo convention của dialog, đồng thời quản lý focus đúng.
2. Modal đăng nhập hiển thị trường số điện thoại và mật khẩu bắt buộc. Dữ liệu hợp lệ gọi
   API với portal `PUBLIC`; trong lúc gửi không thể submit lặp; lỗi validation hoặc lỗi API
   được hiển thị rõ ràng mà không làm mất dữ liệu người dùng đã nhập.
3. Modal đăng nhập có lựa chọn Google và không hiển thị lựa chọn Facebook. Hoàn tất Google
   OAuth tạo phiên PUBLIC và cập nhật UI sang trạng thái đã đăng nhập; người dùng hủy, từ chối
   quyền hoặc callback lỗi được đưa về website với thông báo có thể hiểu được và không tạo phiên
   giả/dở dang. Facebook Login phải bị vô hiệu hóa cả ở UI lẫn backend public entry points;
   request trực tiếp tới start/callback Facebook không được gọi provider hoặc tạo phiên.
4. Modal đăng nhập có nội dung dành cho người chưa có tài khoản và hành động “Đăng ký”.
   Hành động này hiển thị form đăng ký trong cùng trải nghiệm modal; người dùng có thể quay
   lại đăng nhập.
5. Form đăng ký bắt buộc số điện thoại, mật khẩu, xác nhận mật khẩu và họ tên; địa chỉ là
   tùy chọn. Form chặn submit khi trường bắt buộc không hợp lệ hoặc xác nhận mật khẩu không
   khớp, và hiển thị lỗi tại đúng trường.
6. Đăng ký thành công tạo đúng một tài khoản PUBLIC, danh tính LOCAL, hồ sơ có họ tên và
   địa chỉ nếu được cung cấp, vai trò mặc định và phiên xác thực trong một giao dịch nhất
   quán; số điện thoại trùng được báo lỗi và không tạo dữ liệu trùng/dang dở.
7. Sau đăng nhập hoặc đăng ký thành công, modal đóng, trạng thái xác thực được cập nhật và
   phiên vẫn tuân thủ cơ chế access token in-memory + refresh token HttpOnly cookie hiện có.
8. Khi đã đăng nhập, bấm icon người dùng mở popup neo tại icon. Popup có một dòng hành động
   “Đăng xuất”; chọn hành động gọi API logout, thu hồi/clear phiên phía server và client,
   đóng popup và đưa UI về trạng thái chưa đăng nhập.
9. Modal, popup, form và nút dùng design token/component hiện hữu, hiển thị tốt trên desktop
   và mobile, có accessible name/role, thao tác được bằng bàn phím và không phá vỡ header,
   navigation hay các route public hiện tại.
10. Các component xác thực có thể tái sử dụng, không chứa bản sao form/logic API giữa
    desktop và mobile; test bao phủ các happy path, validation/error chính, chuyển đổi
    đăng nhập–đăng ký, OAuth callback và đăng xuất.

## Out of scope

- Quên/đặt lại mật khẩu, OTP hoặc xác minh số điện thoại.
- Chỉnh sửa hồ sơ, đổi mật khẩu và quản lý nhiều phiên/thiết bị.
- Thay đổi luồng đăng nhập hoặc phân quyền của admin website.
- Hiển thị, kích hoạt hoặc cung cấp public endpoint hoạt động cho Facebook Login; tính năng
  này được hoãn để triển khai sau khi provider contract được xác minh.
- Thêm nhà cung cấp đăng nhập ngoài LOCAL, Google và Facebook.
- Thiết kế lại header, hệ thống design token hoặc các trang public không liên quan.

## Technical notes

- Module/file liên quan frontend: `apps/public-web/components/site-header.tsx`,
  `apps/public-web/app/providers.tsx`, `packages/auth`, `packages/validation`,
  `packages/api-client` và `packages/ui` trong repo `apps/frontend`. Component chỉ dùng cho
  public shell đặt dưới `apps/public-web/components`; primitive thực sự dùng chung giữa các
  app đặt trong `packages/ui`.
- Module/file liên quan backend: `libs/modules/identity-access` cho register/login/logout và
  provider OAuth; `libs/modules/user-profiles` cho địa chỉ; migration tại
  `libs/platform/database/src/migrations` chỉ khi mô hình persistence thực tế yêu cầu đổi
  schema.
- API/database/UI convention: dùng contract OpenAPI sinh type, không sửa tay
  `packages/api-client/src/generated/schema.d.ts`; request lỗi đi qua error envelope chuẩn;
  backend giữ Clean Architecture và cross-module import qua public API. Không lưu access
  token trong localStorage/sessionStorage. Refresh cookie tiếp tục HttpOnly và các endpoint
  public/OAuth phải được rate-limit, kiểm tra state/nonce/redirect URI theo cấu hình tin cậy.
- Luồng LOCAL: icon user → modal login → submit `phone/password/portal: PUBLIC` → cập nhật
  auth state; hoặc login modal → register form → submit thông tin → tạo phiên PUBLIC. Luồng
  logout: icon user → account popup → logout → revoke session/clear token và cookie.
- Luồng OAuth Google: social button → backend khởi tạo authorization với state/nonce → provider →
  backend callback xác minh response và danh tính → tạo/liên kết account PUBLIC theo quy
  tắc không trùng danh tính → phát hành refresh cookie → trả người dùng về public web để
  rehydrate access token. Không đưa provider secret/token vào browser, URL, log hoặc tài
  liệu.
- Facebook Login phải fail closed trước khi trao đổi với provider. Không được phát hành refresh
  cookie/access token, tạo account/profile/identity/session hoặc làm UI báo đăng nhập thành công
  từ bất kỳ request Facebook OAuth nào trong phạm vi task này.
- Edge case bắt buộc: số điện thoại đã tồn tại; sai thông tin đăng nhập; tài khoản inactive/
  locked/deleted; password confirmation không khớp; mất mạng/API error; submit nhiều lần;
  refresh hết hạn; logout lỗi; OAuth bị hủy, state/nonce sai, email/provider identifier trùng
  hoặc callback lặp. Các lỗi không được để UI báo đã đăng nhập khi server chưa tạo phiên.

## Constraints

- Không quản lý worktree/branch.
- Không commit hoặc push.
- Không đọc secret.
- Không sửa ngoài worktree khai báo.
