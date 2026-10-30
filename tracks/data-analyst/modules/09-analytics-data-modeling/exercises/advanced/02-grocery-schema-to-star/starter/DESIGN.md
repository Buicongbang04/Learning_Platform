# Star schema cho Grocery Sales

Gửi: team BI. Từ: <tên bạn>. Nguồn: schema 7 bảng Grocery Sales (dữ liệu sinh giả, chỉ dùng để luyện thiết kế).
250-1200 từ. Xoá mọi dòng TODO khi viết xong.

## Grain

TODO: câu "một dòng = ..." cho fct_sales; vì sao không chọn grain giỏ hàng (TransactionNumber) và bạn đã kiểm điều
đó bằng truy vấn nào.

## Bảng và khoá

TODO: sơ đồ (mermaid erDiagram hoặc bảng) fact + 4 dimension; khoá thay thế lấy từ đâu; vì sao gộp categories,
cities, countries vào dimension phẳng thay vì giữ snowflake; role của employees trong fact.

## Quyết định với dữ liệu nguồn

TODO: TotalPrice luôn bằng 0 thì tính tiền thế nào và giới hạn của cách đó (giá hiện tại, ModifyDate, không có
lịch sử giá); dòng thiếu SalesDate; khoá không khớp dimension; giá trị 'Unknown' trong IsAllergic/Resistant; SCD
cho thành phố của khách nếu nguồn có lịch sử.

## Data test

TODO: các test bạn sẽ gắn nếu chuyển sang dbt (unique, not_null, relationships, accepted_values, đối soát số dòng),
mức error/warn và lý do; kết quả đối soát trên bộ thật (số dòng fact, số dòng unknown).

## Không rút insight

TODO: vì sao mô hình này chỉ để luyện thiết kế và không được dùng để báo cáo doanh số (dẫn kết luận ở module 06),
và bạn sẽ nói gì nếu stakeholder hỏi "sản phẩm nào bán chạy nhất" trên bộ này.
