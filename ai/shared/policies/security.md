# Security Policy

## Cấm

- Đọc/ghi `.env*`, secret manager dump, private key, access token, cookie, credential hoặc dữ liệu production.
- Ghi secret vào prompt, log, báo cáo, fixture hoặc knowledge base.
- Vô hiệu hóa authentication/authorization để làm test pass.
- Chạy script tải/chạy mã bên ngoài không được dự án kiểm soát.
- Thay đổi policy bảo mật ngoài scope tính năng.

## Bắt buộc

- Dùng dữ liệu giả cho test.
- Giữ nguyên cơ chế phân quyền hiện có: backend xác thực bằng `JwtAuthGuard` (`libs/platform/security`, verify Bearer access token, áp dụng theo từng controller qua `@UseGuards`) + rate limiting toàn cục bằng `ThrottlerGuard` (đăng ký `APP_GUARD`); frontend giữ access token CHỈ in-memory (`packages/auth/src/token-store.ts`, không bao giờ ghi localStorage/sessionStorage) và kiểm tra quyền hiển thị qua `hasPermission`/`hasAnyPermission` (`packages/auth/src/permissions.ts`). Không tắt/bỏ qua các cơ chế này để làm test hoặc tính năng mới pass.
- Với tính năng hiện tại, xác định actor, quyền, dữ liệu nhạy cảm và trust boundary: `[BỔ SUNG THEO TÍNH NĂNG]`.
- Báo `blocker` nếu phát hiện nguy cơ lộ secret, bypass quyền hoặc mất dữ liệu.

## CI and runtime security activation

- Khai báo `permissions` trong GitHub Actions làm mọi scope không liệt kê thành `none`; rà toàn bộ action/CLI trong job khi thay đổi permissions.
- Không nội suy input không tin cậy trực tiếp vào `run:`. Truyền qua `env:` rồi tham chiếu biến shell đã quote.
- Import module cấu hình bảo mật không đồng nghĩa enforcement đã chạy. Guard/middleware phải được đăng ký (`APP_GUARD` hoặc route guard) và được xác minh bằng traffic/test vượt policy, ví dụ rate-limit.
