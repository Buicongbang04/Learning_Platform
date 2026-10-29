---
title: Synthetic control cho California (Proposition 99)
level: intermediate
services: []
files:
  - path: starter/synth.ipynb
    note: 5 hàm TODO + phần kết luận
  - path: tests/test_synth.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py prop99
  - uv run jupyter lab tracks/data-science/modules/06-causal-inference/exercises/intermediate/02-synthetic-control-california/starter/synth.ipynb
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/intermediate/02-synthetic-control-california -q
---

## Mục tiêu

Ước lượng tác động của một chính sách chỉ áp lên **một** đơn vị bằng synthetic control, và làm
suy luận bằng placebo thay cho standard error, đúng như bài báo gốc của Abadie, Diamond và
Hainmueller (2010).

## Đề bài

Bài Basic 02 cho thấy DiD giữa California và trung bình 38 bang vi phạm parallel trends. Mở
`starter/synth.ipynb`:

1. `to_panel(df, unit="state", time="year", outcome="cigsale")`: panel rộng, index là năm.
2. `synth_weights(y_pre, donors_pre) -> Series`: trọng số không âm, tổng bằng 1, tối thiểu hoá tổng
   bình phương sai lệch trước can thiệp.
3. `synth_gap(panel, treated, pre_years) -> Series`: y thật − y tổng hợp cho mọi năm.
4. `rmspe(gap, years) -> float`.
5. `placebo_ratios(panel, treated, pre_years, post_years) -> Series`: tỉ số RMSPE sau / trước cho
   mọi bang khi coi bang đó là treated (donor của bang placebo không gồm California), sắp giảm dần.
6. Chạy các cell `explore` (biểu đồ, leave-one-out, placebo theo thời gian) và viết kết luận.

Giai đoạn trước: 1970–1988; giai đoạn sau: 1989–2000.

## Tiêu chí đạt

- `synth_weights` tìm đúng tổ hợp lồi khi có nghiệm chính xác, và vẫn hợp lệ (không âm, tổng 1)
  khi đơn vị treated nằm ngoài bao lồi của donor.
- Trên panel mô phỏng (tác động −10): RMSPE trước dưới 1.0, gap trung bình sau trong khoảng ±1.5
  quanh −10, placebo xếp đơn vị treated đầu tiên.
- Trên dữ liệu thật: donor nặng nhất là Utah (≈ 0.39), RMSPE trước ≈ 1.66, gap năm 2000 ≈ −26.6,
  gap trung bình 1989–2000 ≈ −19.5, California đứng thứ 3/39 theo tỉ số RMSPE.

## Gợi ý

### Gợi ý 1

Cách gọn và ổn định: `scipy.optimize.nnls` (least squares với ràng buộc không âm) trên ma trận được
nối thêm một dòng toàn số rất lớn `M`, và vector đích nối thêm `M`. Dòng đó phạt nặng mọi lệch
khỏi `sum(w) = 1`. Chuẩn hoá lại `w / w.sum()` ở cuối. Cách khác là `minimize(method="SLSQP")` với
`bounds` và ràng buộc đẳng thức, nhưng SLSQP có thể dừng ở nghiệm tệ mà không báo lỗi: luôn kiểm tra
RMSPE trước can thiệp.

### Gợi ý 2

`placebo_ratios`: với mỗi cột `unit`, panel dùng là `panel` (nếu `unit` là treated thật) hoặc
`panel.drop(columns=treated)` (nếu là placebo), rồi gọi lại `synth_gap`. Một bang placebo có gap
lớn sau 1989 chỉ đáng lo nếu nó khớp tốt trước 1989; tỉ số sau / trước gói cả hai ý vào một con số.
