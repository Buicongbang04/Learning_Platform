# Lời giải: Báo cáo khoảng cách gửi IT bệnh viện

## Hướng làm

1. **Phân loại trước khi viết.** Từ dữ liệu đề cho:

   | Phát hiện | Loại | Vì sao |
   | --- | --- | --- |
   | Đĩa: 6,0 GiB trống ở `/var/lib/docker` (nằm trên `/`), cần ≥10 GiB | Chặn, IT làm, thay đổi hệ thống | Cài sẽ dừng giữa chừng khi nạp image + model |
   | Cổng 18080 có tiến trình nghe, user thường không thấy là gì | Chặn cho tới khi IT xác nhận | Có thể là dịch vụ của viện; không tự `kill`, không tự đổi cổng mà không hỏi |
   | HTTPS qua proxy lỗi chứng chỉ (TLS inspection, CA chưa trust) | Không chặn ngày cài | Bundle offline mang đủ image, model, plugin compose; CA chỉ cần cho cập nhật về sau |
   | Thiếu plugin `docker compose` | Việc của FDE | Bundle mang binary compose v2 (module 02) |
   | Đồng hồ chưa đồng bộ | Cần xác nhận | Log và chứng chỉ lệch giờ gây lỗi khó đoán; hỏi NTP nội bộ |
   | CPU 4, RAM 15 992 MiB, Ubuntu 20.04, Docker 26.1.3 | Đạt | Ghi một dòng để IT khỏi hỏi lại |

2. **Xếp lịch ngược từ cửa sổ 12/11.** Cửa sổ duy nhất trước đó là ngày mai 05/11, nhiều khả năng IT không kịp xin
   change. Nên báo cáo đưa hai đường: nới đĩa trong cửa sổ 05/11 nếu kịp; không thì dùng 30 phút đầu cửa sổ 12/11 cho việc
   nới đĩa, có **điểm quyết định lúc 20:30**: chưa đạt thì dời cài sang 19/11 thay vì cài vội trong 90 phút còn lại.
3. **Viết cho người đọc.** Anh Tuấn cần biết việc của anh; chị Hà cần biết không có gì phải giải trình với An toàn
   thông tin. Không có tên script nội bộ, không thuật ngữ preflight.

## Rubric (tự chấm, đạt đủ 10 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| R1 | Đoạn "Kết luận": 3 câu, nói rõ chưa cài được, hai việc chặn, mốc 09/11, cửa sổ 05/11 hoặc 20:30 ngày 12/11 |
| R2 | Bảng "Tóm tắt" đủ 6 cột |
| R3 | Đĩa và cổng: số đo, nguồn, yêu cầu, người làm, hạn đúng lịch cửa sổ |
| R4 | Hai phương án đĩa (nới đĩa ảo, hoặc volume riêng cho dữ liệu Docker), không đề nghị dọn dữ liệu |
| R5 | Cổng: nói rõ không thấy tiến trình, lệnh `sudo ss -tlnp 'sport = :18080'`, phương án đổi cổng do IT chọn |
| R6 | "Proxy và chứng chỉ": không chặn ngày cài; IT cấp tệp CA, FDE cấu hình |
| R7 | Không có đề nghị nới bảo mật nào; câu cuối mục proxy nói rõ điều đó |
| R8 | "Việc phía chúng tôi" |
| R9 | "Cần xác nhận": NTP, tiến trình trên 18080, người trực |
| R10 | Không tên tệp/hàm nội bộ, "Chặn" được định nghĩa, 50 dòng |

## Bài mẫu

```markdown
# Báo cáo khoảng cách: cài quillo trên srv-ai01

Gửi: anh Tuấn (IT hạ tầng). Đồng gửi: chị Hà (An toàn thông tin). Ngày 04/11/2026.

## Kết luận

srv-ai01 hiện **chưa** cài được quillo vì hai việc: thư mục dữ liệu của Docker chỉ còn 6,0 GiB trống (cần ít nhất 10 GiB)
và cổng 18080 đang có một tiến trình khác nghe. Để giữ cửa sổ thứ Năm 12/11, nhờ anh Tuấn xác nhận cổng trước thứ Hai
09/11 và nới đĩa trong cửa sổ 05/11, hoặc trong 30 phút đầu cửa sổ 12/11 (20:00–20:30). Nếu đến 20:30 ngày 12/11 đĩa chưa
đạt, chúng tôi đề nghị dời việc cài sang cửa sổ 19/11 thay vì cài vội.

## Tóm tắt

"Chặn" là việc phải xong trước khi bắt đầu cài; các mục còn lại không ảnh hưởng ngày 12/11.

| Hạng mục | Hiện trạng (đo ngày 04/11) | Yêu cầu | Mức | Ai làm | Hạn |
| --- | --- | --- | --- | --- | --- |
| Đĩa cho dữ liệu Docker | 6,0 GiB trống tại `/var/lib/docker` (nằm trên phân vùng `/`) | Ít nhất 10 GiB trống | Chặn | IT | Cửa sổ 05/11, muộn nhất 20:30 ngày 12/11 |
| Cổng 18080 | Đang có tiến trình nghe, tài khoản cài đặt không xem được là gì | Cổng trống, hoặc chọn cổng khác | Chặn | IT xác nhận | Thứ Hai 09/11 |
| Chứng chỉ của proxy | HTTPS qua proxy 10.20.0.5:3128 báo lỗi chứng chỉ | Tệp CA nội bộ | Không chặn | An toàn thông tin | Thứ Ba 10/11 |
| Đồng hồ hệ thống | Chưa đồng bộ thời gian | Có máy chủ NTP | Cần xác nhận | IT | Thứ Ba 10/11 |
| CPU, RAM, hệ điều hành, Docker | 4 CPU, 15,6 GiB, Ubuntu 20.04, Docker 26.1.3 | 2 CPU, 4 GiB, Ubuntu 20.04, Docker 20.10 trở lên | Đạt | — | — |

## Việc cần bệnh viện hỗ trợ

**Đĩa** (anh Tuấn chọn một):
1. Nới đĩa ảo của srv-ai01 từ 8 GB lên 20 GB và nới phân vùng `/`. Tối thiểu cần thêm 4 GiB; 20 GB để còn chỗ cho bản
   nâng cấp sau (hai phiên bản cùng nằm trên đĩa trong lúc chuyển).
2. Gắn một ổ riêng 20 GB, mount ví dụ tại `/data`. Trong cửa sổ cài, chúng tôi chuyển thư mục dữ liệu Docker sang
   `/data/docker` (một dòng cấu hình, có bước hoàn tác).

**Cổng 18080**: tài khoản cài đặt không có quyền xem tiến trình của tài khoản khác. Nhờ anh chạy
`sudo ss -tlnp 'sport = :18080'` và cho biết đó là dịch vụ gì. Nếu cần giữ dịch vụ đó, quillo chạy được ở cổng khác
(ví dụ 18081); anh chọn cổng, chúng tôi đổi cấu hình.

**Proxy và chứng chỉ**: bản cài mang theo đủ image và model, nên ngày 12/11 không cần ra internet. Để cập nhật về sau qua
proxy, nhờ chị Hà gửi tệp CA nội bộ (định dạng PEM) và xác nhận các địa chỉ được phép đi qua proxy; chúng tôi tự cấu hình
Docker dùng proxy và CA đó. Chúng tôi không đề nghị bỏ kiểm tra HTTPS hay tắt kiểm soát nào của bệnh viện.

## Việc phía chúng tôi

- Mang theo công cụ `docker compose` trong bản cài (máy chưa có; không cần IT cài thêm gói nào).
- Docker 26.1.3 đã đạt yêu cầu, không cần nâng cấp.
- Kiểm tra lại toàn bộ máy vào 20:00 ngày 12/11 trước khi cài, gửi kết quả cho anh Tuấn.

## Cần xác nhận

- Máy chủ NTP nội bộ nào srv-ai01 nên dùng (đồng hồ lệch làm log và chứng chỉ sai giờ).
- Dịch vụ đang dùng cổng 18080 là gì, có cần giữ không.
- Ai trực IT trong cửa sổ 12/11 nếu cần nới đĩa hoặc mở cổng gấp.
```

## Lỗi hay gặp

- Mở đầu bằng bảng 13 trường survey: IT phải tự rút ra kết luận.
- Xếp proxy/CA thành việc chặn: đúng với cài qua mạng, sai với sản phẩm giao bằng bundle offline; làm IT và An toàn
  thông tin tốn công không cần.
- "Xin dọn bớt log/ảnh Docker cũ cho đủ chỗ": đụng dữ liệu của khách, và 6 GiB vẫn không đủ cho bản nâng cấp.
- Hẹn "trước ngày cài" mà không gắn với cửa sổ: IT không thể nới đĩa ngoài cửa sổ thứ Năm.
- "Anh kill giúp tiến trình trên 18080": chưa biết nó là gì.
