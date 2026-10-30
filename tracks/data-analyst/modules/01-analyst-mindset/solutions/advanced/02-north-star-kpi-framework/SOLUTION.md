# Hướng làm: bộ KPI và scorecard cho Capital Bikeshare

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hàm scorecard, các con số tham chiếu, một bộ KPI mẫu,
các quyết định cần cân nhắc và rubric.

## Hàm `kpi_scorecard`

- Kỳ: `dates = pd.to_datetime(day["dteday"])`, giữ `end - window < dates <= end` (đúng `window` ngày, gồm cả hai đầu).
- Kỳ so sánh: cùng cách với `end - pd.Timedelta(days=364)`.
- Một hàm phụ `_metrics(part)` trả Series năm metric; ghép hai Series thành hai cột, `.loc[METRICS]` để giữ thứ tự,
  `change_pct = current / previous.replace(0, np.nan) - 1`.
- Không dùng cột `yr`, `mnth`: hàm phải đúng với bất kỳ khoảng ngày nào.

## Con số tham chiếu

| 28 ngày kết thúc | Lượt (hiện tại / năm trước) | Lượt thành viên | Tỉ trọng thành viên | Ngày xấu trời |
| --- | --- | --- | --- | --- |
| 30/09/2012 | 206 623 / 113 499 (+82.1%) | +82.5% | 81.2% / 81.0% | 0 / 3 |
| 31/10/2012 | 179 852 / 113 566 (+58.4%) | +63.4% | 81.8% / 79.3% | 1 / 3 |
| 31/12/2012 | 107 639 / 72 991 (+47.5%) | +47.5% | 89.9% / 89.9% | 1 / 2 |

Lượt thành viên theo tuần so với 52 tuần trước (52 tuần của năm 2012): trung vị +66%, độ lệch chuẩn 48 điểm %, thấp nhất
−28%. Tăng trưởng theo tuần rất nhiễu (một tuần mưa đủ đổi dấu), nên ban giám đốc xem scorecard 28 ngày, còn tuần dùng
cho đội vận hành kèm số ngày xấu trời.

## Bộ KPI mẫu (rút gọn)

- **North star**: lượt thuê của thành viên mỗi tuần (28 ngày tới 31/10/2012: 147 120, +63.4% so với cùng kỳ). Thành
  viên trả phí định kỳ, dùng xe cho việc hằng ngày; lượt của họ là giá trị nhận được và dẫn tới gia hạn. Không chọn
  tổng lượt (bị thời tiết, khách du lịch chi phối) hay doanh thu (đến chậm, tăng bằng tăng giá được).
- **Input**: thành viên hoạt động (marketing, gia hạn); lượt mỗi thành viên (mạng lưới trạm, app); tỉ lệ vãng lai chuyển
  thành thành viên (giá gói, marketing); tỉ lệ trạm có xe giờ cao điểm (vận hành).
- **Leading/lagging**: lượt trước 10h dự báo tổng ngày (đã kiểm ở bài Basic 03, sai số trung vị khoảng 9%); lượt mỗi
  thành viên giảm 4 tuần liền dự báo không gia hạn (giả định, cần dữ liệu tài khoản).
- **Guardrails**: tỉ lệ xe hỏng, thời gian trạm trống xe giờ cao điểm, doanh thu mỗi lượt vãng lai.
- **Metric tree**: lượt thành viên = thành viên hoạt động × lượt mỗi thành viên; thành viên hoạt động = mới + giữ lại.
  Thời tiết và mùa là nhánh **bối cảnh**, không ai sở hữu nhưng phải hiện cạnh scorecard.
- **Nhịp**: ngày (leading, vận hành), tuần (north star, so 52 tuần), tháng (scorecard 28 ngày lệch 364 ngày).
- **Game metric**: tách chuyến để tránh phí quá giờ làm tăng lượt giả; gói thành viên rẻ ngắn hạn làm tăng chuyển đổi
  nhưng giảm doanh thu. Dữ liệu thiếu: tài khoản, doanh thu, xe, trạm.

Một lựa chọn khác chấp nhận được: north star là "số thành viên có ít nhất 2 lượt mỗi tuần" (đo người dùng thường xuyên
thay vì lượt), nếu giải thích được và nêu là cần dữ liệu tài khoản.

## Các quyết định cần cân nhắc

- **Giá trị cho khách, không phải số lớn nhất**: tổng lượt lớn hơn nhưng lẫn khách vãng lai nhạy thời tiết.
- **Hành động được**: mỗi input một team; thời tiết không phải input mà là bối cảnh.
- **So sánh công bằng**: lệch 364 ngày cùng thứ trong tuần; kèm số ngày xấu trời để tách công ty với trời.
- **Dữ liệu có và không có**: bộ UCI chỉ có tổng lượt mỗi ngày/giờ. Bộ KPI tốt ghi rõ metric nào tính được ngay, metric
  nào cần nguồn mới; không giả vờ đo được số thành viên.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| North star | 20 | Một metric, định nghĩa chính xác, giải thích giá trị cho khách và liên hệ doanh thu dài hạn, lý do loại phương án khác, có con số hiện tại và so cùng kỳ |
| Input metrics | 15 | 3–5 metric, mỗi cái một team điều khiển được, nối với north star |
| Leading và lagging | 15 | Ghép cặp; phân biệt leading đã kiểm (có số) với leading còn là giả định |
| Guardrails | 15 | Ít nhất 2, chặn được cách game cụ thể, có ngưỡng |
| Metric tree | 10 | Sơ đồ đúng phép cộng/nhân, tách nhánh bối cảnh (thời tiết, mùa) |
| Scorecard và nhịp xem | 15 | Hàm đúng, giải thích vì sao lệch 364 ngày, nhịp và chủ sở hữu rõ |
| Dữ liệu thiếu và rủi ro | 10 | Nêu cụ thể nguồn cần thêm và cách mỗi KPI bị game |

Từ 70 điểm trở lên là bộ KPI đủ trình ban giám đốc.

## Sai lầm hay gặp

- Chọn doanh thu hoặc tổng lượt làm north star mà không giải thích vì sao nó thể hiện giá trị cho khách.
- Liệt kê 10 input metric, không cái nào có chủ sở hữu.
- Đưa nhiệt độ hay thời tiết vào danh sách KPI như thể có team điều khiển được.
- So tháng này với tháng trước thay vì cùng kỳ năm trước: mùa vụ của xe đạp lớn hơn mọi thay đổi của công ty.
- Viết leading indicator chưa từng kiểm khả năng dự báo như thể đã chắc chắn.
