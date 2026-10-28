---
title: Thiết kế tầng lưu trữ NoSQL cho tracking và review Olist
level: advanced
services: [cassandra, mongo]
files:
  - path: starter/DESIGN.md
    note: Tài liệu thiết kế, 7 phần TODO
  - path: starter/schema.cql
    note: Bảng Cassandra, 2 TODO
  - path: starter/mongo_schema.py
    note: Validator và index MongoDB, 2 TODO
  - path: tests/test_design.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/advanced/02-olist-nosql-design -q
  - docker compose -f setup/docker-compose.yml up -d cassandra mongo
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/advanced/02-olist-nosql-design -q
---

## Mục tiêu

Làm một bài thiết kế hệ thống giống phỏng vấn Data Engineer: từ yêu cầu nghiệp vụ, liệt kê access pattern, chọn
store, mô hình hoá dữ liệu, nêu consistency và cách đưa dữ liệu về lakehouse. Kết quả là một tài liệu thiết kế có
lập luận cùng schema chạy được, không chỉ là code.

## Đề bài

Olist mở rộng: 3 triệu đơn mỗi tháng, mỗi đơn sinh khoảng 15 sự kiện vận chuyển (tạo vận đơn, lấy hàng, qua kho,
giao...). Có bốn nhu cầu:

1. **Khách** mở trang đơn hàng và xem toàn bộ hành trình, mới nhất trước. Mục tiêu p99 dưới 20 ms, khoảng 5.000
   lượt/giây giờ cao điểm.
2. **Đội vận hành** xem danh sách đơn **trễ hạn** theo bang của khách cho từng ngày giao dự kiến, cập nhật gần
   thời gian thực.
3. **Review**: khách viết review (điểm 1–5, tiêu đề, nội dung, ảnh tuỳ chọn, seller trả lời sau). Trang sản phẩm
   hiện review mới nhất; CSKH tra review theo `order_id`; có hàng đợi review điểm thấp chưa trả lời.
4. **Analytics** cần toàn bộ dữ liệu trên lakehouse hằng ngày (module 04).

Nộp ba tệp trong `starter/`:

- `DESIGN.md`: hoàn thiện đủ 7 phần có sẵn, mỗi phần ít nhất vài câu có lập luận (không để `TODO`). Phần
  "Lựa chọn database" có một bảng nhu cầu → store → lý do. Ước lượng kích thước (sự kiện/ngày, kích thước partition)
  ở phần "Bối cảnh và giả định".
- `schema.cql`: tối thiểu hai bảng `shipment_events_by_order` (nhu cầu 1) và `late_orders_by_state_day` (nhu cầu
  2). Có thể thêm bảng khác nếu cần. Không dùng `ALLOW FILTERING`.
- `mongo_schema.py`: `REVIEW_VALIDATOR` (một `$jsonSchema` validator cho collection `reviews`) và `REVIEW_INDEXES`
  (list index, mỗi index là list `(field, 1 | -1)`) phục vụ ba truy vấn ở nhu cầu 3.

## Tiêu chí đạt

- Test tĩnh offline pass: đủ 7 phần, không còn `TODO`, có bảng so sánh; schema CQL có partition key hợp lý cho
  hai truy vấn; validator yêu cầu đủ trường và giới hạn `score` từ 1 tới 5; có index cho cả ba truy vấn review.
- Khi bật dịch vụ: schema CQL tạo được trên Cassandra; validator thật sự chặn review sai trên MongoDB.
- Tài liệu nêu được: consistency level đọc/ghi, cách tránh partition lớn và tombstone, đường đi của dữ liệu từ
  nguồn tới Cassandra/MongoDB/lakehouse, và phương án thay thế (vd. DynamoDB, PostgreSQL partitioning) kèm lý do
  không chọn.

## Gợi ý

### Gợi ý 1

Nhu cầu 2 không thể là `SELECT ... WHERE delivered = false` trên bảng nhu cầu 1. Hãy để một consumer (Kafka/stream)
phát hiện đơn trễ và ghi vào bảng riêng có partition `(customer_state, expected_date)`. Khi đơn được giao, xoá
dòng — nghĩ xem tombstone có thành vấn đề không, và vì sao partition theo ngày giúp giảm nó.

### Gợi ý 2

Validator MongoDB dùng `bsonType`: `{"$jsonSchema": {"bsonType": "object", "required": [...], "properties":
{"score": {"bsonType": "int", "minimum": 1, "maximum": 5}, ...}}}`. Hàng đợi review điểm thấp chưa trả lời có thể
dùng compound index `(answered, score, created_at)` hoặc partial index.
