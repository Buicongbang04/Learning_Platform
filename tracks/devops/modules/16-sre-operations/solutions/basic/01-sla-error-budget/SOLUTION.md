# Lời giải: SLO, SLA và error budget

## Cách làm

- `load` dùng `csv.DictReader`, so `reader.fieldnames` với `FIELDS` trước khi đọc, rồi kiểm từng dòng: số lỗi cộng số chậm không thể
  âm hay vượt số request. Dữ liệu sai thì dừng sớm, đừng để một dòng hỏng làm lệch cả tháng.
- `sli` và `budget_report` tính trên **request**: một giờ đông khách nặng ký hơn một giờ vắng. `allowed_bad` là số request xấu được
  phép trong cả tháng; `exhausted_at` cộng dồn từ đầu tháng và dừng ở dòng đầu tiên vượt (lớn hơn, không phải lớn hơn hoặc bằng).
- `burn_rates` lấy `w` dòng kết thúc ở `end_hour`. Burn rate 1 nghĩa là tiêu đúng nhịp để hết budget vào cuối cửa sổ SLO; 14,4 trên
  cửa sổ 1 giờ nghĩa là cứ đà này thì budget 30 ngày hết trong khoảng 2 ngày.
- `sla_availability` đếm **giờ**, chỉ nhìn 5xx, và bỏ giờ bảo trì khỏi cả tử lẫn mẫu: đó là điều khoản hợp đồng, không phải trải
  nghiệm của khách.
- `sla_credit` duyệt bảng từ mức cao xuống, nhân `availability` với 100 trước khi so.

## Số liệu tháng 10

| Đại lượng | Giá trị |
| --- | --- |
| SLI (request tốt) | 99,624% |
| Budget cho phép | khoảng 12.161 request xấu, đã có 15.256, tức tiêu 125% |
| Budget cạn lúc | 2026-10-24T02:00:00Z |
| Burn rate lúc 12:00 ngày 28/10 | 7,73 (1h), 4,71 (6h), 2,29 (24h), 1,27 (72h) |
| Burn rate lúc 04:00 ngày 23/10 | 41,4 (1h), 26,3 (6h) |
| SLA | 3 giờ sập trên 743 giờ tính, 99,596%, credit 10% |

## Vì sao SLO cạn mà SLA vẫn ổn

- SLA chỉ đếm giờ có trên 5% lỗi: hai giờ sự cố deploy ngày 7/10 và một giờ ngày 28/10. Giờ ngày 14/10 có 3,1% lỗi không đủ ngưỡng.
- Giờ bảo trì 19:00 ngày 19/10 trả 5xx cho mọi request. Khách vẫn bị ảnh hưởng nên SLO tính, còn hợp đồng loại ra.
- Sự cố latency đêm 23/10 (12% request chậm) không có 5xx nên SLA không thấy, nhưng nó đẩy SLO qua mép. Cộng với lỗi nền khoảng 0,06% và
  chậm nền khoảng 0,18% mỗi giờ, đủ để budget cạn ngày 24/10.
- Bài học: SLA là cam kết pháp lý, lỏng hơn và đo thứ dễ chứng minh. SLO là công cụ nội bộ, chặt hơn SLA để còn thời gian phản ứng
  trước khi phải trả tiền. Đo latency trong SLO là thứ SLA hay bỏ sót.

## Sai lầm hay gặp

- Tính SLO trung bình theo giờ thay vì theo request: giờ 3 giờ sáng ít khách bị đếm nặng như giờ cao điểm.
- So `availability >= 99.9` khi `availability` là tỉ lệ 0,999: mọi tháng đều thành 100% credit.
- Quên `slow` trong SLO, hay đếm `slow` vào SLA.
- `exhausted_at` dùng `>=`: tiêu vừa đủ budget chưa phải là vượt.
