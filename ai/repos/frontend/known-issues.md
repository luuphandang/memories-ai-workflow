# Memories Frontend Known Issues

| ID | Dấu hiệu | Phạm vi | Workaround | Trạng thái |
|---|---|---|---|---|
| FE-1 | 19/20 trang dashboard dưới `apps/admin-web/app/(dashboard)/*` chỉ render 1 dòng `<h1>` placeholder, chưa có data fetching/UI thật | `admin-web` — overview, orders, products, staff, reports, v.v. | Không có — chờ triển khai tính năng tương ứng | Đã biết, chưa xử lý |
| FE-2 | Đa số trang commerce/cards của `public-web` (`products`, `cart`, `checkout`, `custom-orders`, `templates`, `view/[cardId]`, `design/[cardDesignId]`, `policies/[slug]`, v.v.) là stub tĩnh | `public-web` | Không có — chờ triển khai tính năng tương ứng | Đã biết, chưa xử lý |
| FE-3 | `apps/public-web/app/(auth)/register/page.tsx` chưa triển khai dù `registerSchema` (packages/validation) đã có sẵn | `public-web` — trang đăng ký | Không có | Đã biết, chưa xử lý |
| FE-4 | `packages/i18n` và `packages/analytics` đã code + test đầy đủ nhưng KHÔNG được import ở bất kỳ app nào (dead code trong trạng thái hiện tại) | `packages/i18n`, `packages/analytics` | Không có | Đã biết, chưa tích hợp |
| FE-5 | TanStack Query đã cấu hình đầy đủ (provider, client, query-key factory) nhưng chưa có page nào gọi `useQuery`/`useMutation` thật | Toàn bộ 2 app | Không có | Đã biết, chờ tính năng dùng data fetching thật |
| FE-6 | `packages/editor-core` (document model cho card design) đã code + test nhưng chưa được mount vào UI thật (`design/[cardDesignId]/page.tsx` chỉ có comment nhắc tới, chưa import) | `public-web` | Không có | Đã biết, chưa tích hợp |
