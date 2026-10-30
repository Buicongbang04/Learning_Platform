# Lời giải: chẩn đoán lượt thuê tháng 10/2012 theo cây giả thuyết

## Cách làm

1. **`month_summary`**: tháng từ `dteday` (không dùng `yr`/`mnth` để hàm đúng với mọi bộ ngày); tạo hai cột cờ
   `clear = weathersit == 1`, `bad = weathersit >= 3`, nhóm theo tháng với `sum` và `size`, rồi
   `per_day = rides / days`.
2. **`segment_contribution`**: lấy hai dòng của `month_summary`, cột `casual`, `registered`; `change`, `pct`,
   `share_of_change = change / change.sum()`.
3. **`same_weather_change`**: hai `groupby("weathersit")["cnt"].mean()`, giữ index chung, chia rồi trừ 1. Loại
   thời tiết chỉ có ở một tháng bị bỏ: không có gì để so trong cùng điều kiện.

## Kiểm từng nhánh

| Nhánh | Con số | Kết luận |
| --- | --- | --- |
| Lịch | Tổng −9.0%, nhưng **mỗi ngày −12.0%** (tháng 10 có 31 ngày, tháng 9 có 30) | Không giải thích; số ngày còn làm mức giảm thật lớn hơn |
| Mùa vụ | Năm 2011 cùng chuyển tháng: mỗi ngày **−6.2%** | Giải thích khoảng một nửa |
| Thời tiết | Ngày quang 22 → 14, ngày mây 8 → 15, ngày xấu 0 → 2 (bão Sandy 29/10, 22 lượt; 30/10, 1 096 lượt). Trong cùng loại thời tiết: quang **−2.6%**, mây −4.2% | Giải thích phần lớn phần còn lại |
| Phân khúc | `casual` −21.1% (46.8% mức giảm, dù chỉ 20% lượt); `registered` −6.0% | Vãng lai giảm mạnh hơn, đúng kiểu nhạy thời tiết |

Hai cách kiểm chéo cho cùng câu chuyện:

- **Giữ cơ cấu thời tiết của tháng 9** (73% quang, 27% mây) với lượt trung bình từng loại thời tiết của tháng 10:
  7 069 lượt/ngày so với 7 286, **−3.0%**. Phần còn lại của mức −12% là do tháng 10 xấu trời hơn.
- **Bỏ hai ngày bão**: tháng 10 còn 6 818 lượt/ngày, **−6.4%** so với tháng 9, gần đúng bằng mức mùa vụ năm trước
  (−6.2%).

Lưu ý: hai cách tách mùa vụ và thời tiết không cộng lại gọn gàng (mùa vụ năm 2011 cũng lẫn thời tiết của năm đó);
đủ để quyết định thì không cần tách chính xác hơn.

## Câu trả lời cho giám đốc

"**Không có dấu hiệu khách bỏ dịch vụ.** Lượt thuê mỗi ngày tháng 10 thấp hơn tháng 9 khoảng 12%, trong đó khoảng
một nửa là mùa vụ (năm ngoái cùng kỳ giảm 6%) và phần lớn phần còn lại là thời tiết: tháng 10 có 14 ngày quang so
với 22, và bão Sandy làm mất gần hết lượt của hai ngày 29–30/10. So những ngày cùng thời tiết, tháng 10 chỉ thấp
hơn 3–4%. Giới hạn: dữ liệu ngày không cho biết số thành viên đang hoạt động; muốn chắc về churn cần dữ liệu theo
tài khoản."

Thứ tự kết luận → bằng chứng → giới hạn, con số nào cũng có tham chiếu.

## Con số tham chiếu

| Đại lượng | Giá trị |
| --- | --- |
| Tháng 9 / 10 năm 2012 | 218 573 / 198 841 lượt; 7 285.8 / 6 414.2 lượt mỗi ngày |
| Năm 2011 cùng chuyển tháng | tổng −3.1%, mỗi ngày −6.2% |
| `casual` / `registered` | −9 240 (−21.1%) / −10 492 (−6.0%) |
| Cùng thời tiết 2012 | quang −2.6%, mây −4.2% |
| Cùng thời tiết 2011 | quang −5.3%, mây −16.7%, xấu −16.5% |
| Tháng 10/2012 với cơ cấu thời tiết tháng 9 | 7 069 lượt/ngày, −3.0% |
| Tháng 10/2012 bỏ 29–30/10 | 6 818 lượt/ngày, −6.4% |

## Đáp án trắc nghiệm

- `check-first` (c): nhánh lịch/dữ liệu rẻ nhất (đếm ngày) và hay là thủ phạm (kỳ chưa đủ, khác số ngày, pipeline
  lỗi). Kiểm phân khúc trước (a) là nhảy vào câu trả lời giám đốc gợi ý.
- `per-day-change` (c) **−12%**. −9% (b) là tổng tháng, chưa tính tháng 10 dài hơn.
- `last-year` (a) **−6%** (−6.2%). −12% (d) là năm 2012.
- `clear-day-change` (b) **khoảng 3%** (−2.6%).
- `casual-share` (d) **khoảng 47%**: gấp hơn hai lần tỉ trọng của nhóm, vì khách vãng lai đi chơi nên nhạy thời
  tiết và mùa hơn thành viên đi làm.
- `mix-adjusted` (a) **khoảng 3%**.
- `conclusion` (c): mùa vụ và thời tiết giải thích phần lớn. (d) sai vì tháng dài hơn làm tổng **cao** hơn, không
  thấp hơn; (b) bỏ qua bằng chứng đã có, chờ thêm một tháng thì quá họp ban điều hành.
- `limitation` (b): dữ liệu ngày là tổng lượt, không có mã khách, nên không đo được số thành viên hoạt động. Ba
  phương án còn lại là thứ dữ liệu đã chứng minh.
