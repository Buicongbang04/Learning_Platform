# Lời giải: ước tính hoá đơn cloud

## Cách làm

- **Storage**: tuyến tính `GB x giá x tháng`. Kiểm tra tham số âm một chỗ (`_non_negative`) để
  mọi hàm cùng hành vi.
- **Egress lũy tiến**: giống thuế thu nhập bậc thang, mỗi bậc chỉ tính phần dữ liệu **nằm trong
  bậc đó**: `min(gb, upper) - lower`. Lỗi hay gặp là lấy giá của bậc cao nhất nhân cho toàn bộ
  lượng dữ liệu (tính kiểu "lũy thoái").
- **Scan**: `max(0, tb - free_tb) * giá`, BigQuery on-demand cho 1 TiB miễn phí mỗi tháng.
- **Làm tròn**: chỉ làm tròn ở lớp trình bày (`monthly_bill`), không làm tròn trong hàm tính toán
  để tránh sai số tích lũy khi cộng nhiều dòng.

## Đọc kết quả

Ví dụ trong test: lưu 2 TB (≈ 47 USD), cho đối tác tải 1.1 TB ra ngoài (≈ 92 USD), BI quét 11 TB
(≈ 62 USD). **Egress đắt gấp đôi lưu trữ**, và scan có thể giảm 10x nếu bảng được partition theo
ngày + lưu Parquet. Đó là lý do câu hỏi FinOps trong phỏng vấn thường xoay quanh egress và scan,
không phải giá GB lưu trữ.

Khi làm thật: AWS Pricing Calculator, Azure Pricing Calculator, Google Cloud Pricing Calculator;
giá thay đổi theo region, theo cam kết (Savings Plans, Committed Use Discounts) và egress giữa
region/AZ cũng tính phí (thường 0.01–0.02 USD/GB).
