---
title: Từ notebook "train ETA mini" sang package
level: basic
services: []
files:
  - path: starter/train_eta_mini_nb.py
    note: Notebook cũ xuất ra script, chỉ đọc
  - path: starter/pyproject.toml
    note: 3 TODO
  - path: starter/src/eta_mini/data.py
    note: 2 TODO
  - path: starter/src/eta_mini/features.py
    note: 1 TODO
  - path: starter/src/eta_mini/model.py
    note: 2 TODO
  - path: starter/src/eta_mini/cli.py
    note: 1 TODO
  - path: tests/test_package.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/basic/01-notebook-to-package -q
---

## Mục tiêu

Biến một notebook chạy được trên máy một người thành package có hàm `train()` gọi được, CLI chạy được ở thư mục bất kỳ và test pass.

## Đề bài

`starter/train_eta_mini_nb.py` là notebook "train ETA mini" của một đồng nghiệp: đọc một tệp parquet tháng 1/2019 của NYC Yellow Taxi,
làm sạch, tạo 5 feature, train `HistGradientBoostingRegressor` dự đoán thời lượng chuyến (phút) và lưu model ra Desktop. Nó có ba vấn đề:
đường dẫn của máy cá nhân, `random_state=random.randint(...)` nên mỗi lần chạy ra một MAE, và mọi thứ nằm ở top-level nên không import hay test được.

Chuyển logic sang package `eta_mini` theo `src/` layout (đã có khung trong `starter/src/eta_mini/`):

- `data.load_trips(path, max_rows, seed)`: đọc `.parquet` hoặc `.csv` theo đuôi tệp, chỉ đọc 5 cột trong `TRIP_COLUMNS`, lấy mẫu theo `seed`.
- `data.clean(df)`: thêm `duration_min`; giữ chuyến có `0 < duration_min <= 180` và `0 < trip_distance <= 100`.
- `features.build_features(df)`: DataFrame đúng cột và thứ tự của `FEATURES`.
- `model.train(df, seed, max_iter)` chia 80/20 (số dòng test xấp xỉ 20%, `n_train + n_test` bằng số dòng đầu vào) và trả `TrainResult`; `model.predict(model, df)` dự đoán từ chuyến thô.
- `cli.main(argv)` với `--data`, `--out`, `--seed`, `--max-rows`; in đúng một dòng JSON `{"mae", "n_train", "n_test"}` ra stdout.
- `pyproject.toml`: `requires-python`, dependencies, entry point `eta-train`, build backend setuptools tìm package trong `src/`.

Package không được chứa đường dẫn của máy cá nhân. Test chạy CLI trong sandbox `bubblewrap`; thiếu `bwrap` thì test đó tự skip (xem `## 0. Cài đặt` của module).

## Tiêu chí đạt

- `pyproject.toml` khai báo đủ dependency, entry point và `src/` layout.
- Không còn đường dẫn kiểu `/home/...`, `C:\...`, `Downloads`, `Desktop` trong package.
- `load_trips` đọc được CSV và Parquet, trả đúng 5 cột theo thứ tự `TRIP_COLUMNS` (cột giờ đón và giờ trả là kiểu datetime, `max_rows` cho đúng `max_rows` dòng), mẫu giống nhau khi cùng seed.
- `clean` loại đúng các chuyến bẩn theo luật; `build_features` đúng cột và thứ tự.
- `train` chạy được, `predict` trả đúng một giá trị hữu hạn cho mỗi chuyến, MAE nhỏ hơn một nửa MAE của cách đoán trung bình trên dữ liệu tổng hợp, cùng seed thì cùng MAE.
- `python -m eta_mini ...` chạy được từ thư mục bất kỳ, ghi model ra `--out`.
- Trên một mẫu 30 000 chuyến thật của 2019-01 (nếu đã tải `nyc-tlc`), MAE tốt hơn đoán trung vị.

## Gợi ý

### Gợi ý 1

Chép logic từng cell vào đúng hàm; cell đọc dữ liệu thành `load_trips`, cell lọc thành `clean`, cell tạo `X` thành `build_features`. Đừng giữ biến toàn cục.

### Gợi ý 2

`pd.read_parquet(path, columns=...)` chỉ đọc cột cần; với CSV dùng `usecols` và `parse_dates`. Lấy mẫu bằng `df.sample(n=..., random_state=seed)`.
Seed đi vào ba chỗ: lấy mẫu, `train_test_split` và model.

### Gợi ý 3

Entry point trong `[project.scripts]` có dạng `tên = "package.module:hàm"`. Với `src/` layout, setuptools cần
`[tool.setuptools.packages.find]` với `where = ["src"]`.
