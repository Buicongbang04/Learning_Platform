---
title: Đánh đổi chi phí, độ trễ, chất lượng - cache, batch, distillation
level: basic
services: []
files:
  - path: starter/tradeoffs.py
    note: 4 hàm TODO
  - path: tests/test_tradeoffs.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/02-cost-latency-tradeoffs -q
---

## Mục tiêu

Ở quy mô lớn, câu hỏi senior không phải "model nào tốt nhất" mà "mỗi mili giây và mỗi điểm chất lượng tốn bao nhiêu tiền".
Bạn viết bốn phép tính nhỏ để so phương án bằng số thay vì cảm giác: cache trước model, batch hay realtime, distill model to
thành model nhỏ, và chọn phương án rẻ nhất thoả ràng buộc. Sau đó làm phần trắc nghiệm chọn phương án theo tình huống.

## Đề bài

Điền 4 hàm trong `starter/tradeoffs.py`. Các công thức là mô hình đơn giản hoá có chủ ý (README module mục 5 nói chỗ nào
nó sai ngoài đời).

**`cache_plan(qps, hit_rate, cache_ms, cache_p99_ms, model_ms, model_p99_ms, model_cost_per_1k, cache_cost_per_hour)`** trả dict:

- `mean_ms = cache_ms + (1 - hit_rate) x model_ms` (miss vẫn phải tra cache trước).
- `p99_ms`: nếu tỉ lệ miss `1 - hit_rate` **lớn hơn 0.01** thì `cache_ms + model_p99_ms`, ngược lại `cache_p99_ms`.
- `model_calls_per_hour = qps x 3600 x (1 - hit_rate)`.
- `cost_per_hour = model_calls_per_hour / 1000 x model_cost_per_1k + cache_cost_per_hour`.
- `hit_rate` ngoài `[0, 1]` thì `raise ValueError`.

**`batch_vs_realtime(entities, refreshes_per_day, batch_cost_per_1k, requests_per_day, realtime_cost_per_1k, realtime_fixed_per_day)`**
trả dict:

- `batch_cost_per_day = entities x refreshes_per_day / 1000 x batch_cost_per_1k` (tính trước cho mọi thực thể, dù có ai hỏi hay không).
- `realtime_cost_per_day = requests_per_day / 1000 x realtime_cost_per_1k + realtime_fixed_per_day` (replica bật cả ngày).
- `batch_max_staleness_h = 24 / refreshes_per_day`.
- `cheaper`: `"batch"` nếu chi phí batch nhỏ hơn **hoặc bằng** realtime, ngược lại `"realtime"`.
- `refreshes_per_day <= 0` thì `raise ValueError`.

**`distillation_breakeven_days(teacher_cost_per_1k, student_cost_per_1k, one_off_cost, requests_per_day)`**: số ngày để tiền tiết
kiệm mỗi ngày `(teacher - student) x requests_per_day / 1000` bù chi phí distill một lần `one_off_cost`; trả `math.inf` khi student
không rẻ hơn.

**`choose(options, max_p99_ms, max_quality_drop)`**: mỗi phương án là dict `name`, `cost_per_day`, `p99_ms`, `quality_drop`.
Trả `name` của phương án có `cost_per_day` nhỏ nhất trong số thoả `p99_ms <= max_p99_ms` **và** `quality_drop <= max_quality_drop`;
hoà chi phí thì chọn `p99_ms` nhỏ hơn; không phương án nào thoả thì `None`.

Sau khi test pass, làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/02-cost-latency-tradeoffs -q` pass.
- Bạn giải thích được vì sao cache 80% hit làm latency trung bình giảm 4 lần nhưng không đổi p99.
- Bạn nêu được một trường hợp batch rẻ hơn nhưng vẫn phải chọn realtime.

## Gợi ý

### Gợi ý 1

Viết tỉ lệ miss một lần (`miss = 1 - hit_rate`) và dùng lại. Kiểm `hit_rate` trước khi tính.

### Gợi ý 2

`min(feasible, key=lambda o: (o["cost_per_day"], o["p99_ms"]))` xử lý hoà chi phí bằng tuple.
