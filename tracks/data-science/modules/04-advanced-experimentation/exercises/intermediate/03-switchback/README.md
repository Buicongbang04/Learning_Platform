---
title: Network effect trong marketplace và switchback experiment
level: intermediate
services: []
files:
  - path: starter/switchback.py
    note: 3 hàm TODO
  - path: tests/test_switchback.py
    note: Không sửa (chứa simulator marketplace, đọc để hiểu cơ chế)
run:
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/intermediate/03-switchback -q
---

## Mục tiêu

Thấy tận mắt vì sao A/B test theo user cho kết quả **sai cả hướng độ lớn** trong marketplace có
nguồn cung chung, và sửa bằng switchback: random theo khoảng thời gian, bỏ giai đoạn chuyển tiếp
(burn-in) để xử lý carryover.

## Đề bài

Simulator trong `tests/test_switchback.py` mô phỏng một nền tảng giao hàng: mỗi period có khoảng
1 000 user, mỗi user đặt đơn với xác suất 10%; treatment (giảm phí ship) tăng xác suất đặt thêm
50%. Mỗi period chỉ có 110 shipper; đơn vượt quá không được phục vụ và một nửa trong số đó đặt lại
ở period sau. Metric: **số đơn được phục vụ trên mỗi user**. Tác động cần đo là tác động **toàn
cục**: bật cho tất cả so với tắt cho tất cả.

Trong `starter/switchback.py`:

1. `switchback_schedule(n_periods, block, seed=0)`: mảng 0/1, các period gom thành block `block`
   period liên tiếp cùng nhánh, số block hai nhánh lệch tối đa 1, thứ tự block ngẫu nhiên. Block
   cuối có thể thiếu.
2. `switchback_estimate(periods, burn_in=0) -> dict`: `diff`, `se`, `n_used`. Metric mỗi period
   là `orders / users`. Bỏ `burn_in` period đầu của **mỗi đoạn liên tiếp cùng nhánh** (kể cả đoạn
   đầu chuỗi), rồi so trung bình hai nhánh với SE Welch trên các period còn lại. Không được phụ
   thuộc thứ tự dòng của DataFrame.
3. `user_split_estimate(users) -> dict`: `diff`, `se` của A/B theo user thông thường.

## Tiêu chí đạt

- Lịch switchback đúng cấu trúc block, cân bằng, tái lập được.
- Hai hàm ước lượng đúng trên ví dụ tính tay (kể cả cách bỏ burn-in).
- A/B theo user ước lượng tác động lớn hơn 2.5 lần tác động toàn cục, với CI rất hẹp quanh con số
  sai.
- Đổi nhánh mỗi period và không bỏ burn-in: ước lượng nhỏ hơn 0.6 lần tác động thật.
- Block 6 period, bỏ 2 period đầu mỗi block: trung bình 5 lần chạy cách tác động thật dưới 15%, và
  gần hơn so với không bỏ burn-in.

## Gợi ý

### Gợi ý 1

Lịch: `n_blocks = ceil(n_periods / block)`, `rng.permutation(np.arange(n_blocks) % 2)` cho nhánh
từng block, `np.repeat(arms, block)[:n_periods]`.

### Gợi ý 2

Đánh số đoạn liên tiếp cùng nhánh: sắp theo `period`, `run_id = (treat != treat.shift()).cumsum()`.
Vị trí trong đoạn: `groupby(run_id).cumcount()`. Giữ các dòng có vị trí `>= burn_in`.
