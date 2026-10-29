---
title: Khoảng dự báo số đơn Olist cho kế hoạch vận hành
level: advanced
services: []
files:
  - path: starter/intervals.py
    note: 5 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Trưởng bộ phận vận hành kho
  - path: tests/test_intervals.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/advanced/02-olist-forecast-intervals -q
---

## Mục tiêu

Biến dự báo điểm thành thứ người lập kế hoạch dùng được: khoảng dự báo có độ phủ (coverage) đúng
như đã hứa, được chấm bằng metric phù hợp, và một quy tắc chọn mức phân vị theo chi phí kinh doanh.

## Đề bài

Chuỗi số đơn Olist mỗi ngày (như bài Intermediate 02), horizon 14 ngày, khoảng 80%.

1. **`intervals.py`**: `backtest_errors`, `empirical_interval` (hai kiểu `additive` và
   `log_ratio`), `coverage`, `interval_score`, `pinball_loss` theo docstring. Interval score của
   khoảng $$[l, u]$$ ở mức $$1 - \alpha$$:

$$
S_\alpha(l, u; y) = (u - l) + \frac{2}{\alpha}(l - y)\,\mathbf 1\{y < l\} + \frac{2}{\alpha}(y - u)\,\mathbf 1\{y > u\}
$$

2. **Hiệu chỉnh và đánh giá tách rời**: sai số backtest để dựng khoảng lấy từ các origin 2017-06-04
   tới 2018-02-18 (mỗi 7 ngày); đánh giá coverage trên 12 origin từ 2018-03-04 (mỗi 14 ngày).
3. **So sánh ít nhất ba cách dựng khoảng**: khoảng lý thuyết của SARIMA (`get_forecast().conf_int`),
   empirical additive, empirical log-ratio; với ít nhất hai model điểm (seasonal naive, SARIMA).
4. **Quyết định**: nếu thiếu một nhân viên tốn gấp 4 lần thừa một nhân viên, nên lập kế hoạch theo
   phân vị nào? Giải thích bằng pinball loss.
5. **`REPORT.md`** theo khung có sẵn.

## Tiêu chí đạt

- `empirical_interval` khớp `np.quantile` từng bước h; `interval_score` và `pinball_loss` đúng công
  thức; pinball loss nhỏ nhất ở đúng phân vị thật; trên chuỗi mô phỏng ổn định, khoảng 80% phủ
  70–90% dữ liệu mới.
- Trên dữ liệu thật với seasonal naive và khoảng additive: coverage 0.685, interval score 214.5.
- `REPORT.md` không còn TODO, ít nhất 300 từ. Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Coverage thấp hơn danh nghĩa không nhất thiết do model tệ: Olist 2018 lớn hơn nhiều so với giai đoạn
hiệu chỉnh, nên sai số **tuyệt đối** cũng lớn hơn. Sai số tương đối (log-ratio) ổn định hơn khi mức
của chuỗi thay đổi.

### Gợi ý 2

Phân vị tối ưu khi thiếu tốn $$c_u$$ và thừa tốn $$c_o$$ là $$c_u / (c_u + c_o)$$ (bài toán
newsvendor). Pinball loss ở phân vị $$q$$ chính là chi phí kỳ vọng với tỉ lệ đó.
