# MEMORIES-0011: Tích hợp API card và product vào trang chủ

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0011`
- Repository triển khai: `frontend`
- Route chính: `/`

## Goal

Thay dữ liệu mock của hai khu vực `Mẫu thiệp` và `Quà kỷ niệm` trên homepage public bằng dữ liệu
thật từ các API card-template và product đã có. Trang chủ phải giữ nguyên bố cục, visual hierarchy,
responsive behavior và các interaction hiện hành, đồng thời biểu diễn trung thực mọi trạng thái
loading, error, empty và dữ liệu tùy chọn bị thiếu.

## Background

Homepage đã được hoàn thiện về giao diện và hành vi trong task trước, nhưng
`TemplatesTeaser` vẫn đọc `CARD_TEMPLATES` và `GiftsTeaser` vẫn đọc `GIFT_PRODUCTS`. Backend và
frontend đã có sẵn contract typed, API client, TanStack Query hooks và mapper cho hai catalog; các
trang `/mau-thiep` và `/qua-ky-niem` đã dùng luồng này. MEMORIES-0011 đưa homepage vào cùng nguồn dữ
liệu, tránh duy trì một bản catalog mock riêng và tránh nội dung homepage lệch khỏi dữ liệu backend.

## Current system

- Homepage được compose tại `apps/public-web/app/(marketing)/page.tsx`; hai component cần tích hợp
  nằm tại `components/home/templates-teaser.tsx` và `components/home/gifts-teaser.tsx`.
- `Providers` ở app root đã cung cấp `QueryProvider` và `ApiClientProvider`; marketing layout đã
  cung cấp `ShopProvider` cho favorite và cart.
- `useCardTemplates` gọi public `GET /card-templates`; `useProducts` gọi public `GET /products`.
  Cả hai dùng generated OpenAPI types, query-key factory, request cancellation và cache policy
  chung của repo.
- `mapCardTemplate` và `mapProduct` chuyển API response sang view model mà các component hiện tại
  sử dụng. Mapper đã xử lý catalog terms, màu, access tier, variant, ảnh và rating nullable.
- Hai teaser hiện render tối đa 6 card theo grid `1/2/3` cột và dùng `ShopProvider` cho favorite/
  add-to-cart. Các section khác của homepage không phụ thuộc catalog API.

## Scope

### 1. Nguồn dữ liệu và contract truy vấn

- [ ] Thay hoàn toàn dependency runtime của `TemplatesTeaser` vào `CARD_TEMPLATES` bằng
  `useCardTemplates({ sortBy: 'popular', page: 1, pageSize: 6 })` và map từng item qua
  `mapCardTemplate`.
- [ ] Thay hoàn toàn dependency runtime của `GiftsTeaser` vào `GIFT_PRODUCTS` bằng
  `useProducts({ sortBy: 'popular', page: 1, pageSize: 6 })` và map từng item qua `mapProduct`.
- [ ] Giữ nguyên thứ tự do API trả về và không render quá 6 item trong mỗi teaser. Không dùng mock
  làm fallback khi API lỗi hoặc trả rỗng, không gọi `fetch` trực tiếp và không tạo API/query layer
  song song với typed client, hook, mapper và query keys hiện có.
- [ ] Hai query hoạt động độc lập: lỗi hoặc empty ở một teaser không được làm mất teaser còn lại hay
  làm hỏng các section tĩnh khác trên homepage.

### 2. Trạng thái UI và dữ liệu tùy chọn

- [ ] Mỗi teaser có initial loading skeleton/status phù hợp grid hiện tại; loading phải có accessible
  status và giữ kích thước section đủ ổn định để hạn chế layout shift.
- [ ] Khi request lỗi, chỉ section tương ứng hiển thị thông báo lỗi tiếng Việt và nút `Thử lại` gọi
  đúng query `refetch`; không hiển thị dữ liệu mock cũ như thể request thành công.
- [ ] Khi request thành công nhưng `items` rỗng, hiển thị empty state rõ ràng và giữ CTA điều hướng
  tới catalog đầy đủ tương ứng.
- [ ] Khi background refetch, tiếp tục hiển thị dữ liệu gần nhất theo cache/`keepPreviousData` và có
  feedback cập nhật không gây thay toàn bộ grid bằng skeleton.
- [ ] Card template dùng dữ liệu API cho tên, dịp, phong cách, access tier, metadata và visual đã map.
  API hiện không có giá template bằng số nên chỉ hiển thị `Miễn phí` hoặc `Cao cấp`; không giữ hoặc
  tự suy diễn giá từ mock.
- [ ] Gift card xử lý an toàn `image`, `ratingAverage`, `description` và `variant` nullable. Sản phẩm
  không có available variant phải hiện trạng thái không khả dụng, không được thêm vào cart và không
  được biến giá thiếu thành `0₫`; ảnh/rating thiếu có fallback UI có accessible name.

### 3. Interaction và không regression homepage

- [ ] Filter style của template chỉ lọc trên các item API đã tải, dùng giá trị `style` đã map và
  giữ `aria-pressed`. Danh sách tab gồm `Tất cả` cộng các style khác nhau thực sự có trong response;
  không đọc style/card từ mock. Nếu refetch loại bỏ style đang chọn, selection phải trở về trạng
  thái hợp lệ thay vì để grid rỗng do state stale.
- [ ] Preview template, favorite template/product và add-to-cart tiếp tục nhận chính object/id đã
  map từ API và dùng `ShopProvider`; favorite/cart badge hiện hành vẫn cập nhật đúng.
- [ ] CTA `Xem tất cả mẫu thiệp` và `Khám phá tất cả quà kỷ niệm` giữ đúng route hiện tại ở mọi
  trạng thái success, loading, error và empty.
- [ ] Giữ nguyên thứ tự 11 homepage sections, heading hierarchy, template/gift card composition,
  grid responsive, keyboard operability và semantics hiện có; không redesign các section khác.

### 4. Tests và handoff

- [ ] Cập nhật test homepage để chạy qua QueryProvider/ApiClientProvider với API fixture kiểm soát
  được, chứng minh request dùng `sortBy=popular`, `page=1`, `pageSize=6` và UI render dữ liệu đã map
  thay vì fixture mock production.
- [ ] Test success, initial loading, background refetch, error + retry, empty response, hai query độc
  lập và các field nullable quan trọng của cả hai teaser.
- [ ] Giữ hoặc cập nhật regression tests cho section order, filter/`aria-pressed`, preview,
  favorite, add-to-cart, CTA, responsive grid và giới hạn tối đa 6 card.
- [ ] Chạy đầy đủ `lint`, `typecheck`, `test`, `build`; handoff liệt kê exact changed files, kết quả
  validation và mọi quyết định có chủ đích. Cập nhật knowledge chỉ khi phát sinh convention bền vững.

## Acceptance criteria

- [ ] AC1 — Homepage gọi `GET /card-templates` qua typed client/query hook với
  `sortBy=popular&page=1&pageSize=6`, map response thật và không còn runtime dependency vào
  `CARD_TEMPLATES` trong template teaser.
- [ ] AC2 — Homepage gọi `GET /products` qua typed client/query hook với
  `sortBy=popular&page=1&pageSize=6`, map response thật và không còn runtime dependency vào
  `GIFT_PRODUCTS` trong gift teaser.
- [ ] AC3 — Mỗi teaser render đúng thứ tự API và tối đa 6 item; template filter được tạo/lọc từ
  response thật, còn preview/favorite/cart dùng đúng object/id đã map và shared store.
- [ ] AC4 — Initial loading, background refetch, error có retry và empty response đều có UI rõ
  ràng, accessible; trạng thái của hai teaser độc lập và tuyệt đối không fallback sang mock.
- [ ] AC5 — Template không bịa giá ngoài contract; product có image/rating/variant nullable được
  render trung thực, và product không có available variant không thể thêm vào cart.
- [ ] AC6 — Toàn bộ 11 section, heading/CTA, template/gift composition, grid responsive và các
  interaction homepage hiện có không regression ngoài nội dung động do API quyết định.
- [ ] AC7 — Automated tests chứng minh query params, mapping, giới hạn 6 item, success/loading/
  refetch/error/retry/empty/nullable/independent-query behavior và shared-store interactions.
- [ ] AC8 — `lint`, `typecheck`, `test`, `build` của frontend đều pass; handoff và evidence thuộc
  đúng source state hiện tại theo workflow.

## Out of scope

- Thay đổi backend controller, use case, repository, database schema, migration, seed hoặc OpenAPI
  contract; nếu phát hiện contract gap thì ghi blocker thay vì tự mở rộng backend.
- Tạo endpoint homepage/featured mới, thay đổi thuật toán `popular`, thêm CMS hoặc server-side
  personalization.
- Tích hợp API cho Occasions, Testimonials, Blog, cart persistence, checkout hoặc các section khác.
- Xây pagination, search hoặc full facet filtering trên homepage; các chức năng đó tiếp tục thuộc
  hai trang catalog đầy đủ.
- Sửa tay `packages/api-client/src/generated/schema.d.ts` hoặc giữ mock catalog làm silent fallback.
- Redesign homepage, thay design tokens hoặc thay đổi route/destination hiện hành.

## Technical notes

- Reuse trực tiếp: `lib/queries/use-card-templates.ts`, `lib/queries/use-products.ts`,
  `lib/api/map-card-template.ts`, `lib/api/map-product.ts` và shared query keys.
- Public endpoints không cần auth header. AbortSignal, retry và cache tiếp tục do `ApiClient` và
  TanStack Query quản lý; component không tự tạo request lifecycle khác.
- Có thể tái sử dụng `CatalogSkeletonGrid`, `ErrorState`, `EmptyState` hoặc tạo biến thể homepage nhỏ
  nếu cần giữ composition `1/2/3` cột; ưu tiên shared component thay vì copy behavior.
- Unit/component test nên dùng fetch fixture qua provider thật như các catalog tests, không mock
  `useCardTemplates`/`useProducts` theo cách bỏ qua serialization, mapper hoặc query state.
- `CardTemplate.id`/`GiftProduct.id` từ API là identity canonical cho favorite, preview và cart.

## Validation

Chạy từ `worktrees/MEMORIES-0011/frontend`:

```text
npm run lint
npm run typecheck
npm run test
npm run build
```

## Constraints

- Chỉ sửa source trong `worktrees/MEMORIES-0011/frontend` và task artifacts do workflow quản lý.
- Không quản lý worktree/branch, commit hoặc push.
- Không đọc secret hoặc `.env*`; không ghi credential/token vào client, fixture hoặc evidence.
- Không sửa trực tiếp `ai/shared`, `ai/repos` hoặc `ai/domains`; knowledge update đi qua workflow.
