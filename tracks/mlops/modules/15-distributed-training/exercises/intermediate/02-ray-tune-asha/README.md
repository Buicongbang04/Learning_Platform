---
title: Ray Tune nhiều trial song song với dừng sớm ASHA
level: intermediate
services: []
files:
  - path: starter/tune_search.py
    note: 3 hàm TODO (train_model, search, best)
  - path: tests/test_tune.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/02-ray-tune-asha -q
---

## Mục tiêu

Tìm siêu tham số cho một MLP nhỏ bằng Ray Tune: nhiều trial chạy song song trên Ray cục bộ, scheduler ASHA dừng sớm trial kém để dồn
tài nguyên cho trial hứa hẹn, kết quả ghi vào thư mục storage chỉ định, rồi chọn config tốt nhất theo đúng metric.

## Đề bài

`starter/tune_search.py` có sẵn dữ liệu hồi quy sinh theo `SEED` (512 mẫu train, 256 mẫu validation), `build_model(hidden)` và các
hằng `MAX_EPOCHS`, `BATCH`, `LR_RANGE`, `HIDDEN_CHOICES`. Điền 3 hàm:

- **`train_model(config)`**: trainable dạng hàm của Tune. Dựng `build_model(config["hidden"])`, SGD với `lr=config["lr"]`, huấn luyện
  `MAX_EPOCHS` epoch theo batch `BATCH` trên phần train; **sau mỗi epoch** báo `{"loss": MSE trên validation}` bằng `tune.report`.
- **`search(storage_path, num_samples=12) -> ResultGrid`**: chạy `num_samples` trial với không gian tìm kiếm
  `lr ~ loguniform(LR_RANGE)`, `hidden ~ choice(HIDDEN_CHOICES)` (đúng hai khoá này), metric `loss` nhỏ hơn là tốt hơn, scheduler
  **ASHA** với `max_t=MAX_EPOCHS`, `grace_period=1`, `reduction_factor=2`; kết quả lưu dưới `storage_path` (`RunConfig(storage_path=...)`).
  Không gọi `ray.init` trong hàm: Ray do người gọi khởi tạo.
- **`best(results) -> dict`**: `{"config": config của trial tốt nhất, "loss": loss cuối cùng của trial đó}`, "tốt nhất" là loss **cuối
  cùng** (lần báo sau chót của mỗi trial) nhỏ nhất.

Test khởi tạo Ray bằng `mlopskit.ray_local(num_cpus=2)` (chỉ loopback, thư mục tạm riêng, dọn khi xong; mỗi trial 1 CPU nên 2 trial chạy
cùng lúc), gọi `search(storage, num_samples=12)` rồi kiểm:

- Đủ 12 trial, không trial nào lỗi, mọi `loss` là số hữu hạn; có tệp được ghi vào `storage_path`.
- Có trial chạy đủ `MAX_EPOCHS` vòng và có ít nhất một trial dừng sớm (`training_iteration < MAX_EPOCHS`).
- Mọi config có đúng hai khoá, nằm trong không gian tìm kiếm; 12 giá trị `lr` khác nhau.
- `best(...)` trả đúng trial có loss cuối nhỏ nhất, và loss đó nhỏ hơn một nửa phương sai của nhãn validation (model học thật).

Cả bài mất khoảng 30-60 giây (khởi động Ray chiếm phần lớn). Test có giới hạn cứng **180 giây** cho cả lần tìm kiếm: quá hạn
(vd. trial xin nhiều CPU hơn 2 CPU của Ray cục bộ nên nằm `PENDING` mãi) thì mọi test của bài fail với thông báo hết giờ,
Ray vẫn được tắt và dọn sạch. Tự chạy script bằng `uv run` thì đặt hai biến môi trường ở mục 0 của
README module.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/02-ray-tune-asha -q` pass.
- Bạn giải thích được vì sao ASHA cần trainable báo metric **mỗi epoch** chứ không chỉ một lần ở cuối.
- Bạn nói được search algorithm và scheduler khác nhau ở đâu, và khi nào ASHA dừng nhầm một config tốt.

## Gợi ý

### Gợi ý 1

`from ray import tune`; `tune.Tuner(train_model, param_space={...}, tune_config=tune.TuneConfig(...), run_config=tune.RunConfig(...)).fit()`.
`ASHAScheduler` nằm ở `ray.tune.schedulers`.

### Gợi ý 2

Khai báo `metric` và `mode` ở `TuneConfig` thì không truyền lại cho scheduler. `ResultGrid.get_best_result(metric=..., mode=..., scope=...)`:
đọc kỹ `scope` để biết "tốt nhất" tính theo lần báo nào.

### Gợi ý 3

Trial nằm `PENDING` mãi khi tự chạy qua `uv run`: thiếu `RAY_ENABLE_UV_RUN_RUNTIME_ENV=0`.
