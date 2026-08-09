# Memories Frontend Architecture

## Routing/rendering
Next.js App Router (`app/` directory, không có `pages/`) cho cả `admin-web` và `public-web`. Đa số `page.tsx` là server component thuần (không có `'use client'`); chỉ 9 file dùng `'use client'` toàn repo — `app/providers.tsx`, `app/error.tsx`, trang login của cả 2 app, `auth-guard.tsx`/`dashboard-nav.tsx` (admin-web), trang `profile` (public-web) — tức chỉ những nơi thật sự cần context/hook/`useRouter` mới là client component. Không có `middleware.ts` ở app nào — bảo vệ route (redirect khi chưa đăng nhập) làm ở client qua `AuthGuard` component, không qua Next middleware.

## State/data fetching
TanStack Query (`@tanstack/react-query ^5.51.23`) đã cấu hình đầy đủ: `packages/query/src/query-client.ts` (`createQueryClient()` — staleTime 30s, retry 1, `refetchOnWindowFocus:false`) + `packages/query/src/query-provider.tsx` (`QueryProvider`), cả 2 app đều wrap qua `app/providers.tsx`. Có sẵn convention query-key (`packages/query/src/query-key-factory.ts`: `createQueryKeyFactory(domain)` → `all()/lists()/list(params)/details()/detail(id)`). HIỆN TẠI chưa có page nào thật sự gọi `useQuery`/`useMutation` — toàn bộ hạ tầng đã lắp nhưng chưa có consumer thật (mọi trang dashboard/commerce đều là stub tĩnh). Không dùng thư viện state khác (không có zustand/redux/jotai); auth state là React context thuần (`packages/auth/src/auth-provider.tsx`, dùng `useSyncExternalStore`).

## Component boundaries
`admin-web` và `public-web` không import lẫn nhau (xác nhận bằng grep — 0 kết quả); cả 2 chỉ import từ package `@memories/*` dùng chung hoặc từ `./app`/`./components` nội bộ của chính mình. Ranh giới này hiện là RÀNG BUỘC CẤU TRÚC (npm workspaces + `transpilePackages` trong `next.config.js`), KHÔNG có ESLint rule nào (không có `eslint-plugin-boundaries`/`no-restricted-imports`) enforce tự động — chỉ có `import/order` (warn) và `import/no-cycle` (error) trong `packages/eslint-config`.

## Auth/permission UI
Trang login thật, hoạt động đầy đủ ở cả 2 app (`app/(auth)/login/page.tsx`), dùng `react-hook-form` + `zodResolver(loginSchema)`. Access token CHỈ giữ trong bộ nhớ (`packages/auth/src/token-store.ts`'s `TokenStore` — 1 field của class, không ghi localStorage/sessionStorage — mất khi refresh trang, đúng chủ đích theo AC #46); refresh token là HttpOnly cookie, lấy lại access token qua `POST /auth/refresh` (`credentials:'include'`, `packages/auth/src/token-provider.ts`) — `AuthProvider` tự gọi lại endpoint này khi mount để rehydrate sau khi refresh trang. Kiểm tra quyền qua `hasPermission`/`hasAnyPermission` (`packages/auth/src/permissions.ts`), dùng để lọc menu (`dashboard-nav.tsx`) và bảo vệ toàn bộ layout `(dashboard)` qua `AuthGuard` (redirect về `/login` nếu chưa đăng nhập) — chỉ có ở `admin-web`, `public-web` chưa có tương đương.

## Quyết định không được phá vỡ
- Access token không bao giờ được ghi vào `localStorage`/`sessionStorage` (chỉ giữ in-memory qua `TokenStore`).
- `admin-web`/`public-web` chỉ giao tiếp qua `packages/*` dùng chung, không import chéo source nội bộ của nhau.
- Component UI dùng chung đặt tại `packages/ui`, style/token dùng chung đặt tại `packages/design-system` — không tự ý tạo token màu/spacing riêng trong từng app.
- Type/contract gọi API lấy từ `packages/api-client/src/generated/schema.d.ts` (sinh tự động từ `openapi-typescript` đọc `openapi.json` của backend) — không tự khai type response tay khi đã có type generated tương ứng.
