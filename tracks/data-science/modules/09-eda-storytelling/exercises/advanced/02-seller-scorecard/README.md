---
title: Funnel plot seller và đặc tả dashboard chất lượng giao hàng
level: advanced
services: []
files:
  - path: starter/scorecard.py
    note: 2 hàm TODO
  - path: starter/DASHBOARD.md
    note: Đặc tả dashboard
  - path: tests/test_scorecard.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/advanced/02-seller-scorecard -q
---

## Mục tiêu

Thay bảng xếp hạng "10 seller giao trễ tệ nhất" (luôn đầy seller 1–2 đơn) bằng **funnel plot**, rồi
viết đặc tả một dashboard vận hành đúng nghĩa: ít KPI, định nghĩa chặt, quy tắc cảnh báo có căn cứ,
xử lý kỳ chưa chín và lỗi dữ liệu.

## Đề bài

PM vận hành muốn mỗi tuần nhận danh sách seller cần can thiệp vì giao trễ.

1. `seller_funnel(table, unit="seller_id", target="late", z=3.0)` trong `starter/scorecard.py`: một
   dòng mỗi seller với `n, events, rate, expected, lower, upper, excess, flag`. Giới hạn kiểm soát
   theo **xấp xỉ normal** quanh tỉ lệ chung $$p$$:

   $$
   p \pm z\sqrt{\frac{p(1-p)}{n}}
   $$

   cắt vào [0, 1]; `excess` là số sự kiện vượt kỳ vọng $$\text{events} - p\,n$$; `flag` là `above`,
   `below` hoặc `within`.
2. `alerts(funnel, min_n=20)`: seller `above` có ít nhất `min_n` đơn, sắp theo `excess` giảm dần.
3. Chạy trên Olist thật: đơn giao xong mua tới 2018-08-31, seller của item đầu tiên mỗi đơn, `late`
   theo định nghĩa chung. Vẽ funnel plot (trục x là n, thang log; trục y là tỉ lệ trễ; hai đường giới
   hạn). So với bảng xếp hạng theo tỉ lệ.
4. Viết `starter/DASHBOARD.md` theo khung có sẵn (ít nhất 350 từ).

## Tiêu chí đạt

- `seller_funnel` đúng cột, đúng số đếm, giới hạn đúng công thức (cắt ở 0/1, hẹp dần khi n tăng),
  `flag` đúng ở cả ba trường hợp; đổi được `unit`, `target`, `z`.
- `alerts` loại seller nhỏ, chỉ lấy `above`, sắp theo `excess`.
- Mô phỏng 300 seller có 10 seller tệ thật (5 seed): bắt được ít nhất 8, báo nhầm tối đa 2.
- Trên Olist thật: 2 960 seller, tỉ lệ trễ chung 8.11%, 30–50 cảnh báo với `min_n = 20`, đứng đầu là
  seller `06a2c3af…` (90 đơn trễ trên 388).
- `DASHBOARD.md` không còn TODO, ít nhất 350 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`table.groupby(unit)[target].agg(n="size", events="sum")`. Giới hạn là vector theo n; dùng
`np.where` lồng nhau cho `flag`.

### Gợi ý 2

Xấp xỉ normal kém khi n nhỏ (với 1–2 đơn, một đơn trễ đã vượt giới hạn trên), nên `min_n` không chỉ
là quy ước. Nếu muốn chính xác hơn, giới hạn nhị thức chính xác (`scipy.stats.binom.ppf`) là lựa
chọn tốt; bàn đánh đổi trong `DASHBOARD.md`. Khi viết đặc tả, nghĩ về hành vi: seller có thể "làm
đẹp" chỉ số bằng cách nới ngày hẹn giao.
