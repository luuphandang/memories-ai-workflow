# Memories Frontend Testing

- Framework: Vitest `^2.0.5` (KHÔNG dùng Jest) + React Testing Library (`@testing-library/react`/`jest-dom`/`user-event`); cấu hình riêng từng app (`apps/{admin-web,public-web}/vitest.config.ts`, môi trường `jsdom`, `globals: true`, setup file `test/setup.ts`).
- Unit/component/e2e boundary: chỉ có unit/component test (`*.spec.ts`/`*.spec.tsx`) đặt tại `test/` của từng app/package — 16 file thật trong toàn repo (2 ở app, 14 ở packages). CHƯA có E2E nào (không có Playwright hay công cụ E2E nào được cấu hình — xác nhận không có `playwright.config.*` và không package nào khai `playwright`).
- API mocking: chưa thấy thư viện mock request chuyên dụng (không có MSW hay tương đương) — test hiện tại mock trực tiếp qua Vitest (`vi.fn()`/module mock) ở boundary hàm/class (ví dụ `http-client.spec.ts`, `media-client.spec.ts`).
- Query/selector policy: dùng Testing Library (`render`, `screen`, `userEvent`) theo convention mặc định của thư viện (query theo role/label/text) — chưa có quy tắc riêng của dự án ngoài việc dùng Testing Library.
- Accessibility/visual test: chưa triển khai (không có axe/jest-axe, không có visual regression/Chromatic/Percy nào trong dự án hiện tại).
- Test bắt buộc cho tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`
