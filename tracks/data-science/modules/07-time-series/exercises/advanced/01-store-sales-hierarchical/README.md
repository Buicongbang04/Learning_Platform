---
title: Dự báo phân cấp và reconciliation cho chuỗi Rossmann
level: advanced
services: []
files:
  - path: starter/reconcile.py
    note: 5 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Báo cáo cho Giám đốc vận hành
  - path: tests/test_reconcile.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run pytest tracks/data-science/modules/07-time-series/exercises/advanced/01-store-sales-hierarchical -q
---

## Mục tiêu

Dự báo doanh thu 6 tuần ở ba cấp (toàn chuỗi, loại cửa hàng, từng cửa hàng) sao cho các con số
**cộng khớp nhau**, chọn cách reconcile bằng backtest, và giải thích cho lãnh đạo vì sao cách đó
đúng với dữ liệu này.

## Đề bài

Hệ phân cấp: Total → 4 `StoreType` (a, b, c, d) → 20 cửa hàng (5 cửa hàng id nhỏ nhất mỗi loại,
trong số cửa hàng đủ mọi ngày), doanh thu theo tuần.

1. **`reconcile.py`**: `build_hierarchy`, `summing_matrix`, `aggregate`, `is_coherent`,
   `reconcile` với bốn phương pháp `bottom_up`, `ols`, `wls_struct`, `wls_var` (định nghĩa trong
   docstring). Công thức chung của nhóm reconciliation tuyến tính:

$$
\tilde{\mathbf y}_h = \mathbf S\,(\mathbf S^\top \mathbf W^{-1} \mathbf S)^{-1}\,\mathbf S^\top \mathbf W^{-1}\,\hat{\mathbf y}_h
$$

2. **Base forecast**: tự chọn model cho từng node (ít nhất hai cấu hình, ví dụ: cùng một model cho
   mọi node; model khác nhau cho cấp trên và cấp cửa hàng). Gợi ý thử Holt damped, seasonal naive
   52 tuần, ETS, hoặc LightGBM của bài Intermediate 03 cộng theo tuần.
3. **Backtest**: horizon 6 tuần, ít nhất hai origin. Bảng MAE theo cấp cho base và mỗi phương pháp
   reconcile.
4. **Phân tích**: khi nào reconcile giúp, khi nào không đổi gì, khi nào làm tệ đi; vì sao.
5. **`REPORT.md`** theo khung có sẵn.

## Tiêu chí đạt

- Ma trận `S` đúng thứ tự node; mọi phương pháp cho kết quả coherent; dự báo đã coherent thì không
  đổi qua `ols`/`wls`; công thức `ols`, `wls_struct`, `wls_var` khớp tới 1e-9; `ols` không bao
  giờ làm tăng tổng bình phương sai số trên 10 bộ mô phỏng.
- Trên dữ liệu thật: 133 tuần × 20 cửa hàng, tổng doanh thu Total 131 986 711.
- `REPORT.md` không còn TODO, ít nhất 300 từ. Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Hai cửa hàng trong tập có tuần doanh thu bằng 0 (đóng cửa cả tuần). Model nhân tính hoặc log sẽ
gặp `log(0)`; quyết định xử lý trước khi chạy hàng loạt.

### Gợi ý 2

Nếu mọi node dùng một model **tuyến tính theo dữ liệu** với cùng tham số (seasonal naive, trung bình
k tuần), base forecast đã coherent sẵn và reconcile không đổi gì. Reconcile có giá trị khi các node
có thông tin khác nhau: model khác nhau, feature khác nhau, độ nhiễu khác nhau.
