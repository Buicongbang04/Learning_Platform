# Lời giải: Join strategies

## Broadcast Hash Join

`broadcast(products)` là hint: Spark gom `products` về driver, gửi một bản tới mỗi executor, dựng hash
table trong bộ nhớ; mỗi partition của `items` dò hash table tại chỗ. `items` **không bị shuffle**, plan
không có `Exchange hashpartitioning` cho bên lớn mà có `BroadcastExchange` cho bên nhỏ.

Không có hint, Spark tự broadcast khi ước lượng kích thước một bên nhỏ hơn
`spark.sql.autoBroadcastJoinThreshold` (mặc định 10 MB). Dữ liệu tạo bằng `createDataFrame` rất nhỏ nên
Spark thường tự broadcast; vì vậy muốn thấy sort-merge phải đặt ngưỡng `-1`.

## Sort-Merge Join

Cả hai bên `Exchange hashpartitioning(product_id)` rồi `Sort`, sau đó merge hai luồng đã sắp. Ổn định
cho hai bảng lớn, spill được ra đĩa, nhưng tốn hai lần shuffle và sort.

## Thay đổi cấu hình an toàn

`spark.conf` là trạng thái dùng chung của cả SparkSession. Một hàm thư viện đổi cấu hình mà không trả
lại sẽ làm hỏng các job khác chạy sau (rất khó debug). Mẫu `old = get; set; try ... finally set(old)`
bảo đảm khôi phục cả khi có exception. Plan và `collect()` phải nằm trong `try`, vì DataFrame lazy: plan
vật lý chỉ được chọn khi bị yêu cầu lần đầu.

## Khi nào chọn gì

| Tình huống | Chọn |
| --- | --- |
| Dimension nhỏ (products, sellers, vài MB) join fact lớn | Broadcast |
| Hai fact lớn (orders × order_items) | Sort-merge (mặc định) |
| Bảng "nhỏ" vài GB | Đừng broadcast: OOM driver/executor, timeout |
| Không chắc kích thước sau filter | Để AQE quyết định lúc chạy |
