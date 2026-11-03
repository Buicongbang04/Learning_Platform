---
title: "Sự cố: dashboard báo drift mạnh từ hôm qua"
level: intermediate
services: []
files:
  - path: starter/monitor_pipeline.py
    note: 4 hàm TODO, PSI và báo cáo drift đã có sẵn
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/intermediate/04-incident-alert-drift-overnight -q
---

## Mục tiêu

Xử lý một cảnh báo drift như một sự cố thật: tái hiện triệu chứng, tìm xem nó bắt đầu từ lúc nào và ở cột nào, quyết định xem nó có thật không, sửa tận gốc ở đường dữ liệu và thêm rào để lần sau máy báo đúng chỗ.

## Đề bài

Sáng nay on-call nhận cảnh báo: **dashboard báo drift mạnh từ hôm qua** trên model ETA. Không ai báo có deploy hay thay đổi nào. MAE trên nhãn đã về của những ngày trước đó vẫn bình thường, và hai đội
(data, serving) đều nói họ không đổi gì.

Bạn có bảng log feature 21 ngày, mỗi dòng một chuyến, cột `day`, `trip_distance`, `fare_amount`, `trip_time` (xem cách test dựng bảng trong `tests/test_incident.py`). 20 ngày đầu là bình thường, ngày cuối cùng
là ngày dashboard bắt đầu đỏ. Trong `starter/monitor_pipeline.py`, `psi`, `drift_scores` và `drifted_columns` đã chạy được (PSI chia quantile, ngưỡng cảnh báo 0.25). Điền 4 hàm:

- `change_point_day(df, column)`: tính trung vị của `column` theo từng `day`; trả `day` đầu tiên mà trung vị khác trung vị ngày liền trước hơn 2 lần (tỉ số giữa số lớn và số nhỏ lớn hơn 2); `None` nếu không có ngày nào.
- `median_ratio(df, column, day)`: trung vị của `column` ở các dòng có `day` nhỏ hơn mốc, chia trung vị ở các dòng từ mốc trở đi, làm tròn về số nguyên gần nhất; trả `float`.
- `adjust_from(df, column, day, factor)`: trả bản sao (không sửa đầu vào) trong đó `column` được nhân với `factor` ở các dòng từ `day` trở đi, mọi cột khác và số dòng giữ nguyên.
- `range_guard(df, column, low, high, max_outside=0.05)`: `True` nếu tỉ lệ dòng có `column` nằm ngoài `[low, high]` không vượt `max_outside` (so sánh `<=`), ngược lại `False`. Đây là rào đặt ở cửa vào của pipeline monitoring để lô bất thường bị chặn
  trước khi tới dashboard.

Việc cần làm theo đúng quy trình sự cố: chạy test đầu tiên (nó chứng minh triệu chứng có thật trên bảng thô), tự tìm cột nào, từ ngày nào, lệch bao nhiêu lần, rồi điền hàm. Test cuối kiểm bảng đã `adjust_from`
không còn cột nào bị cảnh báo và giá trị khớp từng dòng với dữ liệu gốc.
Ghi lại bạn nghĩ nguyên nhân là gì và vì sao nó không phải "model hỏng"; `SOLUTION.md` có đáp án để đối chiếu.

## Tiêu chí đạt

- Triệu chứng được tái hiện: trên bảng thô, `drifted_columns` chỉ trả đúng một cột.
- `change_point_day` trả đúng ngày bắt đầu với cột lệch và `None` với hai cột còn lại.
- `median_ratio` trả số nguyên (dạng float); `adjust_from` khôi phục từng giá trị mà không đổi cột khác và không đổi đầu vào.
- Sau `adjust_from` không cột nào có PSI từ 0.1 trở lên và `drifted_columns` rỗng.
- `range_guard` cho qua dữ liệu bình thường, chặn lô hôm qua, cho qua lô đã sửa; ngưỡng so sánh `<=`.

## Gợi ý

### Gợi ý 1

`df.groupby("day")[column].median()` rồi `shift(1)` để so với ngày liền trước; `np.maximum(a, b) / np.minimum(a, b)` cho tỉ số không phụ thuộc chiều thay đổi.

### Gợi ý 2

Hỏi: thế giới thật có thể đổi như vậy chỉ trong một đêm không, và nếu có thì những cột liên quan (cự ly, giá cước) có phải đổi theo không? Nếu không, thứ đã đổi nằm ở chỗ khác.
