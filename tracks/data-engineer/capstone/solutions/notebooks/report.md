# Báo cáo mẫu: khám phá bộ Olist thật

## Bộ dữ liệu

- **Nguồn**: Brazilian E-Commerce Public Dataset by Olist (Kaggle `olistbr/brazilian-ecommerce`), giấy phép
  CC BY-NC-SA 4.0. Tải bằng `uv run python data/download_olist.py` vào `data/raw/`.
- **Kích thước**: 9 tệp CSV, 121 MB (62 MB nếu bỏ `geolocation`, 1 triệu dòng tọa độ chưa dùng ở đây).
  99 441 đơn, 112 650 item, 103 886 payment, 99 224 review, 32 951 sản phẩm, 3 095 seller, 96 096 khách thật.
- **Thời gian**: đơn mua từ 04/09/2016 tới 17/10/2018, nhưng chỉ 01/2017–08/2018 là đủ tháng (09–12/2016 có
  ~330 đơn, 09–10/2018 chỉ 20 đơn).
- **Grain**: `orders` một dòng mỗi đơn; `order_items` mỗi item trong đơn (khoá `order_id, order_item_id`);
  `order_payments` mỗi lần trả (một đơn có thể trả nhiều cách); `order_reviews` mỗi review (không duy nhất
  theo đơn); `customers` mỗi `customer_id`, mà `customer_id` là id **của đơn**, người mua thật là
  `customer_unique_id`.

## Làm sạch

- **Đơn đã giao**: 96 478 đơn `delivered`, nhưng 8 đơn thiếu `order_delivered_customer_date`, nên
  `is_delivered` có 96 470 đơn. Mọi chỉ số giao hàng tính trên 96 470 đơn này.
- **Trễ hạn tính theo ngày lịch**: ngày dự kiến luôn là 00:00, so cả giờ thì đơn giao 15h đúng ngày hẹn
  cũng thành trễ. `delay_days` là ngày giao − ngày dự kiến (bỏ giờ), `is_late = delay_days > 0`, `<NA>` cho đơn
  chưa giao thay vì `False` (chưa giao không có nghĩa là đúng hạn).
- **Mốc thời gian vô lý**: 189 đơn (166 đơn giao hãng trước lúc mua, 23 đơn khách nhận trước lúc giao hãng)
  được gắn cờ `bad_timeline`, **không xoá**: xoá làm số đơn lệch nguồn, và đây là manh mối lỗi đồng bộ đồng hồ
  ở hệ thống nguồn mà M10 sẽ biến thành rule chất lượng mức `warn`.
- **Review**: 814 `review_id` dùng lại cho nhiều đơn, 551 đơn có hơn một review. Giữ review trả lời sau cùng,
  mỗi đơn một dòng; 768 đơn không có review.
- **Join không nhân tiền**: gom `items` và `payments` theo `order_id` trước khi join, kiểm bằng
  `validate="one_to_one"`. Tổng `items_value` = tổng `price` gốc = 13 591 643,70 BRL.
- **Danh mục**: 610 sản phẩm không có danh mục (thành `unknown`), 2 danh mục không có bản dịch (`pc_gamer`,
  `portateis_cozinha_e_preparadores_de_alimentos`) giữ tên gốc. Zip đọc kiểu chuỗi để giữ số 0 đầu.
- **Dữ liệu sạch**: `data/clean/olist/order_facts.parquet`, 99 441 dòng × 18 cột, 10,3 MB (CSV gốc của các bảng
  đã dùng 62 MB). Ghi qua tệp tạm rồi `os.replace`, chạy lại vẫn 99 441 dòng.

## Insight

1. **Trễ hạn là thứ giết điểm review.** 6,77% đơn đã giao bị trễ. Đơn đúng hạn được trung bình 4,29 sao,
   đơn trễ chỉ 2,27 sao; tỉ lệ review 1–2 sao tăng từ 9,3% lên 62,4%. Trễ hơn 7 ngày còn 1,70 sao (79% là 1–2
   sao). Nghĩa là KPI vận hành quan trọng nhất cho dashboard M09 là `late_share`, không phải thời gian giao
   trung bình (trung vị 10,2 ngày, vì Olist hẹn rất rộng: 75 744 đơn tới sớm ≥ 7 ngày).
2. **Đông Bắc giao kém.** Alagoas (AL) trễ 21,4% số đơn, gấp hơn ba lần trung bình cả nước; theo sau là MA
   17,4%, SE 15,2%, PI 13,9%, CE 13,8%: các bang xa São Paulo, nơi phần lớn seller ở. RJ (12,1% trên 12 350 đơn)
   là bang lớn duy nhất trong nhóm đầu. Đây là bộ lọc theo bang mà dashboard cần.
3. **Thẻ tín dụng và trả góp.** 76,9% đơn có trả bằng `credit_card` (78,3% giá trị), 19,9% bằng `boleto`; 66,9%
   lần trả bằng thẻ là trả góp (> 1 kỳ). Pipeline phải giữ được nhiều dòng payment mỗi đơn, không được giả định
   một đơn một payment.
4. **Seller rất tập trung.** 10% seller lớn nhất (310 / 3 095) chiếm 67,6% GMV; chỉ 130 seller đã chiếm một nửa.
   SCD2 cho `dim_seller` (M02) và scorecard seller đáng làm kỹ cho nhóm nhỏ này.
5. **Danh mục và khách quay lại.** `health_beauty` dẫn đầu doanh thu (1 258 681 BRL), sát sau là `watches_gifts`
   (1 205 006 BRL). Chỉ 3,0% khách thật (`customer_unique_id`) có từ 2 đơn trở lên: Olist gần như toàn khách mua
   một lần, nên phân tích cohort/retention trên bộ này ít ý nghĩa, và đếm khách bằng `customer_id` sẽ sai hẳn.

## Giới hạn

- Đây là **mẫu đã ẩn danh** Olist công bố (~100 nghìn đơn), không phải toàn bộ giao dịch; tên seller/sản phẩm bị
  thay bằng hash, review tiếng Bồ. Không suy ra quy mô thật của Olist.
- Tháng đầu và cuối bị cắt (09–12/2016, 09–10/2018): biểu đồ theo tháng phải bỏ hoặc đánh dấu, đừng đọc là doanh
  thu sụt.
- `is_late` dựa trên ngày dự kiến Olist đưa ra lúc mua; nếu hệ thống hẹn quá rộng thì "đúng hạn" không có nghĩa
  là nhanh. Quan hệ trễ → review là tương quan; đơn trễ có thể còn lỗi khác (hàng sai, hỏng) cùng làm điểm thấp.
- Các con số phụ thuộc định nghĩa đã chọn: trễ theo ngày lịch (so cả giờ thì tỉ lệ trễ cao hơn), giữ review sau
  cùng, bỏ đơn `canceled`/`unavailable` khi tính mua lại (tính cả thì 3,1%), ngưỡng 100 đơn khi xếp bang.
