---
title: Phân tích thí nghiệm Cookie Cats trên notebook
level: intermediate
services: []
files:
  - path: starter/analysis.ipynb
    note: 3 hàm TODO + phần khuyến nghị
  - path: tests/test_analysis.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cookie-cats
  - uv run jupyter lab tracks/data-science/modules/03-ab-testing/exercises/intermediate/01-cookie-cats-retention/starter/analysis.ipynb
  - uv run pytest tracks/data-science/modules/03-ab-testing/exercises/intermediate/01-cookie-cats-retention -q
---

## Mục tiêu

Phân tích trọn một thí nghiệm thật như ở công ty: hiểu dữ liệu, tóm tắt theo nhóm, ước lượng tác
động kèm khoảng tin cậy bằng bootstrap, ra quyết định theo quy tắc đã định trước, và viết khuyến
nghị cho người không làm thống kê.

## Đề bài

Bộ Cookie Cats: 90 189 người chơi mới được chia ngẫu nhiên vào `gate_30` (control) và `gate_40`
(treatment). Mở `starter/analysis.ipynb` và làm theo thứ tự:

1. Chạy các cell `explore` ở đầu: kiểm tra userid trùng, phân phối `sum_gamerounds`, giá trị lạ.
2. `retention_summary(df)`: DataFrame index là `version`, cột `n`, `retention_1`, `retention_7`.
3. `bootstrap_diff_ci(df, metric, n_boot=2000, seed=0, alpha=0.05) -> (diff, lo, hi)`:
   `diff = mean(gate_40) − mean(gate_30)` trên dữ liệu gốc; `[lo, hi]` là percentile bootstrap,
   resample **riêng từng nhóm**, dùng `np.random.default_rng(seed)` để tái lập được. Phải chạy
   nhanh (vài giây) trên dữ liệu thật với `n_boot=2000`.
4. `decision(df, metric="retention_7") -> str`: `"ship_gate_40"` nếu CI nằm trên 0,
   `"keep_gate_30"` nếu nằm dưới 0, ngược lại `"inconclusive"`.
5. Viết khuyến nghị 5–8 câu trong cell markdown cuối (không chấm tự động; so với lời giải mẫu).

## Tiêu chí đạt

- Bảng tóm tắt đúng số người và tỉ lệ mỗi nhóm.
- CI bootstrap chứa chênh lệch quan sát, độ rộng xấp xỉ CI công thức (sai lệch dưới 15%), CI 99%
  rộng hơn CI 95%, cùng seed cho cùng kết quả.
- `decision` đúng cả ba nhánh.
- Trên dữ liệu thật: 44 700 / 45 489 người, `retention_7` ≈ 19.02% / 18.20%, quyết định
  `keep_gate_30`.
- Khuyến nghị có nhắc tới SRM và những gì thí nghiệm không đo.

## Gợi ý

### Gợi ý 1

`df.groupby("version").agg(n=("userid", "size"), retention_1=("retention_1", "mean"), ...)`.
Cột `retention_*` là bool; `mean` của bool cho tỉ lệ.

### Gợi ý 2

Resample ngây thơ (`rng.choice(x, len(x))` 2 000 lần) trên 45 nghìn dòng tốn vài chục giây. Với
cột 0/1, tổng của một mẫu bootstrap kích thước n chính là `Binomial(n, p̂)`, nên
`rng.binomial(n, x.mean(), n_boot) / n` cho đúng phân phối bootstrap, tức thì.
