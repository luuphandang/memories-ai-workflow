# MEMORIES-0009: Hoàn thiện trang chủ theo prototype

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0009`

## Goal

Tái hiện đầy đủ trang chủ public tại `/` theo `prototype/index/index.html`, bao gồm toàn bộ section,
element, nội dung, responsive layout và interaction có ý nghĩa. Đồng thời sửa search trên header
để giao diện tìm kiếm mở dưới dạng popover/overlay, không chèn thêm hàng vào document flow và
không đẩy toàn bộ nội dung trang xuống dưới.

## Background

Trang chủ hiện chỉ ghép sáu component `Hero`, `TemplatesTeaser`, `GiftsTeaser`,
`CustomOrderBanner`, `TestimonialsSection` và `FinalCta`. Prototype có 11 section nội dung với
nhiều element và trạng thái tương tác hơn. Bản inventory của MEMORIES-0003 mô tả một implementation
rút gọn, không được dùng để biện minh cho việc bỏ bớt element trong task này.

Header dùng chung hiện render form search thành block bên trong `<header>`. Khi mở search, block làm
tăng chiều cao header và gây layout shift cho toàn bộ trang. Search vẫn phải hoạt động nhưng surface
của nó phải nằm ngoài normal flow.

## Current system

- Route trang chủ: `apps/public-web/app/(marketing)/page.tsx`; component tại
  `apps/public-web/components/home/*`.
- Shell dùng chung gồm `SiteHeader`, `SiteFooter`, `MobileBottomNav` và `ShopProvider`.
- Search header hiện điều hướng tới danh mục quà bằng query `q`; cart/favorite dùng `ShopProvider`.
- Routes, mock data, UI primitives, design tokens và asset marketing đã có; ưu tiên tái sử dụng.
- Nguồn chuẩn về nội dung, thứ tự, hierarchy, visual composition và interaction là toàn bộ
  `prototype/index/index.html` cùng `prototype/index/assets/*`.

## Scope

### 1. Inventory và page composition

- [ ] Đọc toàn bộ HTML/CSS/JS prototype và lập mapping element → React component trước khi làm;
  không chỉ dựa vào inventory cũ.
- [ ] Giữ đúng thứ tự 11 section: Hero; Occasions; Templates; Editor introduction; Gifts; QR
  Story; How it works; Custom order; Stories; Blog; Final CTA.
- [ ] Giữ announcement, header, footer, mobile drawer và mobile bottom nav từ shell dùng chung;
  chỉ điều chỉnh khi cần cho fidelity hoặc sửa search.
- [ ] Không bỏ section/card/control vì dùng mock hoặc chưa có trang chi tiết; dùng route khả dụng
  gần nhất hoặc fallback có chủ đích và ghi trong handoff.

### 2. Các element bắt buộc

- [ ] Hero có eyebrow, headline hai dòng, mô tả, hai CTA, ba trust points và toàn bộ collage:
  thiệp mở, polaroid, tem, phong bì, hộp quà, nhánh hoa, ruy băng, nhãn cá nhân hóa.
- [ ] Occasions có heading/mô tả và đủ 8 lựa chọn: Sinh nhật, Đám cưới, Kỷ niệm, Tân gia, Đầy
  tháng, Tốt nghiệp, Cảm ơn, Xin lỗi.
- [ ] Templates có heading, đủ filter tabs, 6 template cards với preview, price/free badge,
  favorite, metadata và CTA xem tất cả.
- [ ] Editor introduction có visual editor/card preview, feature list, copy và CTA.
- [ ] Gifts có heading, đủ 6 gift cards, visual, badge, rating, price, personalization info,
  favorite/add-to-cart và CTA xem tất cả.
- [ ] QR Story có copy, bốn bước/benefit items, badges, CTA và visual hộp quà + QR card/phone.
- [ ] How it works có heading và đủ 3 bước được nối thành flow rõ ràng.
- [ ] Custom order có visual, eyebrow, heading, mô tả, các điểm nổi bật và CTA.
- [ ] Stories có heading, đủ testimonial slides, previous/next và pagination dots.
- [ ] Blog có heading, đủ 3 article cards cùng category, title, excerpt/metadata và link/CTA.
- [ ] Final CTA giữ decoration, copy và hai CTA theo prototype.
- [ ] Footer giữ đầy đủ brand/contact/social, các nhóm link, newsletter validation/feedback và
  bottom bar theo shell/prototype hiện hành.

### 3. Interaction và state

- [ ] Template filters thay đổi danh sách và phản ánh trạng thái bằng `aria-pressed`.
- [ ] Favorite/add-to-cart dùng `ShopProvider`, cập nhật badge/toast nhất quán với catalog, không
  tạo state cục bộ tách rời.
- [ ] Stories slider hỗ trợ previous, next và chọn dot; active state có accessible name/state.
- [ ] Announcement close, mobile menu, newsletter validation và CTA/link tiếp tục hoạt động.
- [ ] Motion/reveal tôn trọng `prefers-reduced-motion`; nội dung không bị ẩn vĩnh viễn nếu
  JavaScript hoặc observer không khả dụng.

### 4. Header search không gây layout shift

- [ ] Giữ search button và submit tới danh mục quà với query `q` hiện tại.
- [ ] Form search là popover/overlay được định vị absolute/fixed/portal và neo hợp lý theo
  trigger/header; không thay đổi chiều cao header, vị trí hero hay scroll position.
- [ ] Surface có layering/kích thước/vị trí phù hợp desktop và mobile, không clipping hoặc che
  control đóng thiết yếu.
- [ ] Focus chuyển hợp lý vào input khi mở; Escape, click ngoài hoặc control đóng sẽ đóng search và
  trả focus về trigger.
- [ ] Trigger có `aria-expanded` và semantics liên kết tới surface; Enter submit được; popover nhỏ
  không khóa body scroll.
- [ ] Không sửa bằng cách xóa button hoặc vô hiệu hóa search.

### 5. Responsive, accessibility và quality

- [ ] Kiểm tra tối thiểu 375x812, 768x1024 và 1440x900; không overflow ngang, overlap, clipping
  hoặc CTA không thao tác được.
- [ ] Duy trì landmark, heading hierarchy, accessible names, keyboard navigation, focus-visible,
  alt/`aria-hidden` đúng và hit target hợp lý.
- [ ] Tái sử dụng Next.js `Image`, routes, mock data, shared UI/design tokens và component hiện có;
  tách component/data rõ ràng thay vì dồn toàn trang vào một file.
- [ ] Bổ sung component tests cho section completeness, filter, favorites/cart, slider và header
  search overlay/focus/dismiss/submit/no-layout-flow regression.
- [ ] Cập nhật knowledge nếu mapping prototype hoặc convention UI bền vững thay đổi.

## Acceptance criteria

- [ ] AC1 — `/` render đủ 11 section đúng thứ tự, không thiếu nhóm element trong Scope.
- [ ] AC2 — Nội dung, hierarchy, màu sắc, typography, spacing, decoration và visual composition
  bám sát prototype ở desktop/tablet/mobile; không thay bằng generic cards.
- [ ] AC3 — Hero đủ copy, CTA, trust points và collage; decoration không overflow/che nội dung.
- [ ] AC4 — Occasions đủ 8 item; Templates và Gifts đều đủ 6 card cùng metadata/control.
- [ ] AC5 — Editor, QR Story, How it works và Blog hiện diện đầy đủ, không phải optional scope.
- [ ] AC6 — Template filters hoạt động/accessibile và không làm hỏng layout.
- [ ] AC7 — Favorite/add-to-cart dùng shared store, cập nhật badge/toast nhất quán.
- [ ] AC8 — Slider hoạt động bằng button/dot; newsletter báo lỗi email sai và success email hợp lệ.
- [ ] AC9 — Mở search không đổi bounding box/chiều cao header, vị trí nội dung dưới hoặc scroll.
- [ ] AC10 — Search overlay responsive, tự focus input, đóng bằng Escape và click ngoài/control,
  trả focus trigger, submit đúng route/query.
- [ ] AC11 — Search button không bị xóa/vô hiệu hóa; form không còn là in-flow row.
- [ ] AC12 — Trang usable tại ba viewport yêu cầu, không overflow/clipping/overlap/hidden controls.
- [ ] AC13 — Semantics, accessible names/state, focus-visible và reduced-motion đạt baseline repo.
- [ ] AC14 — Tests khóa regression completeness/search; `lint`, `typecheck`, `test`, `build` pass.
- [ ] AC15 — Handoff có mapping 11 section, file/asset thay đổi, test và visual evidence trước/sau ở
  ba viewport; mọi sai khác có chủ đích được ghi rõ.

## Out of scope

- Thay đổi backend/API/database hoặc xây CMS.
- Xây blog/article, checkout, order lookup hay destination mới chỉ để mọi CTA có trang riêng.
- Redesign toàn diện shell của route khác ngoài phần search dùng chung và regression liên quan.
- Thay contract search catalog hoặc xây suggestions/autocomplete/backend search.
- Sao chép nguyên khối HTML/CSS/JS, iframe hoặc `dangerouslySetInnerHTML` để né kiến trúc React.

## Technical notes

- Source of truth: `prototype/index/index.html` và hai logo trong `prototype/index/assets/`.
- Entry point: `apps/public-web/app/(marketing)/page.tsx`; component area:
  `apps/public-web/components/home/*`.
- Shared search/shell: `components/site-header.tsx`, `site-footer.tsx`,
  `mobile-bottom-nav.tsx`, `app/(marketing)/layout.tsx`.
- Reuse `lib/routes.ts`, `lib/store/shop-store.tsx`, mock template/gift/review và
  `public/marketing/*` khi phù hợp.
- Prototype là chuẩn completeness. Inline SVG/CSS decoration có thể chuyển thành React component
  hoặc asset tương đương, miễn visual và semantics không bị giản lược.
- Với search, header có thể làm positioning context; popover phải ngoài normal flow. Test nên xác
  nhận geometry header/content trước và sau khi mở ngoài behavioral test.

## Validation

```text
npm run lint
npm run typecheck
npm run test
npm run build
```

Handoff phải kèm visual capture/inspection 375x812, 768x1024 và 1440x900 cho trang chủ ở trạng thái
mặc định và search mở.

## Constraints

- Không quản lý worktree/branch, commit hoặc push.
- Không đọc secret hoặc `.env*`.
- Không sửa ngoài frontend worktree, trừ task artifact/report do workflow quản lý.
