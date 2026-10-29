---
title: Thiết kế thí nghiệm cấp cửa hàng trên Rossmann, kiểm chứng bằng A/A
level: advanced
services: []
files:
  - path: starter/store_experiment.ipynb
    note: 3 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Đề xuất thiết kế thí nghiệm
  - path: tests/test_store_experiment.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-science/modules/04-advanced-experimentation/exercises/advanced/01-rossmann-store-experiment/starter/store_experiment.ipynb
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/advanced/01-rossmann-store-experiment -q
---

## Mục tiêu

Thiết kế một thí nghiệm có **ít đơn vị random** (1 115 cửa hàng), tình huống điển hình của
retail, marketplace theo thành phố, hay thí nghiệm theo vùng. Chứng minh bằng dữ liệu thật rằng thiết
kế của bạn vừa không báo động nhầm (A/A) vừa đủ nhạy (power với tác động cài thêm), rồi viết đề xuất
cho người ra quyết định.

## Đề bài

Rossmann thử cách bày hàng mới trong 4 tuần (1–28/6/2015); kỳ trước thí nghiệm là 4–31/5/2015.
Metric: doanh số trung bình mỗi ngày mở cửa của cửa hàng. Mở `starter/store_experiment.ipynb`:

1. `store_panel(train, pre, exp)`: bảng theo cửa hàng, cột `pre` và `y`, chỉ tính ngày
   `Open == 1`, cửa sổ tính cả hai mút, bỏ cửa hàng thiếu một kỳ.
2. `estimate(panel, treat, method)`: `diff`, `se` cho `"diff"`, `"cuped"`, `"poststrat"` (10
   decile của `pre`); phương pháp lạ thì `ValueError`.
3. `power_study(panel, lift, method, n_sims=200, seed=0)`: tỉ lệ $$|z| > 1.96$$ qua nhiều lần chia
   50/50 bằng `rng.permutation`, `y` của treatment nhân `1 + lift`.
4. Phân tích tự do trong các cell `explore`: MDE từng cách, A/A, power ở nhiều mức lift, chia tầng
   theo `StoreType` (bảng `store.csv`) so với theo doanh số, và bất cứ điều gì bạn thấy cần cho
   thiết kế (ngày lễ, khuyến mãi `Promo`, cửa hàng đóng cửa dài ngày…).
5. Viết `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- `store_panel` đúng cửa sổ, chỉ tính ngày mở cửa, bỏ cửa hàng thiếu dữ liệu.
- `estimate` đúng với `"diff"`; CUPED và post-stratification làm SE nhỏ đi rõ rệt khi `pre` dự đoán
  tốt `y`.
- `power_study` cho A/A khoảng 5%, phân biệt được phương pháp yếu và mạnh, tái lập được với seed.
- Trên dữ liệu thật: 1 115 cửa hàng, trung bình `y` khoảng 7 014.2, tương quan `pre`–`y` trên 0.98.
- `REPORT.md` không còn TODO, ít nhất 300 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`train[(train.Open == 1) & (train.Date >= lo) & (train.Date <= hi)].groupby("Store").Sales.mean()`
cho một cửa sổ; `pd.concat({"pre": ..., "y": ...}, axis=1).dropna()` ghép hai cửa sổ. Đọc
`train.csv` với `dtype={"StateHoliday": str}` để tránh cảnh báo kiểu hỗn hợp.

### Gợi ý 2

Chạy `power_study` 1 000 lần cho ba phương pháp mất khoảng 20 giây. Tác động tính theo phần trăm
nên dễ so với MDE: MDE xấp xỉ $$2.8 \times \mathrm{SE}$$ (α = 0.05, power 80%). Khi viết đề xuất,
nhớ rằng tương quan 0.99 giữa hai tháng liền nhau không tự đúng cho mọi tháng: kiểm lại trên một
cặp cửa sổ khác (ví dụ có ngày lễ) trước khi tin.
