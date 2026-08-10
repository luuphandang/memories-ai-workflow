# MEMORIES-0004: Catalog, Taxonomy & Faceted Filtering Implementation

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0004`

## Goal

Triển khai nền tảng catalog, taxonomy và faceted filtering dùng dữ liệu thật cho hai miền mẫu thiệp và quà kỷ niệm, xuyên suốt PostgreSQL/NestJS API tới Next.js public web.

Kết quả phải cho phép quản trị dữ liệu tham chiếu bằng mã ổn định, gắn nhiều giá trị vào template/sản phẩm, truy vấn danh sách có lọc/sắp xếp/phân trang và nhận facet kèm số lượng. Hai route `/mau-thiep` và `/qua-ky-niem` phải bỏ nguồn mock cục bộ cho danh sách và bộ lọc, sử dụng contract OpenAPI được sinh từ backend.

## Background

Phạm vi Epic phân biệt ba loại dữ liệu:

1. Catalog/taxonomy được quản trị tập trung và tái sử dụng: `occasion`, `card_style`, `product_category`, `recipient_segment`, `material`.
2. Mô hình lai: `card_format`, `color_family`, `personalization_capability`; giá trị chuẩn là dữ liệu tham chiếu nhưng hỗ trợ thực tế nằm trên template/sản phẩm.
3. Thuộc tính hoặc dữ liệu dẫn xuất: access tier/giá, preparation time/rush, tồn kho và rating; đây là facet truy vấn, không phải catalog độc lập.

`occasion` phải được dùng chung giữa thiệp và quà. Quan hệ mang bản chất nhiều-nhiều; category sản phẩm hỗ trợ cây cha-con. Giá và rating phải được lọc từ dữ liệu nguồn hoặc trường tổng hợp hiện hành, không tạo bảng bucket tĩnh.

## Current system

- Backend là NestJS 10 monorepo theo Clean Architecture, PostgreSQL + TypeORM; business module nằm trong `libs/modules`, schema chỉ thay đổi qua migration và cross-module import chỉ qua `public-api.ts`.
- Backend hiện chưa có bounded context catalog/card/product và chưa có list endpoint thật sử dụng primitive phân trang.
- Frontend là Next.js 14 App Router monorepo. `public-web` đã có giao diện `/mau-thiep` và `/qua-ky-niem` từ MEMORIES-0003 nhưng đang dùng typed mock/local state.
- Frontend đã có `ApiClient`, TanStack Query và query-key factory; type API phải sinh từ `openapi.json`, không viết tay khi contract đã tồn tại.
- Không có CMS/admin catalog trong phạm vi Epic này.

## Phạm vi đường dẫn

- Prototype hành vi/nhãn hiển thị: `prototype/mau-thiep/mau-thiep.html` và `prototype/qua-ky-niem/qua-ky-niem.html`.
- Backend được phép sửa: `worktrees/MEMORIES-0004/backend`.
- Frontend được phép sửa: `worktrees/MEMORIES-0004/frontend`.
- UI hiện hữu từ MEMORIES-0003 là baseline; không redesign hai trang catalog ngoài thay đổi cần thiết cho loading/error/empty/filter state và tích hợp API.

## Scope

### 1. Domain model, schema và seed data

- [ ] Tạo bounded context/module phù hợp cho catalog và dữ liệu có thể duyệt của card template/product theo đúng 4 lớp hiện có; không đặt logic nghiệp vụ trong controller hoặc ORM entity.
- [ ] Tạo migration cho các catalog chuẩn hóa: occasion dùng chung, card style, product category phân cấp, recipient segment, material, card format/capability, color family và personalization capability.
- [ ] Mỗi catalog có tối thiểu `id`, `code` hoặc `slug` ổn định, tên hiển thị, `status`, `sort_order`, timestamps phù hợp convention; taxonomy phân cấp có `parent_id` nullable và ràng buộc chống self-parent/quan hệ không hợp lệ ở mức phù hợp.
- [ ] Tạo model/bảng tối thiểu cho card template, product và sellable variant/offer đủ để phục vụ hai trang; không xây dựng toàn bộ commerce lifecycle.
- [ ] Tạo quan hệ nhiều-nhiều template/product với catalog; hỗ trợ `is_primary` hoặc trọng số cho occasion, style, recipient và các quan hệ cần xác định giá trị chính/độ phù hợp; bổ sung uniqueness/index phục vụ join/filter.
- [ ] Lưu access tier trên template; giá hiệu lực trên variant/offer; preparation min/max, fulfillment mode và rush trên product/variant; rating average/count là dữ liệu tổng hợp nullable. Không tạo catalog cho price range, preparation bucket hoặc rating bucket.
- [ ] Seed idempotent bộ dữ liệu phát triển tương ứng dữ liệu hợp lệ đang hiển thị ở frontend/prototype, dùng code/slug tiếng Anh ổn định và nhãn tiếng Việt; phân loại category, material, personalization capability và collection đúng mô hình đã nêu trong Epic thay vì chép nguyên nhãn prototype sai nhóm.

### 2. Public read API và facet semantics

- [ ] Cung cấp endpoint public đọc metadata/options catalog cần cho UI, chỉ trả item `active`, theo `sort_order` ổn định.
- [ ] Cung cấp endpoint danh sách card template và product với pagination, deterministic sort, tìm kiếm và multi-select filters tương ứng hai prototype.
- [ ] Response list trả items, metadata phân trang và facet groups/options có `count`; định nghĩa rõ count theo kết quả sau khi áp dụng các filter khác trong cùng query để UI có thể hiển thị option còn khả dụng.
- [ ] Card filters tối thiểu: occasion, style, format/capability, color family và access tier.
- [ ] Product filters tối thiểu: category (có quy tắc descendant), occasion, recipient segment, personalization capability, material, effective price range, preparation range, rush support và minimum rating.
- [ ] Multi-value trong cùng facet dùng OR; giữa các facet dùng AND. Quan hệ nhiều-nhiều không được làm trùng item/count.
- [ ] Price range dùng khoảng nửa mở `[min, max)`, cho phép thiếu một đầu; filter theo effective/current price của variant khả dụng. Preparation lọc bằng số ngày/SLA hiện hành, tách khỏi `supportsRush`.
- [ ] Search chuẩn hóa whitespace/case, input enum/slug/range/sort/pagination được validate; slug không tồn tại trả danh sách rỗng và facet nhất quán, còn query sai kiểu/range mâu thuẫn trả lỗi validation chuẩn.
- [ ] Không bắt buộc JWT cho public read endpoints; vẫn áp dụng global validation, error shape và rate limit hiện hữu.
- [ ] Controller/DTO có Swagger đầy đủ; export `openapi.json` và xác minh contract sau thay đổi.

### 3. Frontend API integration

- [ ] Sinh lại `packages/api-client/src/generated/schema.d.ts` từ OpenAPI backend; không sửa file generated bằng tay.
- [ ] Bổ sung typed API wrapper cho catalog/card/product list, query serialization nhiều giá trị/range/pagination và response/error handling theo convention `ApiClient`.
- [ ] Dùng TanStack Query với query key chứa toàn bộ normalized filter/search/sort/page state; request cũ phải được hủy hoặc không được ghi đè kết quả mới khi người dùng đổi filter nhanh.
- [ ] URL search params là nguồn trạng thái có thể chia sẻ/khôi phục cho filter, search, sort và page; giá trị URL không hợp lệ được bỏ qua hoặc chuẩn hóa an toàn, không làm crash/hydration mismatch.
- [ ] Tích hợp `/mau-thiep` và `/qua-ky-niem` với API thật, giữ layout/design hiện hữu; render filter options/count từ response thay vì mảng nhãn hard-code.
- [ ] Có loading, background refresh, API error + retry, empty state và zero-count/disabled option hợp lý; đổi filter/search/sort reset về trang đầu.
- [ ] Quick-view/product card/template card dùng dữ liệu API và xử lý trường optional/ảnh thiếu an toàn. Cart, checkout và mutation quản trị vẫn là mock/ngoài phạm vi.
- [ ] Không lưu access token hoặc dữ liệu nhạy cảm trong browser storage; public endpoints không được thêm auth workaround.

### 4. Test, contract và documentation

- [ ] Backend unit test domain/use case/repository boundary; integration/e2e chạy migration thật và kiểm tra list/filter/facet/count, taxonomy dùng chung, duplicate join, range boundary, invalid query và public access.
- [ ] Frontend test API wrapper/query serialization và component integration cho URL state, multi-filter, pagination reset, loading/error/empty, stale response và facet count.
- [ ] Chạy backend `lint`, `typecheck`, `test`, `test:architecture`, `test:e2e`, `build`, `export:openapi`; frontend `lint`, `typecheck`, `test`, `build`.
- [ ] Cập nhật repository/domain knowledge nếu implementation tạo quyết định bền vững về schema, API hoặc facet semantics.

## Acceptance criteria

1. Migration từ database rỗng chạy thành công, rollback theo convention hoạt động và `synchronize` vẫn tắt ở mọi môi trường.
2. Các catalog chuẩn hóa và quan hệ được tạo đúng ba nhóm dữ liệu trong phần Background; không tồn tại catalog độc lập cho price bucket, preparation bucket hoặc rating bucket.
3. `occasion` là một nguồn dữ liệu dùng chung cho card template và product; một item có thể gắn nhiều occasion và một occasion có thể gắn nhiều item.
4. Product category hỗ trợ cây cha-con; filter category có hành vi descendant được định nghĩa, test và không trả item trùng.
5. Code/slug catalog là duy nhất và ổn định; public API chỉ trả item active theo thứ tự xác định.
6. Seed development idempotent, có đủ dữ liệu cho hai trang và phân loại đúng các khái niệm category, material, personalization capability và collection theo yêu cầu của Epic.
7. Card list API hỗ trợ đầy đủ occasion, style, format/capability, color family, access tier, search, sort và pagination.
8. Product list API hỗ trợ category, occasion, recipient, personalization, material, effective price, preparation, rush, minimum rating, search, sort và pagination.
9. Trong một facet, nhiều giá trị kết hợp OR; giữa các facet kết hợp AND; count/item không bị nhân bản bởi many-to-many join.
10. Price dùng effective price và khoảng `[min,max)`; preparation range và rush là hai điều kiện độc lập; rating chưa có review được phân biệt với 0.
11. Mỗi list response có pagination metadata và facet counts nhất quán với query/filter semantics đã định nghĩa, bao gồm empty result và zero-count option.
12. Invalid pagination/sort/range/filter format trả lỗi validation theo error contract; slug hợp lệ về cú pháp nhưng không tồn tại không gây 500.
13. Public read endpoints truy cập được không cần access token và vẫn xuất hiện đầy đủ trong OpenAPI với DTO/schema đúng.
14. Frontend generated types được tái sinh từ OpenAPI và typed wrapper không định nghĩa lại response contract bằng type thủ công.
15. `/mau-thiep` và `/qua-ky-niem` lấy items, option và count từ backend; không còn dùng mock catalog làm nguồn runtime chính.
16. Filter/search/sort/page được phản ánh trong URL, khôi phục đúng khi reload/back/forward; đổi điều kiện lọc reset page về 1.
17. Multi-select filter, loading/refresh, retryable error, empty state, ảnh/field optional và thay đổi query nhanh hoạt động không crash hoặc hiển thị kết quả cũ đè query mới.
18. Hai trang giữ visual hierarchy và responsive/accessibility baseline từ MEMORIES-0003; filter control dùng được bằng bàn phím và có accessible name/state.
19. Backend và frontend test bao phủ các rule rủi ro nêu trên; toàn bộ validation command khai báo trong task đều pass.
20. Thay đổi chỉ nằm trong hai worktree khai báo, không commit/push và không đọc/ghi secret.

## Out of scope

- UI/API quản trị CRUD catalog, RBAC, audit log và editorial workflow.
- Tích hợp search engine ngoài PostgreSQL, recommendation, analytics hoặc SEO landing page tự động.
- Checkout, payment, shipping, inventory reservation, review submission hoặc thuật toán cập nhật rating production.
- Product detail/card editor, cart persistence và các mutation commerce khác.
- Dynamic pricing/promotion engine, đa tiền tệ hoặc SLA theo tải xưởng/thời điểm; Epic chỉ mô hình hóa dữ liệu hiện hành cần cho facet.
- Collection/rule engine đầy đủ; có thể hoãn collection nếu không cần để tái hiện chính xác hai catalog page.
- Redesign UI ngoài các trạng thái cần cho tích hợp dữ liệu thật.

## Technical notes

- Backend module dự kiến: `libs/modules/catalog` hoặc các bounded context tách nhỏ nếu execution plan chứng minh cần thiết; export duy nhất qua `public-api.ts` và đăng ký composition root đúng process.
- Migration: `libs/platform/database/src/migrations`; snake_case, FK/unique/check/index rõ ràng, không dùng runtime entity glob.
- API đề xuất dưới `/api/v1/catalogs`, `/api/v1/card-templates`, `/api/v1/products`; implementer có thể tinh chỉnh resource path trước khi khóa OpenAPI nhưng frontend phải dùng đúng generated contract.
- Pagination dùng primitive `PaginatedResult<T>` hiện có hoặc mở rộng tương thích; sort luôn có tie-breaker ID để kết quả ổn định.
- Facet count nên được tính trong query/repository có test SQL/integration; tránh tải toàn bộ dataset về application để lọc/count trong memory.
- Frontend owner: feature component trong `apps/public-web`; API contract/wrapper trong `packages/api-client`; query key theo `packages/query`; không đưa component nghiệp vụ vào `packages/ui`.
- Không sửa trực tiếp generated OpenAPI types; backend export contract trước, frontend generate sau.
- Khi schema thực tế của product/card từ MEMORIES-0003 khác mô hình trong Epic, giữ compatibility UI và ghi quyết định trong execution plan/domain knowledge, không âm thầm thu hẹp filter.

## Constraints

- Không quản lý worktree/branch.
- Không commit hoặc push.
- Không đọc secret hoặc file `.env*`.
- Không sửa ngoài hai worktree khai báo.
- Không sửa prototype hoặc dùng prototype làm runtime dependency.
