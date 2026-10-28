# Thiết kế tầng lưu trữ NoSQL cho tracking và review Olist

## Bối cảnh và giả định

TODO: tóm tắt yêu cầu, ước lượng khối lượng (sự kiện/ngày, ghi/giây, đọc/giây, kích thước một partition).

## Access patterns

TODO: liệt kê từng truy vấn: ai gọi, tham số đầu vào, kết quả, tần suất, yêu cầu độ trễ.

## Lựa chọn database

TODO: bảng nhu cầu → store → lý do; giải thích vì sao không dùng một store cho tất cả.

## Mô hình dữ liệu

TODO: giải thích từng bảng Cassandra (partition key, clustering key, TTL, compaction) và document review MongoDB
(embedding hay referencing cho ảnh, câu trả lời của seller).

## Consistency và hỏng hóc

TODO: consistency level đọc/ghi, replication, điều gì xảy ra khi một node/DC chết, idempotency khi ghi lại.

## Đưa dữ liệu về lakehouse

TODO: CDC hay export, định dạng, tần suất, xử lý schema drift và bản ghi bị xoá.

## Rủi ro và phương án thay thế

TODO: hot partition, tombstone, chi phí vận hành; phương án thay thế (DynamoDB, PostgreSQL partitioning,
ScyllaDB...) và vì sao không chọn.
