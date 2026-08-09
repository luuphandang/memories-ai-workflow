# MEMORIES-0003: [FE] Implement Prototype Pages into Next.js Frontend

## Jira

* Type: `epic`
* Parent: `-`
* Epic: `MEMORIES-0003`

## Goal

Chuyển đổi toàn bộ prototype hợp lệ trong `prototype/<ten-trang>/` thành các page Next.js App Router trong `worktrees/MEMORIES-0003/frontend/apps/public-web`.

Việc triển khai phải bắt đầu bằng nền tảng giao diện dùng chung (design tokens, typography, spacing, shared style và component), sau đó mới xây dựng từng page. Không chuyển từng file HTML thành một component độc lập chứa CSS/JavaScript sao chép từ prototype.

Kết quả phải giữ được ngôn ngữ thiết kế LUUMORY, nội dung, responsive layout và các tương tác chính của prototype; sử dụng mock data có kiểu dữ liệu rõ ràng trong thời gian chưa tích hợp backend.

## Source of truth và phạm vi đường dẫn

* Prototype tham chiếu: `prototype/` tại workspace root.
* Source code được phép triển khai: `worktrees/MEMORIES-0003/frontend`.
* Ứng dụng đích: `worktrees/MEMORIES-0003/frontend/apps/public-web`.
* Component primitive dùng chung giữa nhiều app: `worktrees/MEMORIES-0003/frontend/packages/ui`.
* Design tokens và Tailwind preset: `worktrees/MEMORIES-0003/frontend/packages/design-system`.
* Không thay đổi UI hoặc token mặc định của `apps/admin-web` ngoài phạm vi cần thiết để giữ build tương thích.
* Không tham chiếu runtime từ frontend về thư mục `prototype`; prototype chỉ là nguồn thiết kế và dữ liệu tham chiếu.
* Logo chính thức của frontend là `prototype/logo/logo.png`; bản dùng runtime phải được đặt tại `apps/public-web/public/brand/memories-logo.png` và không được thay bằng logo khác nằm rải rác trong các prototype con.
* Tên thương hiệu khi triển khai là `MEMORIES`. Mọi nội dung, metadata, structured data, manifest, accessible label, tên asset mới và mock copy lấy từ prototype phải đổi `LUUMORY`/`Luumory`/`luumory` thành `MEMORIES`/`Memories`/`memories` theo đúng ngữ cảnh. Không sửa file prototype nguồn.

## Prototype inventory và route bắt buộc

| Prototype | Route Next.js | Layout | Ghi chú |
|---|---|---|---|
| `prototype/index/index.html` | `/` | Public site | Trang chủ |
| `prototype/mau-thiep/mau-thiep.html` | `/mau-thiep` | Public site | Danh sách/lọc mẫu thiệp |
| `prototype/qua-ky-niem/qua-ky-niem.html` | `/qua-ky-niem` | Public site | Danh sách/lọc/quick-view quà |
| `prototype/dat-lam-rieng/dat-lam-rieng.html` | `/dat-lam-rieng` | Public site | Form nhiều bước đặt làm riêng |
| `prototype/gio-hang/gio-hang.html` | `/gio-hang` | Public site | Giỏ hàng mock và tổng kết đơn |
| `prototype/tao-thiep/Tao-thiep.dc.html` cùng `luumory-app.js`, `support.js` | `/tao-thiep` | Editor riêng | Editor toàn màn hình, không bắt buộc dùng public header/footer |

Các link trong prototype trỏ đến route chưa có trong bảng trên phải được cấu hình rõ là placeholder/disabled hoặc dẫn đến `not-found`; không tạo thêm page ngoài phạm vi chỉ để làm link trông như đã hoạt động.

## Nguyên tắc kiến trúc

1. Ưu tiên Server Component; chỉ đặt `"use client"` tại boundary thực sự cần state, browser API hoặc event handler.
2. Page chịu trách nhiệm composition và metadata; không chứa một khối lớn markup, CSS hoặc mock data.
3. Primitive trung tính, có thể dùng cho cả public/admin, đặt trong `packages/ui`; component mang thương hiệu hoặc nghiệp vụ public đặt trong `apps/public-web/components` hoặc feature tương ứng.
4. Dùng CSS custom properties và Tailwind preset từ `packages/design-system`; không tạo một bộ token riêng trong mỗi page.
5. Token LUUMORY cho public site phải được scope bằng theme/class hoặc layout public nếu việc thay token `:root` có thể làm thay đổi admin.
6. State tạm thời phục vụ demo có thể đặt ở client component/hook; không thêm Redux/Zustand khi chưa có nhu cầu kiến trúc rõ ràng.
7. Không dùng `document.querySelector`, `getElementById`, inline `onclick`, `innerHTML` hoặc chèn nguyên script prototype để điều khiển UI.

## Thứ tự triển khai bắt buộc

### 1. Inventory và mapping

* [ ] Đọc đủ 6 prototype và các file JavaScript/tài nguyên đi kèm.
* [ ] Ghi mapping prototype → route → layout → feature/component → interaction → asset/mock data.
* [ ] Xác định phần trùng lặp và khác biệt có chủ đích giữa header/footer/style của các prototype.
* [ ] Dùng `prototype/qua-ky-niem/qua-ky-niem.html` làm nguồn chính cho public header/footer; chỉ lấy bổ sung từ prototype khác khi không xung đột.
* [ ] Ghi rõ các hành vi không thể hoặc không nên chuyển đổi và lý do.

### 2. Design foundation trước page

* [ ] Chuẩn hóa palette LUUMORY tối thiểu: ivory paper, warm cream, dusty rose, burgundy memory, sage green, old ink, antique gold, soft blue, smoky purple, light peach, paper brown và bright white.
* [ ] Bổ sung semantic tokens cho background, foreground, surface/card, primary, secondary, muted, border/input/ring, success, warning và destructive; component sử dụng semantic token thay vì lặp mã màu.
* [ ] Chuẩn hóa font heading/body/accent từ prototype bằng cơ chế font của Next.js hoặc giải pháp local ổn định, có fallback rõ ràng và không lặp import Google Fonts trong từng page.
* [ ] Chuẩn hóa radius, shadow, container width, section spacing, transition và breakpoint cần dùng chung.
* [ ] Expose token qua `packages/design-system/src/tokens.css` và `tailwind-preset.js`; bảo toàn khả năng build của cả public-web và admin-web.
* [ ] Xác định và triển khai các primitive còn thiếu được dùng lặp lại, ví dụ `IconButton`, `Badge`, `QuantityInput`, `Tabs`, `Dialog/Modal`, `Drawer`, `Carousel`, `Select` hoặc `FormField`; ưu tiên primitive accessible và API nhất quán.
* [ ] Không đưa component chỉ có ý nghĩa nghiệp vụ như `ProductCard`, `SiteHeader`, `CartSummary` vào `packages/ui`.
* [ ] Khai báo brand constants dùng chung cho tên `MEMORIES`, logo `/brand/memories-logo.png`, site name và contact placeholder; không lặp literal thương hiệu ở từng page/component.

### 3. Public shell và navigation

* [ ] Tạo route group/layout cho các trang public site, dùng chung `SiteHeader` và `SiteFooter`.
* [ ] Tách menu, footer links, contact/social data khỏi JSX khi dữ liệu được lặp hoặc cần cấu hình.
* [ ] Header hỗ trợ active route, mobile navigation, cart count mock, keyboard/focus management và các trạng thái chưa đăng nhập/đã đăng nhập ở mức presentation.
* [ ] Footer responsive và dùng route nội bộ thực tế; link chưa có đích phải thể hiện rõ trạng thái placeholder.
* [ ] `/tao-thiep` sử dụng editor layout riêng; không ép public header/footer làm giảm diện tích editor.

### 4. Shared feature components và mock model

* [ ] Tách component dùng chung giữa các page: section heading, breadcrumb, product/template card, price, badge, filter controls, empty state, modal/drawer, quantity control và CTA khi thực sự có cùng contract.
* [ ] Tách mock data khỏi page/component; khai báo TypeScript type/interface cho template, product, cart item, option, review và custom-order data.
* [ ] Dùng ID/slug ổn định và cấu trúc gần response API dự kiến, nhưng không giả lập API/network layer khi chưa cần.
* [ ] Có fixture cho trạng thái có dữ liệu, rỗng, danh sách dài, còn/hết hàng, giá thường/khuyến mãi và option bắt buộc/không bắt buộc.
* [ ] Không lưu access token hoặc dữ liệu nhạy cảm vào browser storage. Chỉ dùng storage cho draft không nhạy cảm nếu prototype yêu cầu, có guard cho SSR và có thao tác xóa/reset rõ ràng.

### 5. Triển khai page theo vertical slice

Mỗi route phải được hoàn thành theo thứ tự: page composition → component riêng → mock model/data → interaction → responsive/a11y → test. Không triển khai đồng loạt markup của cả 6 page rồi mới quay lại xử lý component chung.

* [ ] `/`: giữ hero, các section giới thiệu thiệp/quà/làm riêng/câu chuyện và CTA chính.
* [ ] `/mau-thiep`: triển khai danh sách, tìm kiếm/lọc/sắp xếp hoặc modal/preview nếu có trong prototype; có empty state.
* [ ] `/qua-ky-niem`: triển khai catalog, filter/sort, product state và quick-view/add-to-cart mock theo prototype.
* [ ] `/dat-lam-rieng`: triển khai form/stepper, validation, upload preview ở mức local, summary, modal xác nhận và trạng thái draft theo phạm vi an toàn.
* [ ] `/gio-hang`: triển khai cập nhật số lượng, xóa/khôi phục nếu có, option, promo/shipping mock, empty cart và order summary.
* [ ] `/tao-thiep`: chuyển editor từ HTML/JavaScript sang React component/state/hook; hỗ trợ các thao tác chính thể hiện trong prototype và các screenshot tham chiếu, không nhúng nguyên `luumory-app.js` hoặc `support.js`.

### 6. Asset management

* [ ] Di chuyển asset cần dùng vào `apps/public-web/public` theo nhóm có ý nghĩa; cập nhật đường dẫn theo quy ước Next.js.
* [ ] Dedupe logo và ảnh trùng lặp; không đổi nội dung file chỉ để tạo thêm bản sao.
* [ ] Dùng `next/image` khi phù hợp, khai báo dimensions/sizes để hạn chế layout shift.
* [ ] Ảnh nội dung có `alt` phù hợp; ảnh trang trí dùng alt rỗng hoặc CSS background đúng ngữ nghĩa.
* [ ] Không dùng remote image không ổn định để lấp dữ liệu thiếu.
* [ ] Dùng `prototype/logo/logo.png` làm logo frontend duy nhất; copy nguyên bản sang `apps/public-web/public/brand/memories-logo.png`, khai báo kích thước/tỷ lệ hiển thị phù hợp và dùng alt/accessibility label mang tên `MEMORIES`.
* [ ] Không đưa các logo LUUMORY khác từ thư mục con của prototype vào runtime, trừ khi có yêu cầu thay thế logo chính thức mới.

### 7. Responsive, accessibility và fidelity

* [ ] Kiểm tra tối thiểu tại mobile 375px, tablet 768px và desktop 1440px.
* [ ] Không có horizontal overflow ngoài chủ đích; nội dung dài và danh sách rỗng không phá layout.
* [ ] Menu, dialog/drawer, tab, carousel, stepper, filter và editor control sử dụng được bằng bàn phím với focus visible.
* [ ] Control có accessible name, trạng thái `aria-*` phù hợp và vùng thông báo cho validation/toast khi cần.
* [ ] So sánh với prototype theo viewport tương ứng; lưu evidence/screenshot cho các route và trạng thái quan trọng nếu công cụ workflow hỗ trợ.
* [ ] Chấp nhận khác biệt kỹ thuật cần thiết cho accessibility/responsive, nhưng không tự ý redesign.

### 8. Test và validation

* [ ] Test route render và các interaction có rủi ro chính bằng Vitest + Testing Library.
* [ ] Test shared primitive/component một lần tại owner package; test page tập trung vào integration/behavior, không lặp implementation detail.
* [ ] Bao phủ tối thiểu mobile-menu, filter/empty-state, cart quantity/remove, custom-order validation và editor action quan trọng.
* [ ] Không có lỗi runtime, hydration error hoặc warning nghiêm trọng trên browser console.
* [ ] Chạy đầy đủ `lint`, `typecheck`, `test`, `build` của frontend và deterministic checker từ các skill bắt buộc.

## Acceptance criteria

1. Cả 6 prototype trong bảng inventory có route Next.js tương ứng trong `apps/public-web` và truy cập trực tiếp không gây runtime error/trang trắng.
2. Design foundation được triển khai trước hoặc trong slice nền tảng: palette, semantic tokens, typography, spacing, radius, shadow và Tailwind mapping dùng chung; page không sở hữu bản sao `:root` riêng từ prototype.
3. Public theme không làm thay đổi ngoài ý muốn giao diện admin-web.
4. Primitive dùng chung nằm trong `packages/ui`; component mang thương hiệu/nghiệp vụ nằm trong public-web; không có component trùng contract chỉ khác tên.
5. Năm route public site dùng chung header/footer qua layout; `/tao-thiep` dùng layout editor riêng.
6. Header/footer bám theo `prototype/qua-ky-niem/qua-ky-niem.html`, navigation đúng route, active state/mobile menu/cart badge mock hoạt động.
7. Mỗi page được chia theo composition/component/data hợp lý; không có page/component đơn khối chứa bản sao toàn bộ HTML/CSS/script prototype.
8. Không dùng thao tác DOM trực tiếp không cần thiết và không nhúng/chạy nguyên JavaScript từ prototype.
9. Mock data có type, ID ổn định, tách khỏi UI và hỗ trợ trạng thái thường/rỗng/biên quan trọng.
10. Interaction cốt lõi của từng prototype hoạt động với mock state và không lỗi khi dữ liệu rỗng hoặc thiếu trường optional.
11. Asset runtime thuộc public-web, được dedupe và không phụ thuộc đường dẫn `prototype`.
12. Giao diện giữ được hierarchy, palette, typography, spacing, imagery và responsive behavior chính tại 375px, 768px, 1440px.
13. Các control chính dùng được bằng bàn phím, có focus visible và accessible name/state phù hợp.
14. Test có bằng chứng cho shared shell/component và interaction rủi ro chính của từng feature.
15. `lint`, `typecheck`, `test`, `build` và các deterministic skill checks đều pass.
16. Không thay đổi ngoài phạm vi UI/layout của admin-web, không tích hợp API thật và không xóa `prototype`.
17. Frontend sử dụng đúng file logo được chỉ định tại `/brand/memories-logo.png`; header, footer, manifest/icon metadata phù hợp không dùng logo LUUMORY cũ.
18. Không còn chuỗi thương hiệu `LUUMORY`, `Luumory` hoặc `luumory` trong source/runtime asset name do task tạo ra; toàn bộ brand copy triển khai từ prototype được chuẩn hóa thành `MEMORIES`.

## Phân tích skill cho AI workflow

### Skill hiện có

`implement-nextjs-vertical-slice` vẫn là skill implementation bắt buộc vì bao phủ App Router, server/client boundary, accessibility, testing và frontend security. Tuy nhiên skill này mang tính tổng quát, chưa đủ hướng dẫn/checker cho việc trích xuất design system và kiểm chứng độ tương đồng khi chuyển prototype lớn.

`review-vertical-slice-completeness` vẫn là review gate tổng quát, nhưng không thay thế visual-fidelity review.

### Skill nên bổ sung

1. `establish-frontend-design-system` (implementation)
   * Trigger: task yêu cầu chuẩn hóa token/theme/typography/Tailwind/shared primitive từ một hoặc nhiều prototype.
   * `SKILL.md`: quy trình inventory → phân loại raw/semantic token → scope theme theo app → quyết định owner `design-system`/`ui`/app → kiểm tra admin regression.
   * `references/`: token taxonomy, component ownership matrix, Tailwind/CSS-variable conventions của repo.
   * `scripts/`: checker phát hiện mã màu/font/radius lặp vượt ngưỡng trong page và kiểm tra token được expose trong preset. Script chỉ báo cáo evidence, không tự sửa source.

2. `migrate-prototype-nextjs-page` (implementation)
   * Trigger: chuyển HTML/CSS/JavaScript prototype thành một route Next.js/React có fidelity và interaction tương đương.
   * `SKILL.md`: quy trình theo từng route, inventory interaction/state, server/client boundary, asset migration, mock states, responsive/a11y và test.
   * `references/`: mapping anti-pattern DOM → React, checklist editor/form/catalog/cart, artifact/evidence format.
   * `scripts/`: audit đường dẫn `prototype`, inline handler/`innerHTML`, client boundary quá rộng và route-manifest completeness.

3. `review-frontend-ui-fidelity` (review)
   * Trigger: review implementation từ prototype/screenshot/design reference.
   * `SKILL.md`: review theo route × viewport × state; tách lỗi fidelity, responsive, accessibility và architecture; ghi evidence tái lập được.
   * `references/`: viewport/state matrix, severity rule và ngưỡng chấp nhận khác biệt.
   * `scripts/`: tạo/check evidence matrix; nếu workflow có browser automation thì orchestration screenshot nên nằm ở đây thay vì viết logic dài trong `SKILL.md`.

### Cách khai báo và rollout

* Mỗi skill đặt tại `ai/skills/<skill-name>/` với `SKILL.md`, `agents/openai.yaml` và chỉ thêm `references/`/`scripts/` khi có giá trị tái sử dụng.
* Frontmatter chỉ gồm `name` và `description`; description phải nêu rõ hành động và trigger để `classify-skills` có thể nhận diện.
* Cập nhật `ai/bin/classify-skills` bằng keyword/rule có xét repo frontend; không để mọi task frontend tự động nhận cả ba skill.
* Thêm fixture pass/fail vào `ai/tests/fixtures/skill-checks` và test gate tương ứng trước khi dùng skill làm required gate.
* Chạy validator của skill, test script trên fixture và `./ai/bin/ai self-check --smoke`.
* Chỉ sau khi skill tồn tại và validation pass mới thêm `establish-frontend-design-system` + `migrate-prototype-nextjs-page` vào `task.yaml.skills.implement`, và `review-frontend-ui-fidelity` vào `task.yaml.skills.review`.
* Sau mọi thay đổi skill/task requirement phải chạy lại `prepare-plan --force` và `prepare-context` để execution plan và skill hash trong context lock không bị stale.

Ba skill trên đã được triển khai trong `ai/skills`, được map vào `task.yaml` và phải được khóa hash lại bằng `prepare-context` trước khi implement.

## Out of scope

* Tích hợp API/backend/database thực tế.
* Xác thực, phân quyền, thanh toán, vận chuyển hoặc đồng bộ cart thực tế.
* Lưu lâu dài mock state hay dữ liệu người dùng; upload file lên server.
* CMS, analytics, marketing pixel hoặc SEO chuyên sâu ngoài metadata cơ bản của page.
* Thiết kế lại toàn bộ prototype hoặc tạo route chức năng không có trong inventory.
* Xóa/thay đổi prototype nguồn.
* Thay đổi admin-web ngoài điều chỉnh tương thích bắt buộc với shared package.
