# Memories Frontend UI Rules

- Design tokens/components: token màu/radius khai báo dưới dạng CSS custom property tại `packages/design-system/src/tokens.css`, expose qua Tailwind preset dùng chung (`tailwind-preset.js`, `darkMode: 'class'`); component dựng sẵn hiện có trong `packages/ui/src/components`: `Button`, `Card` (+ `CardHeader`/`CardTitle`/`CardContent`), `Input`, `Label`, `Toast` — chưa có dialog/dropdown/select/tabs.
- Responsive breakpoints: dùng breakpoint mặc định của Tailwind (không override riêng trong preset của dự án).
- Accessibility baseline: dựa vào primitive Radix UI có sẵn (`@radix-ui/react-label`, `@radix-ui/react-slot`, `@radix-ui/react-toast`) cho hành vi accessible mặc định (focus management, ARIA) — chưa có tài liệu/checklist a11y riêng của dự án, chưa có test accessibility tự động.
- Drawer/modal/toast conventions: mới chỉ có `Toast` (Radix Toast Provider/Viewport/Root/Title/Description/Close, dùng qua hook `useToast()` — `packages/ui/src/hooks/use-toast.ts`), wired vào `app/providers.tsx` của cả 2 app. Chưa có drawer/modal nào được triển khai.
- Loading/error/empty states: mỗi app dùng quy ước file Next.js App Router (`app/loading.tsx`, `app/error.tsx`, `app/not-found.tsx`) ở cấp root; nhiều trang tính năng hiện là placeholder tĩnh (chỉ heading + 1 câu mô tả ngắn, chưa có loading/empty state thật vì chưa có data fetching) — xem `known-issues.md`.
- UI và interaction của tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`
