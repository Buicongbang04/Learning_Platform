# Lời giải: báo cáo chất lượng dữ liệu tự động cho Olist

Notebook lời giải: `quality.ipynb` (chạy được toàn bộ khi đã tải Olist thật).

## Cách làm

Mọi kiểm tra quy về ba dạng: khoá lặp, khoá ngoại mồ côi, thứ tự thời gian sai. Viết ba hàm nhỏ,
test được, rồi `quality_report` chỉ còn là một bảng "tên → (n_failed, n_total)" cộng một vòng dựng
DataFrame theo `CHECKS`. Tách như vậy để thêm kiểm tra mới là thêm một dòng, và để mỗi kiểm tra có
mẫu số riêng: tỉ lệ "thiếu ngày giao" chỉ có nghĩa trên đơn `delivered`, không phải trên mọi đơn.

Hai chi tiết dễ sai:

- **Thứ tự thời gian chỉ kiểm dòng có cả hai ngày.** Null không phải vi phạm thứ tự (nó đã được kiểm
  ở kiểm tra "thiếu"), và đưa null vào mẫu số làm tỉ lệ nhỏ đi giả tạo.
- **Cộng theo đơn trước khi ghép** payment với item, để không nhân dòng.

## Kết quả trên Olist thật

| check | severity | n_failed | n_total |
| --- | --- | --- | --- |
| orders_pk_duplicated | error | 0 | 99 441 |
| delivered_missing_delivery_date | warning | 8 | 96 478 |
| delivered_missing_approved_at | warning | 14 | 96 478 |
| carrier_after_customer_delivery | error | **23** | 96 475 |
| approved_before_purchase | error | 0 | 99 281 |
| orders_without_items | warning | 775 | 99 441 |
| items_orphan_order | error | 0 | 112 650 |
| items_orphan_product | error | 0 | 112 650 |
| orders_without_review | warning | 768 | 99 441 |
| review_id_duplicated | warning | 1 603 | 99 224 |
| products_missing_category | warning | 610 | 32 951 |
| category_not_translated | warning | 13 | 32 341 |
| customer_zip_not_in_geolocation | warning | 278 | 99 441 |
| payment_items_mismatch | warning | 249 | 98 665 |
| freight_zero | info | 383 | 112 650 |

`blocking_checks` → `["carrier_after_customer_delivery"]`. 11 trong 23 đơn có timeline sai được mua
trong tháng 7/2017: lỗi tập trung theo thời gian thường là dấu hiệu của một sự cố hệ thống (một đợt
tích hợp với hãng vận chuyển) chứ không phải lỗi nhập tay rải rác. Đó là câu hỏi cụ thể để mang tới
đội dữ liệu nguồn.

## Rubric cho phần "Đọc báo cáo"

| Tiêu chí | Đạt khi |
| --- | --- |
| Lỗi chặn | Nêu 23 đơn, vì sao không thể xảy ra, phân tích nào bị ảnh hưởng và phân tích nào không |
| Kiểm tra bằng 0 | Nhận ra đó cũng là thông tin (join items → orders/products an toàn) |
| Cảnh báo có hệ quả | Chỉ ra hệ quả cụ thể cho người phân tích sau (hai cách đếm "số đơn" lệch nhau; dedupe review theo `order_id`) |
| Thông tin | Phí vận chuyển 0 là nghiệp vụ (miễn phí vận chuyển), không phải lỗi |
| Hành động | Đề xuất chạy tự động, chặn hoặc gắn cờ khi có lỗi chặn |

## Sai lầm hay gặp

- Một tỉ lệ cho mọi kiểm tra trên cùng mẫu số "tổng số đơn": làm 8 đơn thiếu ngày giao trông như
  không đáng kể ở mọi ngữ cảnh.
- Gán severity theo con số ("nhiều thì là error"): 1 603 review lặp là cảnh báo, 23 đơn timeline sai
  là lỗi chặn. Severity theo **tác động lên phân tích**, không theo số lượng.
- Viết báo cáo một lần trong notebook rồi thôi. Giá trị nằm ở việc chạy lại mỗi lần dữ liệu đổi.
