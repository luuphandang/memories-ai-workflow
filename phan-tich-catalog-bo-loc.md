# Phân tích catalog và thuộc tính cho bộ lọc thiệp, quà tặng

## 1. Phạm vi và nguồn đối chiếu

Phân tích này dựa trên:

- Prototype thiệp: `prototype/mau-thiep/mau-thiep.html`.
- Prototype quà kỷ niệm: `prototype/qua-ky-niem/qua-ky-niem.html`.
- Kiểu dữ liệu và mock frontend gần nhất trong `worktrees/MEMORIES-0003/frontend/apps/public-web`.

Trong tài liệu này:

- **Catalog** là dữ liệu tham chiếu được quản trị tập trung, có `id/slug/name/status/sortOrder`, có thể tái sử dụng giữa nhiều sản phẩm, dùng cho điều hướng, landing page, SEO hoặc báo cáo. Sản phẩm/thiệp chỉ lưu quan hệ tới mục catalog.
- **Thuộc tính đính kèm** là dữ liệu thuộc riêng sản phẩm, biến thể, template hoặc trạng thái vận hành. Giá trị lọc thường được tính trực tiếp hoặc quy về các khoảng hiển thị, không tạo một catalog độc lập.
- Một số trường là **mô hình lai**: danh sách giá trị chuẩn là catalog, nhưng việc sản phẩm hỗ trợ giá trị nào vẫn là quan hệ/thuộc tính đính kèm.

## 2. Kết luận nhanh

| Nhóm bộ lọc | Cách triển khai đề xuất | Kết luận |
| --- | --- | --- |
| Thiệp — Theo dịp | Catalog dùng chung `occasion` + quan hệ nhiều-nhiều | Catalog |
| Thiệp — Theo phong cách | Catalog `card_style` + quan hệ nhiều-nhiều | Catalog |
| Thiệp — Theo định dạng | Catalog/capability `card_format` + quan hệ nhiều-nhiều | Catalog có hành vi kỹ thuật |
| Thiệp — Theo màu sắc | Palette chuẩn + màu chủ đạo gắn vào template | Mô hình lai, không cần catalog điều hướng độc lập |
| Thiệp — Mức phí | Chính sách giá/quyền truy cập gắn vào template | Thuộc tính đính kèm |
| Quà — Theo loại sản phẩm | Catalog phân cấp `product_category` | Catalog |
| Quà — Theo dịp | Dùng chung catalog `occasion` với thiệp | Catalog |
| Quà — Theo người nhận | Catalog `recipient_segment` + quan hệ nhiều-nhiều | Catalog |
| Quà — Theo mức giá | Giá ở sản phẩm/SKU; khoảng giá được tính khi truy vấn | Thuộc tính đính kèm |
| Quà — Theo khả năng cá nhân hóa | Catalog capability + cấu hình hỗ trợ gắn vào sản phẩm/SKU | Mô hình lai |
| Quà — Theo thời gian chuẩn bị | Số ngày, trạng thái làm sẵn/làm theo yêu cầu và hỗ trợ làm gấp | Thuộc tính đính kèm |
| Quà — Theo chất liệu | Catalog `material` + quan hệ sản phẩm–chất liệu | Mô hình lai, nên có catalog tham chiếu |
| Quà — Đánh giá | Dữ liệu tổng hợp từ review | Thuộc tính dẫn xuất, không phải catalog |

## 3. Nguyên tắc quyết định

Một bộ lọc nên trở thành catalog khi phần lớn các điều sau đúng:

1. Giá trị được dùng lại trên nhiều sản phẩm hoặc cả hai miền thiệp và quà.
2. Người quản trị cần đổi tên, sắp xếp, ẩn/hiện hoặc thêm giá trị mà không sửa mã nguồn.
3. Giá trị có ý nghĩa kinh doanh ổn định, có thể có trang danh mục/URL riêng hoặc dùng trong báo cáo.
4. Cần chống sai chính tả, trùng nghĩa và sai khác giữa nhãn hiển thị với dữ liệu lọc.
5. Quan hệ nhiều-nhiều là bản chất của dữ liệu.

Ngược lại, dữ liệu nên là thuộc tính đính kèm khi nó là số đo, giá tiền, trạng thái tồn kho, khả năng vận hành, kết quả tổng hợp hoặc cấu hình riêng của từng sản phẩm/SKU.

## 4. Phân tích bộ lọc thiệp

### 4.1. Theo dịp — catalog dùng chung

Nên tạo một catalog `occasion`, dùng chung cho thiệp và quà. Các giá trị prototype như Sinh nhật, Đám cưới, Tân gia, Đầy tháng, Thôi nôi, Kỷ niệm, Tốt nghiệp, Cảm ơn, Xin lỗi và Chúc mừng đang xuất hiện ở cả hai miền.

Đề xuất:

- `occasion(id, slug, name, description, status, sort_order, parent_id?)`.
- `card_template_occasion(template_id, occasion_id, is_primary)`.
- `product_occasion(product_id, occasion_id, is_primary)`.

Prototype hiện lưu đúng một `occ` cho thiệp, trong khi một mẫu có thể phù hợp nhiều dịp. Nên chuyển thành quan hệ nhiều-nhiều, có `is_primary` nếu cần một dịp chính để hiển thị hoặc xếp hạng.

Không nên tách hai catalog “dịp của thiệp” và “dịp của quà”, vì sẽ tạo hai phiên bản khác nhau của cùng một khái niệm.

### 4.2. Theo phong cách — catalog riêng cho thiệp

Các giá trị như Hoài niệm, Tối giản, Thanh lịch, Dễ thương, Lãng mạn, Sang trọng, Thiên nhiên, Truyền thống Việt Nam và Hiện đại là taxonomy biên tập, phù hợp để quản trị như catalog.

Đề xuất:

- `card_style(id, slug, name, status, sort_order, thumbnail_asset_id?)`.
- `card_template_style(template_id, style_id, is_primary)`.

Dù prototype hiện chỉ gắn một phong cách cho mỗi thiệp, thực tế một mẫu có thể vừa “Tối giản” vừa “Hiện đại”. Quan hệ nhiều-nhiều giúp tránh buộc biên tập viên chọn một nhãn duy nhất.

### 4.3. Theo định dạng — catalog có ràng buộc kỹ thuật

Nên quản lý `card_format` như catalog/capability, không chỉ là tag văn bản. Các giá trị hiện tại đang trộn ba khía cạnh:

- Tỷ lệ/hình học: dọc, ngang, vuông.
- Trải nghiệm: động, có nhạc.
- Kênh xuất bản: dạng trang web, dùng để in.

Nếu giữ nguyên một danh sách phẳng, một template có thể gắn nhiều định dạng như prototype. Tuy nhiên về lâu dài nên tách thành các thuộc tính có kiểu rõ ràng:

- `aspect_ratio`: portrait, landscape, square.
- `capabilities`: animation, audio.
- `delivery_channels`: web, print.

Nếu frontend vẫn cần một bộ lọc duy nhất “Theo định dạng”, API có thể hợp nhất ba nhóm này thành facet. Mỗi capability phải có mã ổn định vì nó còn điều khiển editor, preview, export và validation; không nên chỉ lưu nhãn tiếng Việt tự do.

### 4.4. Theo màu sắc — palette chuẩn và dữ liệu gắn vào template

Không nên coi màu sắc là catalog nội dung ngang hàng với dịp hoặc phong cách. Màu là đặc trưng thiết kế của từng template; người dùng lọc theo nhóm màu gần đúng chứ không cần một landing page kinh doanh độc lập cho từng màu.

Đề xuất mô hình lai:

- Một palette chuẩn nhỏ: `color_family(code, name, representative_hex, sort_order)`; có thể là bảng tham chiếu hoặc cấu hình hệ thống.
- Quan hệ `card_template_color(template_id, color_family_code, weight, is_primary)`.
- Giữ màu thiết kế thực tế như `background`, `foreground` hoặc palette JSON trong dữ liệu phiên bản template.

Prototype hiện chỉ có một `colorName`, nhưng trường hợp “Nhiều màu” cho thấy một nhãn đơn không đủ. Nên cho phép nhiều nhóm màu và dùng `weight` hoặc `is_primary` để xác định màu chủ đạo. Không nên dùng trực tiếp mã hex làm khóa bộ lọc, vì các sắc độ gần nhau sẽ phân mảnh kết quả.

### 4.5. Mức phí — thuộc tính/chính sách thương mại

`Miễn phí` và `Cao cấp` không phải taxonomy nội dung. Đây là quyền truy cập hoặc chính sách giá của template.

Đề xuất lưu trên template hoặc offer:

- `access_tier`: free, premium.
- Nếu có bán lẻ: `price`, `currency`, `valid_from`, `valid_to` trong bảng offer/pricing.
- Nếu phụ thuộc gói thuê bao: dùng entitlement/plan mapping thay vì hard-code nhãn “Cao cấp”.

Bộ lọc frontend được sinh từ giá trị này. Không cần bảng catalog chỉ có hai hàng, trừ khi hệ thống đã có catalog gói/entitlement dùng chung.

## 5. Phân tích bộ lọc quà tặng

### 5.1. Theo loại sản phẩm — catalog phân cấp, cần làm sạch taxonomy

Đây là catalog cốt lõi và nên hỗ trợ cây cha–con:

- Ví dụ nhóm cha: Hoa, Mô hình, Khung/Tranh, Hộp quà, Đèn, Phụ kiện, Combo.
- Ví dụ nhóm con: Hoa kẽm nhung, Hoa khô; Mô hình 3D; Khung ảnh; Hộp kỷ niệm; Đèn lưu niệm.

Danh sách prototype hiện trộn nhiều loại khái niệm:

- `Kẽm nhung` là chất liệu/kỹ thuật, không phải lúc nào cũng là loại sản phẩm.
- `Quà handmade` là phương thức sản xuất hoặc collection.
- `Quà theo ảnh`, `Quà khắc tên` là khả năng cá nhân hóa.
- `Combo thiệp và quà` là bundle/product type đặc biệt.
- `Hoa thủ công`, `Khung ảnh`, `Mô hình 3D`, `Hộp kỷ niệm`, `Đèn lưu niệm` mới gần với loại sản phẩm thực.

Vì vậy không nên đưa nguyên danh sách prototype vào một bảng category. Đề xuất:

- `product_category(id, parent_id, slug, name, status, sort_order)` cho loại sản phẩm thực.
- `collection(id, slug, name, rule/config, status)` cho các trang biên tập như “Quà handmade”, “Quà theo ảnh”. Collection có thể thủ công hoặc được tạo từ rule.
- Khả năng “khắc tên/làm theo ảnh” đi vào personalization capability.
- Combo có `product_kind = bundle` và quan hệ tới các thành phần.

Mỗi sản phẩm nên có một category chính để URL/breadcrumb ổn định, và có thể có thêm category phụ nếu nghiệp vụ cần.

### 5.2. Theo dịp — dùng chung catalog với thiệp

Sử dụng chính `occasion` ở mục 4.1 và quan hệ nhiều-nhiều `product_occasion`. Đây là điểm tái sử dụng quan trọng nhất giữa hai catalog: cùng slug, cùng tên hiển thị, cùng trạng thái quản trị.

Có thể bổ sung trọng số hoặc độ phù hợp để xếp hạng thay vì chỉ có đúng/sai:

- `relevance_score` hoặc `is_primary`.
- Ví dụ một món quà có thể hợp “Kỷ niệm” nhất nhưng vẫn xuất hiện ở “Sinh nhật”.

### 5.3. Theo người nhận — catalog phân khúc người nhận

Các giá trị Người yêu, Vợ hoặc chồng, Cha mẹ, Bạn bè, Trẻ nhỏ, Đồng nghiệp, Gia đình và Doanh nghiệp là taxonomy phục vụ khám phá, merchandising và landing page; nên là catalog.

Đề xuất:

- `recipient_segment(id, slug, name, status, sort_order, parent_id?)`.
- `product_recipient_segment(product_id, segment_id, relevance_score?, is_primary)`.

Cần thống nhất mức chi tiết. Ví dụ “Cha mẹ” và “Gia đình” có thể chồng lấn; `parent_id` hoặc hệ thống tag phân cấp giúp frontend hiển thị đơn giản nhưng dữ liệu vẫn mở rộng được về sau.

### 5.4. Theo mức giá — thuộc tính của offer/SKU, khoảng giá là logic truy vấn

Giá phải nằm ở sản phẩm bán được hoặc SKU/variant, không nằm trong catalog khoảng giá.

Đề xuất:

- `product_variant.price`, `compare_at_price`, `currency` hoặc bảng `price_offer` nếu cần lịch sử/khuyến mãi.
- Giá hiển thị của product là `min(available variant prices)` hoặc khoảng min–max.
- Các khoảng “Dưới 200.000₫”, “200.000₫–350.000₫” chỉ là cấu hình facet ở frontend/search service.

Prototype đang dùng điều kiện bao gồm cả hai đầu cho các khoảng kề nhau, khiến đúng 350.000₫ hoặc 500.000₫ có thể thuộc hai khoảng. Nên dùng khoảng nửa mở, ví dụ `[200.000, 350.000)` và `[350.000, 500.000)`, còn nhãn hiển thị có thể diễn đạt theo cách dễ hiểu.

Nếu có giảm giá, cần xác định rõ filter theo `effective_price`, không theo giá gốc `compare_at_price`.

### 5.5. Theo khả năng cá nhân hóa — catalog capability + cấu hình trên sản phẩm

Đây là mô hình lai:

- Danh sách khả năng chuẩn nên là catalog `personalization_capability` để dùng thống nhất trong filter, admin và rule validation.
- Việc một sản phẩm hỗ trợ khả năng nào, bắt buộc hay tùy chọn, có tính phí hay cần input gì là cấu hình gắn vào sản phẩm hoặc SKU.

Đề xuất các capability chuẩn, dùng code thay vì nhãn:

- `engraved_or_printed_name`.
- `anniversary_date`.
- `from_photo`.
- `message`.
- `color_choice`.
- `size_choice`.
- `attach_card`.
- `qr_memory`.
- `fully_custom_design`.

Quan hệ/cấu hình nên chứa tối thiểu:

- `product_id`, `capability_id`.
- `required`, `input_type`, `min/max`, `price_delta`, `lead_time_delta_days`.
- `applies_to_variant_id` nếu khả năng chỉ có ở một số biến thể.

Prototype và mock hiện có dấu hiệu lệch từ vựng: “Thêm thiệp điện tử”, “Có thể thêm thiệp”, “Gắn mã QR kỷ niệm”, “Khắc tên” và “Khắc hoặc in tên” được dùng ở các trường khác nhau. Catalog capability với code chuẩn sẽ cho phép nhiều nhãn hiển thị nhưng vẫn lọc đúng cùng một khái niệm.

### 5.6. Theo thời gian chuẩn bị — thuộc tính vận hành, không phải catalog

Không nên lưu các nhãn `1–2 ngày`, `3–5 ngày`, `5–7 ngày` như category. Chúng là bucket được suy ra từ dữ liệu vận hành.

Đề xuất lưu:

- `fulfillment_mode`: ready_stock, made_to_order.
- `prep_min_days`, `prep_max_days`.
- `supports_rush`.
- `rush_prep_days` hoặc SLA riêng nếu làm gấp.
- Có thể có override theo SKU, năng lực xưởng, thời điểm hoặc số lượng đặt.

Frontend/API quy đổi số ngày thành các bucket. “Có hỗ trợ làm gấp” là một cờ độc lập, không phải một khoảng thời gian; prototype đã ngầm phản ánh điều này bằng `rush` tách khỏi `prep`, nhưng lại đặt chung trong một nhóm filter. UI có thể vẫn đặt gần nhau, song query model nên tách `prepRange` và `supportsRush`.

Nếu ngày chuẩn bị thay đổi theo tải sản xuất, catalog tĩnh sẽ nhanh lỗi thời. Giá trị dùng để lọc nên là SLA hiện hành đã tính toán, không chỉ mô tả marketing.

### 5.7. Theo chất liệu — catalog tham chiếu + quan hệ sản phẩm

Chất liệu có giá trị lặp lại, cần chuẩn hóa tên và hữu ích cho filter, thông số sản phẩm, tìm kiếm và báo cáo; vì vậy nên có catalog tham chiếu.

Đề xuất:

- `material(id, slug, name, parent_id?, status, sort_order)`.
- `product_material(product_id, material_id, role, percentage?, is_primary)`.

`role` có thể là main, frame, surface, packaging. Điều này tốt hơn một mảng chuỗi vì sản phẩm như đèn có cả Gỗ và Acrylic, còn hộp quà có Giấy và Vải.

Tuy nhiên chất liệu vẫn là thông tin đính kèm của từng sản phẩm thông qua quan hệ. Không nhất thiết tạo landing page công khai cho mọi material; catalog ở đây chủ yếu để chuẩn hóa dữ liệu và facet.

Cần loại `Kẽm nhung` khỏi “loại sản phẩm” khi nó chỉ mô tả chất liệu. Nếu kinh doanh thực sự coi “Hoa kẽm nhung” là dòng hàng, category nên là “Hoa kẽm nhung”, còn material vẫn là “Kẽm nhung”.

### 5.8. Đánh giá — dữ liệu dẫn xuất từ review

Không tạo catalog “4 sao”, “4,5 sao”. Rating phải được tổng hợp từ các review hợp lệ:

- `rating_average`.
- `rating_count`.
- Có thể thêm phân bố 1–5 sao.

Hai trường này có thể được cache trên product/search index để lọc và sắp xếp nhanh, nhưng nguồn sự thật vẫn là review. Khi chưa có đánh giá, phải phân biệt `null/no reviews` với 0 sao.

Nên xác định quy tắc làm tròn và ngưỡng filter rõ ràng: “Từ 4,5 sao” nghĩa là giá trị trung bình chưa làm tròn `>= 4.5`. Với ít đánh giá, có thể dùng Bayesian score cho sắp xếp “phù hợp/yêu thích”, nhưng filter vẫn dùng average và minimum review count nếu cần chống nhiễu.

## 6. Mô hình dữ liệu khuyến nghị

### 6.1. Catalog/reference data

Các catalog nên có cấu trúc quản trị thống nhất:

- `occasion` — dùng chung thiệp và quà.
- `card_style`.
- `card_format` hoặc ba nhóm `aspect_ratio`, `card_capability`, `delivery_channel`.
- `product_category` — hỗ trợ phân cấp.
- `recipient_segment`.
- `personalization_capability`.
- `material`.
- `color_family` — reference nhỏ cho facet, không bắt buộc là catalog điều hướng.
- `collection` — dành cho nhóm biên tập/marketing, tách khỏi category.

Mỗi catalog nên có tối thiểu `id`, `slug/code`, `name`, `status`, `sort_order`, timestamps; tên hiển thị có thể localize mà không làm thay đổi code.

### 6.2. Thuộc tính của card template

- `access_tier` hoặc pricing/entitlement relation.
- `background`, `foreground`, palette thực tế.
- `pages`, feature/capability kỹ thuật, số lượt dùng, số lượt thích.
- Quan hệ tới occasion, style, format và color family.

Số lượt dùng/thích là metric dẫn xuất; không phải catalog và không nên được biên tập như metadata tĩnh.

### 6.3. Thuộc tính của product/SKU

- Giá hiện hành, giá so sánh, tiền tệ.
- Tồn kho và khả dụng.
- Thời gian chuẩn bị min/max, fulfillment mode, hỗ trợ làm gấp.
- Rating average/count được tổng hợp.
- Màu/kích thước chọn mua nên là option/variant, không phải chuỗi mô tả chung.
- Quan hệ tới category, occasion, recipient, personalization capability và material.

## 7. API facet đề xuất

Frontend không nên hard-code toàn bộ danh sách và tự đếm như prototype. Endpoint listing nên trả kết quả cùng facet, ví dụ:

```json
{
  "items": [],
  "page": { "number": 1, "size": 24, "total": 0 },
  "facets": {
    "occasion": [{ "id": "...", "slug": "sinh-nhat", "label": "Sinh nhật", "count": 12 }],
    "category": [{ "id": "...", "slug": "khung-anh", "label": "Khung ảnh", "count": 8 }],
    "price": { "min": 189000, "max": 1190000 },
    "prepDays": [{ "from": 1, "to": 2, "count": 5 }],
    "supportsRush": { "true": 7 },
    "rating": [{ "gte": 4.5, "count": 14 }]
  }
}
```

Facet count nên được tính theo tập kết quả hiện tại để tránh hiển thị lựa chọn luôn trả về rỗng. URL dùng slug/code ổn định, không dùng nhãn tiếng Việt làm định danh.

## 8. Thứ tự triển khai khuyến nghị

### Giai đoạn 1 — taxonomy cốt lõi

1. Tạo catalog dùng chung `occasion`.
2. Tạo `product_category`, làm sạch việc trộn category/tag/material/capability.
3. Tạo `card_style`, `recipient_segment`, `material`.
4. Chuyển quan hệ của thiệp và quà sang nhiều-nhiều với ID ổn định.

### Giai đoạn 2 — dữ liệu thương mại và vận hành

1. Đưa giá xuống offer/SKU và sinh price buckets khi query.
2. Chuẩn hóa prep time thành min/max days, fulfillment mode và rush flag.
3. Tổng hợp rating từ review.
4. Chuẩn hóa màu/kích thước thành option và variant khi chúng ảnh hưởng SKU hoặc giá.

### Giai đoạn 3 — capability và merchandising

1. Tạo `personalization_capability` và schema input/validation tương ứng.
2. Tách `collection` khỏi `product_category`.
3. Tách định dạng thiệp thành aspect ratio, capability và delivery channel nếu editor/export bắt đầu phụ thuộc mạnh vào chúng.
4. Trả dynamic facets và counts từ API/search index.

## 9. Quyết định cuối cùng

Nên triển khai thành **catalog thực sự**: dịp, phong cách thiệp, định dạng/capability thiệp, loại sản phẩm, phân khúc người nhận; đồng thời có catalog tham chiếu cho khả năng cá nhân hóa và chất liệu. Màu sắc phù hợp với một palette tham chiếu nhỏ hơn là catalog điều hướng.

Nên triển khai thành **thuộc tính hoặc dữ liệu dẫn xuất gắn với sản phẩm/template/SKU**: mức phí của thiệp, giá quà, thời gian chuẩn bị, hỗ trợ làm gấp và đánh giá. Khả năng cá nhân hóa, chất liệu, màu và định dạng là các trường hợp lai: tên/định nghĩa được chuẩn hóa tập trung, còn giá trị áp dụng và cấu hình cụ thể phải nằm trên quan hệ với sản phẩm hoặc template.

Điểm cần sửa quan trọng nhất trước khi thiết kế database là không sao chép nguyên danh sách “Theo loại sản phẩm” của prototype thành category. Danh sách này đang trộn loại hàng, chất liệu, phương thức sản xuất, capability cá nhân hóa và collection marketing; nếu giữ nguyên, backend sẽ khó đảm bảo dữ liệu nhất quán và frontend sẽ sớm xuất hiện các bộ lọc trùng nghĩa.
