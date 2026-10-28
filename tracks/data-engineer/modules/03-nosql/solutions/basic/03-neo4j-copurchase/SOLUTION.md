# Lời giải: gợi ý "mua cùng" bằng graph

## Python thuần

Dựng `customer -> set(product)`. Dùng `set` để một khách mua cùng sản phẩm nhiều lần chỉ được đếm một lần
(`count(DISTINCT c)` trong Cypher). Với mỗi khách có `product_id`, cộng các sản phẩm còn lại vào `Counter`. Sort
bằng khoá `(-count, product_id)` để kết quả xác định khi hoà.

Chi phí: phải duyệt toàn bộ lượt mua mỗi lần hỏi, trừ khi bạn tự xây index `product -> customers`. Đó chính là
thứ graph database giữ sẵn (index-free adjacency).

## Cypher

- **Constraint trước khi nạp**: unique constraint vừa chống trùng, vừa tạo index để `MERGE` tìm node nhanh. Không
  có nó, mỗi `MERGE` quét toàn bộ label và nạp dữ liệu lớn sẽ cực chậm.
- **`UNWIND $rows` + `MERGE`**: gửi cả batch trong một lệnh (ít round-trip), và `MERGE` = "tìm, không có thì
  tạo" nên chạy lại không sinh trùng. `ON CREATE SET` chỉ gán thuộc tính khi node mới được tạo.
- Đặt `order_id` trong pattern của `MERGE` quan hệ để hai đơn khác nhau của cùng khách và sản phẩm là hai quan
  hệ, còn chạy lại cùng đơn thì không nhân đôi.
- Truy vấn co-purchase là pattern hai bước:
  `(:Product {id: $pid})<-[:BOUGHT]-(c)-[:BOUGHT]->(o)`, lọc `o.id <> $pid`, gom `count(DISTINCT c)`.
  Luôn truyền tham số (`$pid`, `$k`) thay vì nối chuỗi: an toàn với injection và Neo4j cache được query plan.

## Bàn thêm

- Trong SQL, cùng truy vấn là self-join `order_items` qua `customer_id`; với hàng triệu khách và sản phẩm phổ
  biến, join bùng nổ. Graph chỉ duyệt hàng xóm của một node.
- Gợi ý thực tế cần chuẩn hoá theo độ phổ biến (Jaccard, lift) để không lúc nào cũng gợi ý sản phẩm bán chạy
  nhất. Neo4j GDS có `gds.nodeSimilarity`.
- Với Data Engineer, graph thường được nạp **từ warehouse** (batch hằng ngày) rồi phục vụ ứng dụng; hoặc tính
  co-purchase bằng SQL/Spark rồi đẩy top-k vào Redis.
