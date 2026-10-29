---
title: Soi chart gây hiểu nhầm - linter cho matplotlib và bốn chart thật
level: intermediate
services: []
files:
  - path: starter/chart_audit.ipynb
    note: 2 hàm TODO + soi 4 chart
  - path: tests/test_chart_audit.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/01-misleading-chart-audit/starter/chart_audit.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/01-misleading-chart-audit -q
---

## Mục tiêu

Nhận ra năm lỗi trình bày hay gặp (trục bar bị cắt, dual axis, pie quá nhiều lát, bar danh mục không
sắp, trục thiếu nhãn) bằng cách viết luật kiểm tự động trên `Figure` của matplotlib, rồi dùng nó để duyệt
bốn chart vẽ từ dữ liệu thật và biết khi nào cảnh báo của linter nên bỏ qua.

## Đề bài

Dữ liệu: Olist thật (`olist_order_payments_dataset.csv`, `olist_order_reviews_dataset.csv`,
`olist_customers_dataset.csv`, `olist_orders_dataset.csv` trong `data/raw/`, tải bằng
`data/download_olist.py`, cần Kaggle token) và Bike Sharing `day.csv` (cell đầu tự tải). Mở
`starter/chart_audit.ipynb`, làm lần lượt:

1. `audit_chart(fig) -> set[str]`: trả tập mã lỗi trong `ISSUES`:
   - `truncated_bar_axis`: Axes có bar mà trục giá trị (y với bar đứng, x với `barh`) bắt đầu trên 0;
   - `dual_axis`: hai Axes có cùng khung `get_position().bounds` (kết quả `twinx()`/`twiny()`);
   - `pie_too_many_slices`: pie hơn 6 lát (`Wedge`);
   - `unsorted_bars`: một nhóm từ 3 bar trên trục danh mục (nhãn chữ, gồm cả `Series.plot.bar()` của
     pandas; trục số và trục ngày không tính) mà chiều cao không đơn điệu theo vị trí;
   - `missing_axis_label`: trục đang hiện và có vạch chia nhưng nhãn rỗng; Axes vẽ pie được miễn.
2. `honest_bar(ax, s) -> Axes`: bar đứng sắp giảm dần, trục y từ 0, nhãn trục x là `s.index.name`,
   nhãn trục y là `s.name` (thiếu tên thì `ValueError`); `audit_chart` trên figure của nó phải rỗng.
3. Chạy bốn cell vẽ chart "xấu" (điểm review theo phương thức thanh toán, khách vãng lai và nhiệt độ hai
   trục, pie doanh thu 27 bang, số giao dịch theo phương thức thanh toán). **Tự ghi lỗi bạn thấy trước**,
   rồi so với kết quả `audit_chart`.
4. Vẽ lại bằng `honest_bar` và hai panel chung trục x; đọc lại headline của từng chart gốc còn đứng vững
   không. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên figure nhỏ dựng trong test pass: mỗi mã lỗi được báo đúng khi có và chỉ khi có; line chart
  không từ 0, pie 2-6 lát, bar trên trục số hoặc trục ngày, hai panel cạnh nhau không bị báo nhầm.
- `honest_bar` trả đúng `ax`, sắp giảm dần, y từ 0, nhãn trục đúng, không sửa Series đầu vào.
- Trên dữ liệu thật: mỗi chart trong bốn chart "xấu" bị báo đúng lỗi của nó (chart 4 có hai lỗi), bản vẽ
  lại sạch.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

Duyệt `for ax in fig.axes`, rồi `for c in ax.containers` và giữ những `c` là `BarContainer`.
`c.orientation` cho biết trục giá trị là y hay x; `min(ax.get_ylim())` an toàn cả khi trục bị đảo. Hai
Axes twin: so `tuple(np.round(ax.get_position().bounds, 6))` giữa các Axes.

### Gợi ý 2

Trục danh mục: `axis.get_converter()` là `StrCategoryConverter` khi gọi `ax.bar(["a", "b"], ...)`;
converter khác (ngày) thì không phải danh mục; không có converter (pandas) thì xem
`axis.get_ticklabels()` có nhãn nào không đọc được thành số. "Đã sắp": sắp các `Rectangle` theo
`get_x()` (hoặc `get_y()` với `barh`), lấy chiều cao, `np.diff` toàn `<= 0` hoặc toàn `>= 0`.
