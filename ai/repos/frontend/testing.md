# Memories Frontend Testing

- Framework: Vitest `^2.0.5` (KHÔNG dùng Jest) + React Testing Library (`@testing-library/react`/`jest-dom`/`user-event`); cấu hình riêng từng app (`apps/{admin-web,public-web}/vitest.config.ts`, môi trường `jsdom`, `globals: true`, setup file `test/setup.ts`).
- Unit/component/e2e boundary: chỉ có unit/component test (`*.spec.ts`/`*.spec.tsx`) đặt tại `test/` của từng app/package — 16 file thật trong toàn repo (2 ở app, 14 ở packages). CHƯA có E2E nào (không có Playwright hay công cụ E2E nào được cấu hình — xác nhận không có `playwright.config.*` và không package nào khai `playwright`).
- API mocking: chưa thấy thư viện mock request chuyên dụng (không có MSW hay tương đương) — test hiện tại mock trực tiếp qua Vitest (`vi.fn()`/module mock) ở boundary hàm/class (ví dụ `http-client.spec.ts`, `media-client.spec.ts`).
- Query/selector policy: dùng Testing Library (`render`, `screen`, `userEvent`) theo convention mặc định của thư viện (query theo role/label/text) — chưa có quy tắc riêng của dự án ngoài việc dùng Testing Library.
- Accessibility/visual test: chưa triển khai (không có axe/jest-axe, không có visual regression/Chromatic/Percy nào trong dự án hiện tại).
- Test bắt buộc cho tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`

## Ghi chú: capture full-page cho trang có scroll-reveal (`.reveal` / `Reveal`)

Các trang dùng pattern scroll-reveal của prototype (`.reveal` + `IntersectionObserver`, xem `prototype/*/*.html`) hoặc component `apps/public-web/components/common/reveal.tsx` (`Reveal`) sẽ giữ phần tử ở `opacity:0` cho tới khi `IntersectionObserver` báo phần tử đã vào viewport. Khi capture screenshot full-page bằng headless Chrome CDP (`Page.captureScreenshot` với `captureBeyondViewport:true`, clip height = `document.scrollHeight`) mà KHÔNG cuộn trang, `IntersectionObserver` root vẫn chỉ là viewport đã set (vd. 900px cao) — mọi phần tử `.reveal`/`Reveal` nằm dưới đó sẽ không bao giờ intersect, nên ảnh chụp full-height vẫn có nội dung/section bị trống (blank band) dù chiều cao ảnh đúng bằng toàn bộ trang.

Cách khắc phục đã kiểm chứng (không cần sửa source): trước khi `Page.navigate`, gọi CDP `Emulation.setEmulatedMedia({features: [{name: 'prefers-reduced-motion', value: 'reduce'}]})`. Cả prototype (`@media (prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none}}`) lẫn `Reveal` (tắt hẳn `IntersectionObserver`, không bao giờ áp class `opacity-0`) đã coi `prefers-reduced-motion: reduce` là fallback hiển thị ngay lập tức — đây là hành vi có sẵn, không phải hack riêng cho capture. Kỹ thuật này cho ảnh cùng-viewport, không cần cuộn, và tái lập được (xem `ai/tasks/MEMORIES-0009/evidence/fidelity-matrix.json` method_notes cho ví dụ đầy đủ).
