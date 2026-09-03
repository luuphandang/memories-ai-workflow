# Memories Frontend UI Rules

- Design tokens/components: token màu/radius khai báo dưới dạng CSS custom property tại `packages/design-system/src/tokens.css`, expose qua Tailwind preset dùng chung (`tailwind-preset.js`, `darkMode: 'class'`); component dựng sẵn hiện có trong `packages/ui/src/components`: `Button`, `Card` (+ `CardHeader`/`CardTitle`/`CardContent`), `Input`, `Label`, `Toast` — chưa có dialog/dropdown/select/tabs.
- Responsive breakpoints: dùng breakpoint mặc định của Tailwind (không override riêng trong preset của dự án).
- Accessibility baseline: dựa vào primitive Radix UI có sẵn (`@radix-ui/react-label`, `@radix-ui/react-slot`, `@radix-ui/react-toast`) cho hành vi accessible mặc định (focus management, ARIA) — chưa có tài liệu/checklist a11y riêng của dự án, chưa có test accessibility tự động.
- Drawer/modal/toast conventions: mới chỉ có `Toast` (Radix Toast Provider/Viewport/Root/Title/Description/Close, dùng qua hook `useToast()` — `packages/ui/src/hooks/use-toast.ts`), wired vào `app/providers.tsx` của cả 2 app. Chưa có drawer/modal nào được triển khai.
- Loading/error/empty states: mỗi app dùng quy ước file Next.js App Router (`app/loading.tsx`, `app/error.tsx`, `app/not-found.tsx`) ở cấp root; nhiều trang tính năng hiện là placeholder tĩnh (chỉ heading + 1 câu mô tả ngắn, chưa có loading/empty state thật vì chưa có data fetching) — xem `known-issues.md`.
- UI và interaction của tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`

## Cập nhật (MEMORIES-0009): Dialog/Drawer/Popover đã tồn tại, không chỉ Toast

Dòng "Drawer/modal/toast conventions" ở trên ("mới chỉ có Toast ... Chưa có drawer/modal nào được triển khai") đã lỗi thời. `packages/ui/src/components` hiện có cả bốn: `Toast`, `Dialog` (modal căn giữa, portal `document.body`, focus-trap, khóa scroll), `Drawer` (panel trượt cạnh, portal `document.body`, khóa scroll) và `Popover` (surface neo tuyệt đối `absolute` vào phần tử cha `position: relative` gần nhất — KHÔNG portal). Cả `Dialog`/`Drawer`/`Popover` dùng chung hook `packages/ui/src/hooks/use-dismissable-layer.ts` (`useDismissableLayer`) để: focus-trap Tab bên trong, đóng bằng Escape, và trả focus về phần tử đã mở layer khi đóng.

`Popover` (mở rộng bởi MEMORIES-0009) nhận thêm các prop tùy chọn sau, mặc định giữ nguyên hành vi cũ cho mọi call site hiện có:
- `role?: 'menu' | 'dialog'` (mặc định `'menu'`) — dùng `'dialog'` khi nội dung là form/control tuỳ ý (không phải danh sách `<PopoverItem>` menuitem).
- `lockScroll?: boolean` (mặc định `true`, giống `Dialog`/`Drawer`) — đặt `false` cho surface nhỏ không được khóa cuộn trang nền (vd. overlay tìm kiếm neo trên header).
- `id?: string` — để một trigger button trỏ `aria-controls` vào đúng surface.

Lưu ý bổ sung (review cycle 1): khi anchor wrapper của `Popover` chỉ bọc riêng trigger thay vì cả cụm action-icon chứa nó, surface căn `align="end"` có thể tràn ra ngoài viewport ở màn hình hẹp nếu còn control khác nằm bên phải trigger trong cùng hàng — hãy đặt `Popover` bên trong cụm `relative` bao ngoài cùng (không phải wrapper riêng của trigger) khi hàng chứa nhiều icon. Ví dụ: `apps/public-web/components/site-header.tsx`'s search overlay dùng `<Popover id={...} role="dialog" lockScroll={false} anchorRef={...} ...>` là con cuối cùng của `<div className="relative ml-auto flex items-center gap-0.5">` bọc toàn bộ cụm icon (search/heart/user/cart/CTA), không chỉ bọc riêng nút trigger — cùng khuôn mẫu `relative` wrapper + `Popover` mà `UserMenuTrigger`/`AccountPopover` đã dùng cho menu tài khoản, mở rộng để an toàn ở mọi breakpoint.
