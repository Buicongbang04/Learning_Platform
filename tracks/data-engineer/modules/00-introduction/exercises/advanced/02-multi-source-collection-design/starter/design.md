# Thiết kế thu thập đa nguồn

## Kiến trúc

TODO: sơ đồ ```mermaid từ 5 nguồn tới vùng thô (bronze), vùng sạch, và người dùng; mỗi mũi tên ghi pull/push.

## Lịch chạy và phụ thuộc

TODO: job nào chạy khi nào, job nào phải chờ job nào, cái gì xảy ra nếu một nguồn trễ.

## Idempotency và chạy lại

TODO: chạy lại một ngày bất kỳ (backfill) thế nào mà không nhân đôi; khoá dedup/upsert từng nguồn.

## Dữ liệu đến trễ

TODO: event time vs ingestion time, cửa sổ late data của từng nguồn, xử lý partition cũ.

## Bảo mật và PII

TODO: cột nào là PII, xử lý ở bước nào (mask/hash/tách bảng), ai được đọc vùng thô.

## Giám sát

TODO: chỉ số và ngưỡng cảnh báo cho từng nguồn (độ tươi, số bản ghi, tỉ lệ reject...).

## Chi phí và dung lượng

TODO: ước lượng GB/ngày từng nguồn bằng con số (dùng số đo ở bài intermediate 02), số request API/ngày, retention.
