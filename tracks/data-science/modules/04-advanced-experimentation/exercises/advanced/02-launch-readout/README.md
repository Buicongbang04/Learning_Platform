---
title: Đọc kết quả ra mắt, novelty effect và heterogeneous effect
level: advanced
services: []
files:
  - path: starter/readout.ipynb
    note: 4 hàm TODO + phân tích tự do
  - path: starter/launch_data.py
    note: Sinh dữ liệu, không sửa
  - path: starter/REPORT.md
    note: Khuyến nghị cho PM
  - path: tests/test_readout.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/data-science/modules/04-advanced-experimentation/exercises/advanced/02-launch-readout/starter/readout.ipynb
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/advanced/02-launch-readout -q
---

## Mục tiêu

Làm việc của DS khi dashboard báo "thắng lớn": kiểm tra con số đó có phải tác động dài hạn không,
tác động có khác nhau giữa các nhóm user không, và nói với PM con số nào nên đưa vào kế hoạch, kèm
độ không chắc chắn trung thực.

## Đề bài

Thí nghiệm 4 tuần, giao diện trang chủ mới của một app đọc truyện, random 50/50 theo user. User vào
thí nghiệm rải rác (user cũ trong tuần đầu, user mới suốt 3 tuần đầu). Dữ liệu sinh bởi
`starter/launch_data.py` (giả lập: không có bộ dữ liệu công khai nào ghi novelty ở mức user-ngày).
Mở `starter/readout.ipynb`:

1. `effect_by_exposure_day(log, metric="minutes")`: tác động theo ngày kể từ lần đầu user thấy thí
   nghiệm, cột `diff`, `se`, `n_t`, `n_c`.
2. `novelty_slope(effects, max_day=None)`: độ dốc WLS của tác động theo ngày phơi nhiễm, kèm `se`,
   `p_value`.
3. `user_level(log)` và `interaction_test(users, segment)`: tác động theo nhóm và kiểm định tương
   tác `treat × segment` bằng Wald test.
4. Phân tích tự do: tác động theo ngày phơi nhiễm cho từng segment, ước lượng tác động dài hạn kèm
   CI, heterogeneous effect theo `segment` và `platform`.
5. Viết `starter/REPORT.md` theo khung.

## Tiêu chí đạt

- Các hàm đúng trên ví dụ tính tay (kể cả trọng số WLS bỏ qua điểm nhiễu lớn).
- Phát hiện novelty khi có, không báo novelty khi không có (|z| < 3.5 trên 3 bộ dữ liệu không có
  novelty).
- `interaction_test` phát hiện tương tác có thật (p < 0.0001) và không báo tương tác không có thật.
- `REPORT.md` không còn TODO, ít nhất 300 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

WLS với variance đã biết: $$\bar x_w = \sum w x / \sum w$$, độ dốc là
$$\sum w (x - \bar x_w) y \,/\, \sum w (x - \bar x_w)^2$$. Với `interaction_test`, các hệ số tương tác
có tên bắt đầu bằng `treat:`; `fit.wald_test("treat:C(segment)[T.new] = 0", scalar=True)` kiểm một
hệ số, nối nhiều điều kiện bằng dấu phẩy để kiểm chung.

### Gợi ý 2

Hai cái bẫy trong dữ liệu này. Một: user mới vào muộn nên có ít ngày phơi nhiễm cao; cửa sổ "ngày
phơi nhiễm 14 trở đi" có **tỉ lệ user mới khác** toàn kỳ. Hai: trong cửa sổ đó mỗi user có nhiều
dòng; SE tính như thể các dòng độc lập là quá nhỏ (bài Basic 02).
