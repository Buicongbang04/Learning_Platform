---
title: Panel Grunfeld - tự viết fixed effects, Hausman và chọn model
level: advanced
services: []
files:
  - path: starter/panel.py
    note: within_estimator, hausman
  - path: starter/REPORT.md
    note: Báo cáo chọn model
  - path: tests/test_panel.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/advanced/01-grunfeld-panel -q
---

## Mục tiêu

Hiểu fixed effects từ bên trong (within transformation, bậc tự do), tự viết Hausman test, rồi làm
việc một DS / econometrician thật sự làm: so nhiều spec, chọn một model, bảo vệ lựa chọn đó bằng lập
luận chứ không chỉ bằng p-value.

## Đề bài

Dữ liệu Grunfeld có sẵn trong statsmodels (`sm.datasets.grunfeld.load_pandas().data`, cột `invest`,
`value`, `capital`, `firm`, `year`), không cần tải.

1. `within_estimator(df, entity, y, xs) -> dict` trong `starter/panel.py`, theo docstring: demean theo
   entity, OLS không hằng số, SE cổ điển với bậc tự do $$n - N - k$$, chạy được với panel không cân
   bằng, raise `ValueError` với biến không đổi trong từng entity.
2. `hausman(b_fe, b_re, cov_fe, cov_re) -> (H, p)`:

$$
H = (\hat\beta_{FE} - \hat\beta_{RE})^\top \left[\widehat{V}_{FE} - \widehat{V}_{RE}\right]^{-1} (\hat\beta_{FE} - \hat\beta_{RE})
$$

   trên các hệ số chung (bỏ hằng số), so với $$\chi^2$$ có bậc tự do bằng số hệ số. Nhận trực tiếp
   `params` và `cov` từ `linearmodels`.
3. Dùng `linearmodels` (`PooledOLS`, `PanelOLS`, `RandomEffects`) để fit pooled, FE, RE, two-way FE,
   với SE cổ điển và cluster theo công ty.
4. Viết `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- `within_estimator` khớp `PanelOLS(entity_effects=True)` (hệ số và SE) trên Grunfeld và trên panel
  không cân bằng; loại được omitted variable bias khi hiệu ứng riêng tương quan với x.
- `hausman` cho H ≈ 3.97, p ≈ 0.138 trên Grunfeld; bác bỏ mạnh khi hiệu ứng riêng tương quan với x,
  không bác bỏ khi không tương quan.
- `REPORT.md` không còn TODO, ít nhất 300 từ.
- Phần còn lại chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`df[cols] - df.groupby(entity)[cols].transform("mean")` demean cho cả panel không cân bằng. Biến không
đổi trong từng entity sẽ thành cột toàn 0 sau khi demean.

### Gợi ý 2

`linearmodels` cần MultiIndex `(entity, time)`: `g.set_index(["firm", "year"])`, cột `year` ép về
`int`. `PanelOLS(...).fit(cov_type="clustered", cluster_entity=True)` cho cluster SE. `fe.f_pooled`
là F test cho fixed effects; `re.variance_decomposition` cho tỉ lệ variance ở cấp công ty.
