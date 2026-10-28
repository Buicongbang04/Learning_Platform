# Lời giải: Data skew và salting

## Đo skew

- `key_distribution` là bước đầu tiên khi một stage có task chạy lâu bất thường: xem top key. Trên dữ
  liệu Olist, vài seller lớn và các giá trị NULL/"unknown" là thủ phạm thường gặp.
- `partition_sizes` cho thấy hậu quả: `repartition(4, "seller_id")` băm theo key, nên **mọi** dòng của
  seller nóng vào cùng một partition, tức một task. Thêm executor không giúp gì.

## Salting

- Thêm `salt ∈ [0, N)` vào bên lớn, key mới là `(seller_id, salt)`: dòng của seller nóng chia vào N
  partition khác nhau.
- Bên nhỏ phải có đủ mọi giá trị salt để dòng nào bên lớn cũng tìm được cặp: `crossJoin` với
  `range(N)`, nên bên nhỏ to lên N lần. Đó là đánh đổi; chọn N vừa đủ (vd. 8–32), hoặc chỉ salt các key
  nóng (tách key nóng ra, salt riêng, `union` với phần còn lại).
- Aggregation: tầng 1 theo `(key, salt)` giảm mạnh dữ liệu, tầng 2 theo `key` chỉ còn tối đa N dòng mỗi
  key. Chỉ đúng với phép gộp kết hợp được (sum, count, min, max); average phải tính qua sum và count.

## Chọn cách sinh salt

`F.rand(seed)` đơn giản nhưng không tất định nếu partitioning đầu vào thay đổi (task retry có thể ra
salt khác; với join thì kết quả vẫn đúng vì bên nhỏ có mọi salt). `pmod(monotonically_increasing_id, N)`
chia đều theo vòng tròn trong từng partition.

## Trước khi salt, thử cách rẻ hơn

1. Broadcast bên nhỏ (ở đây `sellers` nhỏ, broadcast là đủ và không shuffle bên lớn).
2. Bật AQE skew join (`spark.sql.adaptive.skewJoin.enabled`, mặc định bật ở Spark 3.x).
3. Lọc key rác (NULL) và xử lý riêng.
Salting dành cho khi cả hai bên đều lớn hoặc khi aggregation theo key nóng.
