# MEMORIES-0010: Hoàn thiện giao diện tạo thiệp theo prototype

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0010`
- Repository: `frontend`
- Route chính: `/tao-thiep`
- Prototype chuẩn: `prototype/tao-thiep/Tao-thiep.dc.html` và `prototype/tao-thiep/luumory-app.js`

## Goal

Hoàn thiện trình tạo thiệp của `public-web` để người dùng có thể đi trọn luồng từ chọn điểm bắt đầu, thiết kế thiệp nhiều trang, chỉnh sửa nội dung, xem trước, kiểm tra và chọn cách trao gửi. Giao diện, hành vi, trạng thái và responsive phải bám sát prototype; không chỉ dựng bố cục tĩnh hoặc các nút không có phản hồi.

Kết quả cần giữ đúng ngôn ngữ thiết kế LUUMORY, tái sử dụng design system và kiến trúc frontend hiện có, đồng thời có mô hình trạng thái rõ ràng, dễ kiểm thử và có thể kết nối backend thật ở epic sau.

## Background

Route `/tao-thiep` đã có editor nền tảng nhưng chỉ bao phủ một phần nhỏ prototype. Hiện tại người dùng có thể thêm một khối chữ, tải một ảnh, đổi một số màu nền, kéo/đổi kích thước phần tử, đổi thứ tự trước/sau, undo/redo và chuyển giữa hai trang cố định.

So với prototype, editor còn thiếu phần lớn trải nghiệm sản phẩm: thư viện và bộ lọc mẫu, preset văn bản/lời chúc, thư viện ảnh, trang trí, khung ảnh, bảng màu, nhạc, video, QR, sự kiện, quản lý layer, thuộc tính nâng cao, zoom/lưới/guideline, quản lý trang, autosave/khôi phục bản nháp, onboarding, preview theo thiết bị, checklist hoàn tất, quyền riêng tư, tải xuống và các lựa chọn chia sẻ.

Prototype là nguồn sự thật cho composition, visual hierarchy, nội dung, trạng thái và hành vi. Việc triển khai phải chuyển prototype sang React/Next.js theo convention của repo; không nhúng nguyên HTML/JavaScript prototype vào ứng dụng.

## Current system

- Entry point editor nằm tại `apps/public-web/app/tao-thiep` và `apps/public-web/components/editor/editor-view.tsx`.
- State hiện tại nằm trong `components/editor/use-card-editor.ts`; model UI nằm tại `lib/types/editor.ts`.
- Canvas hiện hỗ trợ phần tử `text` và `image`, selection, drag, resize và một số thuộc tính chữ cơ bản.
- Mẫu thiệp và route liên quan đã tồn tại trong `lib/mock/card-templates.ts`, `/mau-thiep` và query parameter `/tao-thiep?template=<id>`.
- `packages/editor-core` có document model nền tảng nhưng chưa đại diện đầy đủ cho editor trong prototype; cần đánh giá để mở rộng hoặc đồng bộ, tránh duy trì hai model mâu thuẫn.
- Design tokens và UI primitives dùng chung nằm trong `packages/design-system` và `packages/ui`.
- Chưa có backend contract hoàn chỉnh cho lưu thiết kế, xuất bản, chia sẻ, gửi email, hẹn giờ hoặc tích hợp quà. Trong epic này các luồng đó phải có UI hoàn chỉnh và phản hồi trung thực; không giả vờ rằng một thao tác mạng đã thành công nếu chưa có dịch vụ thật.

## Scope

### 1. Khung editor và thanh công cụ trên cùng

- [ ] Tái tạo layout editor toàn màn hình theo prototype: top bar, tool rail, resource panel, canvas workspace, properties panel và page manager.
- [ ] Hỗ trợ quay lại bộ sưu tập mẫu, logo/điều hướng hợp lệ, đổi tên thiết kế trực tiếp và giới hạn tên hợp lý.
- [ ] Hiển thị trạng thái bản nháp `đang lưu / đã lưu / lỗi` bằng text và live region, không chỉ bằng màu.
- [ ] Hoàn tác/làm lại bằng nút và phím tắt; trạng thái disabled phản ánh đúng history.
- [ ] Hỗ trợ thu nhỏ, phóng to, chọn mức zoom, vừa khung và bật/tắt lưới căn chỉnh.
- [ ] Có nút trợ giúp, xem trước và hoàn tất; mọi nút phải mở đúng luồng hoặc có thông báo rõ ràng về giới hạn hiện tại.
- [ ] Có chế độ công cụ `Cơ bản` và `Nâng cao`, ghi nhớ lựa chọn trên thiết bị.

### 2. Chọn điểm bắt đầu và mẫu thiệp

- [ ] Khi không có template hợp lệ, hiển thị onboarding cho phép bắt đầu với thiệp trắng, chọn mẫu hoặc khôi phục bản nháp gần nhất nếu có.
- [ ] Khi route có `?template=<id>`, nạp đúng mẫu; ID không hợp lệ phải fallback an toàn và thông báo dễ hiểu.
- [ ] Panel mẫu có tìm kiếm, lọc theo dịp và phong cách, trạng thái không có kết quả, nhãn miễn phí/cao cấp và metadata kích thước/số trang.
- [ ] Có thể mở bộ sưu tập mẫu đầy đủ và áp dụng mẫu vào thiết kế.
- [ ] Nếu áp dụng mẫu có nguy cơ ghi đè nội dung hiện tại, phải xác nhận và cho phép hủy; không mất dữ liệu âm thầm.

### 3. Canvas và thao tác phần tử

- [ ] Render đúng các loại phần tử cần cho prototype: văn bản, ảnh, khung ảnh, shape/trang trí, QR, video/event placeholder và các phần tử sinh từ template.
- [ ] Chọn/bỏ chọn; kéo; resize; xoay; duplicate; delete; lock/unlock; hide/show; đổi tên layer và thay đổi z-order.
- [ ] Hỗ trợ đưa lên/xuống một lớp và đưa lên trên cùng/xuống dưới cùng, không chỉ front/back tuyệt đối.
- [ ] Hỗ trợ căn trái/phải/trên/dưới/giữa canvas; hiển thị guideline/snap phù hợp khi di chuyển.
- [ ] Tôn trọng canvas bounds, zoom ratio và touch/pointer interaction; drag/resize ở mức zoom khác 100% không được sai tọa độ.
- [ ] Multi-page selection và element selection không để state trỏ tới phần tử đã xóa hoặc thuộc trang khác.
- [ ] Click vùng trống và `Escape` bỏ chọn; keyboard interaction không xung đột khi người dùng đang nhập text/form.

### 4. Công cụ văn bản

- [ ] Cung cấp preset: tiêu đề, nội dung, chú thích, lời chúc, tên người nhận và ngày tháng.
- [ ] Có thư viện gợi ý lời chúc theo nhóm và tìm kiếm; chọn một gợi ý sẽ thêm nội dung có style phù hợp.
- [ ] Cho phép sửa text trực tiếp hoặc qua properties panel.
- [ ] Hỗ trợ font family, font size, màu chữ, bold, italic, underline, căn lề, line height, letter spacing và opacity theo prototype.
- [ ] Floating text toolbar hoặc interaction tương đương phải xuất hiện gần selection và vẫn dùng được bằng bàn phím.

### 5. Ảnh, khung ảnh và trang trí

- [ ] Upload nhiều ảnh bằng file picker và drag/drop; chỉ nhận JPG/JPEG, PNG, WEBP; validate kích thước và hiển thị lỗi cụ thể.
- [ ] Quản lý thư viện ảnh tạm trên thiết bị: xem thumbnail, thêm lại vào canvas và xóa khỏi thư viện; thu hồi object URL khi không còn dùng để tránh memory leak.
- [ ] Có ảnh mẫu/placeholder để người dùng trải nghiệm khi chưa upload.
- [ ] Có thư viện shape/trang trí theo nhóm, tìm kiếm nếu prototype cung cấp và thêm được lên canvas.
- [ ] Có các dạng khung ảnh trong prototype; ảnh/khung hỗ trợ fit/crop hoặc lựa chọn hiển thị tương đương.
- [ ] Thuộc tính ảnh gồm opacity, border radius, flip ngang/dọc, xoay và thứ tự lớp; chức năng chưa hỗ trợ thật như xóa nền phải ghi rõ `Sắp có`, không tạo false success.

### 6. Nền và bảng màu

- [ ] Panel nền hỗ trợ màu đơn và các preset nền/texture/gradient thể hiện trong prototype.
- [ ] Cho phép chọn màu bằng swatch, color picker và mã màu; mã không hợp lệ phải được xử lý an toàn.
- [ ] Cung cấp palette gợi ý và áp dụng palette lên các thành phần phù hợp mà không phá dữ liệu người dùng.
- [ ] Background và palette phải được lưu độc lập theo từng trang khi prototype yêu cầu.

### 7. Công cụ nâng cao

- [ ] Nhạc: chọn/bỏ nhạc nền, xem trạng thái lựa chọn và nút nghe thử với thông báo trung thực nếu chỉ mô phỏng.
- [ ] Video: nhập/validate liên kết, thêm video placeholder lên thiệp và cho phép chỉnh sửa/xóa.
- [ ] Mã QR: nhập nội dung hoặc URL, nhãn và màu foreground/background; tạo QR preview có thể thêm lên canvas.
- [ ] Sự kiện: nhập thông tin sự kiện cần thiết và thêm block sự kiện theo layout lựa chọn.
- [ ] Layers panel liệt kê theo đúng z-order, chọn layer tương ứng trên canvas, đổi tên, ẩn/hiện, khóa/mở khóa và reorder.

### 8. Quản lý trang thiệp

- [ ] Page manager hiển thị thumbnail, tên và trang đang chọn.
- [ ] Cho phép thêm trang theo loại/kích thước được prototype hỗ trợ, duplicate, đổi tên, xóa và sắp xếp trang.
- [ ] Không cho xóa trang cuối cùng; thao tác phá hủy phải xác nhận khi cần.
- [ ] Chuyển trang giữ đúng state riêng của trang và xóa selection cũ một cách an toàn.
- [ ] Thumbnail cập nhật sau thay đổi nội dung/nền và vẫn phản ánh đúng thứ tự trang.

### 9. Lưu nháp, history và bảo vệ dữ liệu

- [ ] Autosave thiết kế vào local storage với debounce, version/schema rõ ràng và trạng thái saving/saved/error.
- [ ] Có thể khôi phục bản nháp hợp lệ; dữ liệu hỏng hoặc version cũ không được làm crash editor.
- [ ] Manual save và `Ctrl/⌘ + S` kích hoạt lưu thật trên thiết bị.
- [ ] Cảnh báo khi rời trang nếu còn thay đổi chưa lưu; không cảnh báo sau khi lưu thành công.
- [ ] Undo/redo bao phủ các thay đổi nội dung quan trọng, xóa redo branch sau một edit mới và không ghi selection-only change thành history entry dư thừa.
- [ ] Hỗ trợ phím tắt trong prototype: undo, redo, save, duplicate, delete, arrow nudge, Shift + arrow nudge nhanh và Escape.

### 10. Xem trước

- [ ] Preview là dialog/full-screen experience tách khỏi editor, hiển thị toàn bộ trang theo thứ tự mà không có selection handles/editor chrome.
- [ ] Cho phép chuyển phone/tablet/desktop, chuyển trang bằng nút và page dots, đổi nền preview sáng/tối.
- [ ] Preview phản ánh đúng text, ảnh, shape, QR, background, rotation, opacity, hidden state và z-order hiện tại.
- [ ] Nút phát/tạm dừng nhạc phản ánh đúng trạng thái; nếu audio chỉ mô phỏng phải thông báo rõ.
- [ ] Đóng preview trả focus về trigger và không làm mất thay đổi editor.

### 11. Luồng hoàn tất, chia sẻ và tải xuống

- [ ] Luồng `Hoàn tất` nhiều bước theo prototype: checklist nội dung, thông tin người nhận/lời nhắn, quyền riêng tư và cách sử dụng/trao gửi.
- [ ] Checklist phát hiện tối thiểu lời chúc còn thiếu, placeholder chưa thay và khung ảnh trống; cho phép quay lại đúng trang để sửa.
- [ ] Quyền riêng tư có các lựa chọn công khai/riêng tư, mật khẩu hoặc ngày hết hạn theo prototype, kèm validation phù hợp.
- [ ] UI chia sẻ có link, copy feedback, QR chia sẻ và lựa chọn Facebook/Zalo/email/tải xuống/thêm vào quà.
- [ ] Download dialog có loại tệp, phạm vi trang, chất lượng và các tùy chọn liên quan. Chỉ công bố/xuất định dạng thực sự hỗ trợ; định dạng chưa triển khai phải disabled hoặc ghi rõ giới hạn.
- [ ] Nếu triển khai PNG client-side, file phải phản ánh nội dung hiển thị quan trọng và xử lý lỗi/cleanup object URL đúng cách.
- [ ] Hẹn giờ, gửi email, publish link, tài khoản và gắn quà chỉ là UI simulation khi chưa có backend; thông báo phải nói rõ chưa gửi/chưa xuất bản dữ liệu thật.

### 12. Responsive, accessibility và chất lượng UI

- [ ] Desktop bám sát bố cục nhiều panel của prototype ở các viewport mục tiêu.
- [ ] Tablet dùng overlay/drawer cho resource/properties panel mà không che mất control đóng hoặc làm canvas không thao tác được.
- [ ] Mobile có bottom tool navigation, sheet `Thêm`, page manager/properties drawer và thông báo khuyến nghị màn hình lớn; vẫn hoàn thành được core flow bằng touch.
- [ ] Không có horizontal overflow ngoài vùng canvas có chủ đích; top bar và action quan trọng không bị cắt ở viewport nhỏ.
- [ ] Dialog/drawer có focus trap, focus restoration, Escape handling, accessible name và scroll containment.
- [ ] Control icon-only có accessible label; toggle dùng `aria-pressed`; trạng thái save/toast/error được công bố qua live region.
- [ ] Bảo đảm keyboard operability, focus-visible, target cảm ứng hợp lý, contrast và `prefers-reduced-motion`.
- [ ] Giữ visual fidelity về màu, typography, spacing, border, shadow, panel sizing, canvas geometry và hierarchy theo prototype ở desktop/tablet/mobile.

### 13. Tests và tài liệu

- [ ] Mở rộng unit/component tests cho reducer/state model, history, autosave/restore và các thao tác element/page.
- [ ] Integration tests bao phủ các happy path chính: bắt đầu trắng; nạp template từ URL; thêm/chỉnh text; upload ảnh; thêm decoration/QR/event; quản lý layer/page; preview; complete/download simulation.
- [ ] Có tests cho invalid template, invalid/corrupt draft, invalid file/link/color, xóa trang cuối, unsaved navigation, keyboard shortcuts và responsive drawers.
- [ ] Chạy đầy đủ validation của repo: `lint`, `typecheck`, `test`, `build`.
- [ ] Cập nhật knowledge/documentation nếu phát sinh convention bền vững về editor model, rendering hoặc persistence.

## Acceptance criteria

1. `/tao-thiep` thể hiện đầy đủ cấu trúc và nhóm chức năng của prototype ở desktop, tablet và mobile; không còn panel/action chính chỉ là placeholder im lặng.
2. Người dùng có thể bắt đầu từ thiệp trắng, một mẫu trong editor hoặc `?template=<id>`; nội dung mẫu được đưa vào document state có thể chỉnh sửa, không chỉ đổi màu nền.
3. Người dùng có thể thêm và chỉnh sửa text, ảnh, frame, decoration/shape, QR, video/event placeholder; mọi phần tử hỗ trợ selection, transform, visibility/lock và z-order phù hợp.
4. Các công cụ Mẫu, Văn bản, Ảnh, Trang trí, Khung ảnh, Nền, Màu sắc, Nhạc, Video, Mã QR, Sự kiện và Lớp có UI và trạng thái tương tác theo prototype.
5. Người dùng quản lý được nhiều trang: thêm, chọn, đổi tên, duplicate, reorder và xóa có guard; preview và thumbnail phản ánh đúng dữ liệu từng trang.
6. Zoom, fit-to-screen, grid/guideline, undo/redo, keyboard shortcuts và drag/resize hoạt động đúng ở mọi zoom được hỗ trợ.
7. Draft được autosave/restore an toàn trên thiết bị, hiển thị trạng thái chính xác và bảo vệ người dùng khỏi mất thay đổi chưa lưu.
8. Preview hiển thị đúng document hiện tại theo phone/tablet/desktop, chuyển trang được và không chứa editor chrome.
9. Luồng Hoàn tất có checklist, thông tin người nhận, privacy và delivery choices; các tích hợp chưa có backend được mô phỏng minh bạch, không báo thành công như thao tác thật.
10. Responsive layout không che/cắt action thiết yếu; core editing flow thao tác được bằng touch và keyboard.
11. Các dialog, drawer, toolbar, canvas elements và feedback state đáp ứng accessibility criteria đã nêu.
12. Automated tests bao phủ các luồng/rủi ro chính và toàn bộ `lint`, `typecheck`, `test`, `build` đều pass.
13. Visual review tại các viewport mục tiêu xác nhận giao diện bám prototype về composition, density, hierarchy, typography, màu sắc và trạng thái tương tác.

## Out of scope

- Xây mới backend/API/database cho thiết kế thiệp, upload media, publish/share link, email, scheduling, tài khoản hoặc order/gift.
- Gửi email/Zalo/Facebook thật, tạo public URL thật hoặc đồng bộ draft giữa nhiều thiết bị.
- Thanh toán hoặc mua quyền sử dụng template cao cấp.
- AI sinh nội dung/hình ảnh, cộng tác nhiều người và real-time editing.
- Cam kết xuất PDF/JPG/print-ready thật nếu repo chưa có rendering pipeline tương ứng; UI phải thể hiện đúng trạng thái chưa hỗ trợ.
- Thay đổi các trang frontend không liên quan, trừ wiring tối thiểu để mở editor từ `/mau-thiep` hoặc route hiện có.
- Sao chép nguyên runtime/script của prototype vào production code.

## Technical notes

- Các file khởi điểm cần đánh giá: `apps/public-web/components/editor/editor-view.tsx`, `editor-element.tsx`, `use-card-editor.ts`, `apps/public-web/lib/types/editor.ts`, `apps/public-web/test/editor-view.spec.tsx` và `packages/editor-core`.
- Tách editor thành các component/domain nhỏ theo trách nhiệm; tránh tiếp tục dồn toàn bộ UI và state machine vào một file lớn.
- Ưu tiên reducer/commands hoặc state transitions thuần cho document, history, page và element operations để có thể unit test.
- Xác định một document model canonical giữa app và `packages/editor-core`; có migration/version cho local draft.
- Canvas renderer có thể tiếp tục dựa trên DOM/CSS nếu đáp ứng fidelity và export đã cam kết; không thêm thư viện canvas nặng nếu chưa chứng minh nhu cầu.
- Tái sử dụng `@memories/ui`, design tokens, icons, routes, query hooks và card-template data hiện có; không tạo hệ màu/font/song song với design system nếu token đã tồn tại.
- Phải cleanup `ResizeObserver`, event listener, timer, object URL và media resources khi component unmount hoặc asset bị xóa.
- Không persist object URL vào local storage. Nếu cần khôi phục ảnh cục bộ, dùng chiến lược dữ liệu bền vững phù hợp hoặc thông báo rõ giới hạn.
- Dùng dynamic import/lazy loading cho phần export/QR/rendering nặng nếu có để không làm tăng initial bundle không cần thiết.
- Mọi simulation phải dùng wording trung thực như `bản xem thử`, `mô phỏng`, `chưa gửi thật`; không tạo fabricated backend state.

## Suggested implementation slices

1. Chuẩn hóa document model, reducer/history, draft persistence và migration.
2. Tách editor shell, responsive panels, top bar, zoom/grid và keyboard controls.
3. Hoàn thiện canvas interaction, element transforms, alignment, lock/visibility và layers.
4. Hoàn thiện template/text/background/color tools.
5. Hoàn thiện image library, frame và decoration tools.
6. Hoàn thiện QR/video/music/event tools với validation và simulation boundary.
7. Hoàn thiện multi-page manager và thumbnail behavior.
8. Hoàn thiện preview, onboarding/help và complete/share/download flows.
9. Accessibility, responsive fidelity, automated tests và full validation.

## Constraints

- Chỉ sửa source trong worktree đã đăng ký: `worktrees/MEMORIES-0010/frontend`.
- Không quản lý lại worktree/branch trong implementation workflow.
- Không commit hoặc push.
- Không đọc secret hoặc thêm credential vào client.
- Không sửa trực tiếp `ai/shared`, `ai/repos` hoặc `ai/domains`; knowledge update phải đi qua workflow tương ứng.
- Không sửa ngoài repo/worktree khai báo, ngoại trừ artifact của task trong `ai/tasks/MEMORIES-0010` do AI Workflow quản lý.
