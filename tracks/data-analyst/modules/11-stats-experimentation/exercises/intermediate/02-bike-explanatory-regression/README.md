---
title: Regression để giải thích - thời tiết đáng giá bao nhiêu lượt thuê xe
level: intermediate
services: []
files:
  - path: starter/weather_regression.ipynb
    note: 5 hàm TODO + ba câu cho trưởng vận hành
  - path: tests/test_weather_regression.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/intermediate/02-bike-explanatory-regression/starter/weather_regression.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/intermediate/02-bike-explanatory-regression -q
---

## Mục tiêu

Dùng regression để **giải thích** chứ không để dự báo: chọn biến kiểm soát, đọc hệ số theo đơn vị business
("ấm thêm 5°C", "mưa nhỏ") kèm khoảng tin cậy, thấy hệ số thay đổi khi thêm biến (omitted variable bias), kiểm
giả định ảnh hưởng tới sai số chuẩn (heteroskedasticity, tự tương quan), và biết giới hạn của cách đọc "giữ các yếu
tố khác cố định".

## Đề bài

Bộ `bike-sharing-uci`, `day.csv` (731 ngày). Trưởng vận hành hỏi: giữ mọi thứ khác như nhau, nhiệt độ, độ ẩm, gió,
mưa, ngày lễ làm lượt thuê thay đổi bao nhiêu? Mở `starter/weather_regression.ipynb` (hằng `SEASONS`, `WEATHER`,
`FORMULA` có sẵn):

1. `prepare(day)`: thêm `temp_c`, `hum_pct`, `wind_kmh`, `season_name`, `weather`, `year`.
2. `fit_explanatory(df, formula, cov_type)`: OLS với sai số chuẩn HC3 (mặc định) hoặc HAC 7 ngày.
3. `effect_table(res, units)`: hệ số × số đơn vị, kèm khoảng tin cậy và p.
4. `coef_path(df, var, steps)`: hệ số của một biến qua các model thêm dần biến kiểm soát.
5. `turning_point(res, var, var_sq)`: đỉnh của đường cong bậc hai.
6. Chạy các cell `explore`: bảng hệ số, chart hiệu ứng có khoảng tin cậy, đường đi của hệ số nhiệt độ, so HC3 với
   HAC, đường cong nhiệt độ, residual theo ngày. Trả lời 6 câu cuối notebook và viết ba câu cho trưởng vận hành.
   Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: `fit_explanatory` khớp statsmodels với HC3 và HAC; `effect_table` đúng thứ tự dòng,
  cột và nhân cả khoảng tin cậy; `coef_path` và `turning_point` đúng.
- Trên bộ thật: R² = 0.823; hệ số nhiệt độ **124.6 lượt/°C** (ấm thêm 5°C: +623 lượt, CI [539; 707]); ngày lễ
  −624 lượt; hệ số nhiệt độ đi từ 162.0 (một biến) xuống 155.4 khi thêm năm.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`day.assign(...)` với `.map(SEASONS)`, `.map(WEATHER)`. `smf.ols(formula, df).fit(cov_type="HC3")`; với HAC:
`fit(cov_type="HAC", cov_kwds={"maxlags": 7})`. Tên hệ số lấy từ `res.params.index` (biến phân loại có dạng
`C(weather, Treatment('clear'))[T.mist]`).

### Gợi ý 2

`res.conf_int()` trả DataFrame hai cột `0` và `1`. Dựng dict các dòng rồi `pd.DataFrame.from_dict(rows,
orient="index")` để giữ thứ tự khoá. `coef_path`: `pd.Series({label: ... for label, f in steps.items()}, name=var)`.

### Đọc thêm

Lý thuyết OLS, robust SE, VIF ở DS
[05-econometrics-regression](../../../../../../data-science/modules/05-econometrics-regression/README.md). Bài này
không đòi chẩn đoán đầy đủ; nó luyện cách nói kết quả regression cho người không đọc bảng hệ số.
