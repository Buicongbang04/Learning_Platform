# Lời giải: tối ưu pipeline pandas

## Cách làm

Đọc hàm chậm như đặc tả và tách ra bốn khối, mỗi khối là một phép toán trên cột:

1. **Đơn giao xong + cờ trễ**: lọc bằng mặt nạ boolean, `late` là so sánh hai cột datetime (một vòng
   lặp C), thay cho vòng `iterrows` trên `orders`.
2. **Review mới nhất**: `sort_values("review_answer_timestamp").drop_duplicates("order_id",
   keep="last")`, thay cho dict cập nhật từng dòng.
3. **Doanh thu theo món**: `merge` món với đơn giao xong, `groupby("seller_id").price.sum()`.
4. **Tỉ lệ theo đơn**: `items[["seller_id", "order_id"]].drop_duplicates()` cho mỗi cặp (seller, đơn)
   một dòng, `merge` với khối 1 và khối 2 (`validate="many_to_one"`), rồi `groupby().agg()`.

Chi tiết dễ sai nhất là **grain**: doanh thu cộng theo món, còn `n_orders`, `late_rate`,
`review_score` tính theo đơn. Merge thẳng món với review rồi lấy `mean` thì đơn 3 món của một seller
nặng gấp 3 lần đơn 1 món. Chi tiết thứ hai: `bad` phải là NaN cho đơn không có review
(`(score <= 2).where(score.notna())`); nếu để `False` thì đơn không review bị tính là "review tốt" và
`bad_review_rate` bị kéo xuống.

## Kết quả

- Olist thật: bản chậm khoảng 7–10 giây, bản nhanh 0.3–0.6 giây, nhanh hơn 16–23 lần tuỳ tải máy lúc
  đo; `assert_frame_equal` xác nhận cùng kết quả (2 970 seller, tổng doanh thu 13 220 248.93).
- Test 1 triệu món: bản nhanh vài giây; bản `iterrows` vượt mốc 20 giây (đo khi viết bài: bản chậm
  mất 6.2 giây cho chỉ 100 nghìn món). Một bản lai chỉ dùng `apply(axis=1)` cho cột `late` mất khoảng
  10–12 giây, sát giới hạn: vì vậy test còn kiểm mã nguồn không chứa `apply`.

## optimize_dtypes

Cột chuỗi có tỉ lệ giá trị khác nhau thấp thành `category`; số nguyên downcast. Trên Olist:
`order_items` từ 19.3 MB xuống 11.6 MB (`seller_id`, `product_id` thành category, `order_item_id` thành
`int8`); `orders` chỉ giảm từ 17.4 MB xuống 15.8 MB vì hai cột lớn nhất (`order_id`, `customer_id`) là
duy nhất trên mỗi dòng, category không giúp được gì. Bài học: kiểm tra trước khi áp dụng mù quáng; với
khoá duy nhất, đọc ít cột (`usecols`) hoặc dùng Parquet mới là cách giảm bộ nhớ.

Lưu ý: ngưỡng 0.5 là quy ước của bài; trong thực tế category có lợi khi số giá trị khác nhau nhỏ hơn
nhiều so với số dòng (dưới vài phần trăm), và cần cẩn thận khi nối hai bảng có category khác tập giá trị.
