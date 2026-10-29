# Lời giải: kiểm tra Sample Ratio Mismatch

## Cách làm

Chuẩn hoá tỉ lệ thiết kế, nhân với tổng số đơn vị để có số kỳ vọng mỗi nhánh, tính thống kê
chi-square `Σ (O − E)² / E` và lấy p-value phía phải với `k − 1` bậc tự do. Một nhánh bị mất đơn
vị thì nhánh kia "thừa" tương ứng, nên chỉ có `k − 1` thông tin độc lập.

## Cookie Cats có SRM không?

p ≈ 0.0086. Câu trả lời đúng là: **phụ thuộc vào ngưỡng đã định trước**.

- Ngưỡng ngành 0.001 (Microsoft, Booking dùng mức này hoặc chặt hơn): không báo SRM.
- Ngưỡng 0.01: có SRM, phải điều tra trước khi tin vào kết quả retention.

Vì sao ngành chọn ngưỡng chặt: kiểm tra SRM chạy hằng ngày trên hàng trăm thí nghiệm. Ở ngưỡng
0.05, cứ 20 lần kiểm tra lại có một báo động nhầm (test A/A trong bài cho thấy đúng điều đó), và
team sẽ nhanh chóng phớt lờ cảnh báo. Ngược lại, ngưỡng quá lỏng khiến lỗi phân nhóm thật lọt qua.

Điều không được làm: nhìn p = 0.0086 rồi mới chọn ngưỡng cho phù hợp với kết luận mong muốn.

## Nếu có SRM thì làm gì

1. Không đọc kết quả metric.
2. Chia nhỏ theo ngày, platform, phiên bản app, quốc gia, user mới/cũ để tìm lát cắt lệch.
3. Kiểm tra pipeline: sự kiện phân nhóm được log ở đâu, có filter (bot, user nội bộ) nào áp khác
   nhau giữa hai nhánh không.
4. Sửa và chạy lại. Không cân lại bằng cách loại bớt user ở nhánh đông hơn: việc loại đó không
   ngẫu nhiên.

Với Cookie Cats, ta không có dữ liệu ngày hay platform để điều tra. Trong thực tế bạn sẽ yêu cầu
team phát triển game cung cấp log phân nhóm.
