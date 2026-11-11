# Hướng dẫn chấm: kiến trúc cloud cho Olist Shop với 300 USD

Không có đáp án duy nhất. `ARCHITECTURE.md` cạnh tệp này là một lời giải qua test (AWS sa-east-1, ECS Fargate, RDS, Lambda cho event);
GCP southamerica-east1 với Cloud Run và Cloud SQL cũng đạt nếu lập luận tốt.

## Hướng làm

1. **Loại theo ràng buộc cứng trước, so giá sau.** Độ trễ São Paulo và LGPD loại các nhà cung cấp không có region ở Brazil (Hetzner,
   DigitalOcean, Contabo, Heroku). Còn AWS `sa-east-1`, GCP `southamerica-east1`, Azure Brazil South. Phương án bị loại vẫn nên có trong bảng
   để người đọc thấy đã cân nhắc (Hetzner rẻ nhất nhưng thêm khoảng 200 ms và dữ liệu ra khỏi Brazil).
2. **Chọn kiểu tính toán theo hình dạng tải.** Tải đều cả ngày: container (Fargate, Cloud Run có min instance) rẻ hơn Lambda luôn chạy.
   Event payment theo đợt: Lambda và SQS hợp. Job 40 phút: container task, không Lambda (giới hạn 15 phút).
3. **Liệt kê thứ chạy cả ngày**: database, load balancer, NAT, IPv4 public, log. Region São Paulo đắt hơn khoảng 30 đến 50% so với us-east-1.
4. **Đặt RPO/RTO vào lựa chọn database**: PITR và backup tự động đủ cho RPO 1 giờ; RTO 4 giờ cho phép single-AZ cộng restore; Multi-AZ
   đắt gấp đôi.
5. **Viết đường lui cụ thể**: thứ gì là chuẩn mở (container, Postgres, S3 API), thứ gì khoá chặt (IAM, hàng đợi, event bus), chuyển mất bao lâu.

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Ràng buộc dẫn tới quyết định | 2 | Độ trễ, LGPD, người vận hành, RPO/RTO được dùng để loại hay chọn phương án, không chỉ liệt kê |
| So sánh công bằng | 1 | ≥3 nhà cung cấp, mỗi phương án có chi phí, gánh vận hành, rủi ro chính; không dựng phương án rơm |
| Kiểu tính toán hợp tải | 2 | Lý giải container/serverless/VM theo hình dạng tải; job dài không đặt vào Lambda; event dùng hàng đợi có DLQ |
| Chi phí đúng và đủ | 2 | Có database, load balancer, mạng (NAT hay IPv4 public), egress, log, staging; số khớp; còn dư cho đỉnh mùa |
| Shared responsibility | 1 | Phân rõ phần nhà cung cấp và phần team cho đúng dịch vụ đã chọn (managed DB khác VM tự cài) |
| Lock-in, đường lui, khi nào xem lại | 2 | Nêu cụ thể phần khoá chặt, cách rút và thời gian; điều kiện xem lại đo được (chi phí, lưu lượng, RTO mới) |

## Lỗi hay gặp

- Chọn Kubernetes được quản lý (EKS, GKE) cho team 3 người: control plane cộng node vượt ngân sách và thêm gánh vận hành.
- Chọn us-east-1 vì rẻ, quên độ trễ khoảng 120 ms tới São Paulo và LGPD.
- Quên NAT gateway (khoảng 33 USD/tháng ở us-east-1, đắt hơn ở São Paulo) hay IPv4 public (từ 2024 tính tiền).
- Đưa job 40 phút vào Lambda; đưa API tải đều vào Lambda có provisioned concurrency 24/7.
- Bảng chi phí không có egress; tổng ghi một số, cộng các dòng ra số khác.
