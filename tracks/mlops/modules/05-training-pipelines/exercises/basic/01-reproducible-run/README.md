---
title: Run tái lập được - seed, fingerprint dữ liệu, artifact có hash và manifest
level: basic
services: []
files:
  - path: starter/repro.py
    note: 5 hàm TODO
  - path: tests/test_repro.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/basic/01-reproducible-run -q
---

## Mục tiêu

Làm cho một lần train trả lời được câu "chạy lại có ra đúng artifact này không?" bằng bằng chứng, không bằng niềm tin:
seed tường minh, hash của dữ liệu, hash của artifact, và một manifest ghi đủ để chạy lại.

## Đề bài

`starter/repro.py` có sẵn `make_dataset` (dữ liệu taxi tổng hợp nhỏ, chỉ dùng cho test), `FEATURES`, `TARGET` và `DEFAULT_PARAMS`
(`n_estimators` 20, `max_depth` 6). Cài năm hàm:

1. `data_fingerprint(df)`: sha256 (64 ký tự hex) của nội dung bảng. Cùng nội dung thì cùng hash, đổi một ô thì khác hash, đổi
   thứ tự dòng cũng khác hash.
2. `train(df, seed, params=None)`: `RandomForestRegressor` trên `FEATURES` để dự đoán `TARGET`; `params` ghi đè `DEFAULT_PARAMS`;
   `n_jobs=1`. Cùng `seed` phải cho artifact giống từng byte; kết quả **không** được phụ thuộc trạng thái random toàn cục
   (`np.random.seed(...)` gọi trước đó không được làm đổi kết quả). Không sửa `df` đầu vào.
3. `save_artifact(model, path)`: ghi model bằng `joblib`, trả sha256 của đúng các byte trong tệp.
4. `build_manifest(df, seed, params, artifact_path)`: dict có đúng các khoá `data_sha256`, `seed`, `params` (đã gộp mặc định),
   `artifact_sha256`, `python` (`platform.python_version()`), `sklearn`, `numpy` (chuỗi phiên bản).
5. `verify(manifest, artifact_path)`: `True` nếu tệp tồn tại và hash khớp `artifact_sha256`; tệp bị sửa hoặc không tồn tại thì
   `False` (không ném lỗi).

## Tiêu chí đạt

- Hai lần train cùng seed ra cùng `artifact_sha256`; seed khác ra hash khác.
- Gọi `np.random.seed(1)` rồi `np.random.seed(2)` trước `train` không đổi hash.
- Thêm một byte vào artifact thì `verify` trả `False`.
- Chạy lại từ manifest (`seed`, `params`) trên cùng dữ liệu cho `verify` ra `True`.

## Gợi ý

### Gợi ý 1

Seed của `RandomForestRegressor` truyền qua `random_state`. Đừng dựa vào `np.random.seed` toàn cục: ai đó gọi nó giữa chừng
hoặc thứ tự import đổi là kết quả đổi. Một mô hình train song song nhiều luồng cũng có thể cộng dồn số thực theo thứ tự khác
nhau, vì vậy đặt `n_jobs=1` cho bài này.

### Gợi ý 2

`df.to_csv(index=False)` cho chuỗi xác định để băm. Hash tệp artifact bằng `hashlib.sha256(path.read_bytes())`; viết một hàm
nhỏ dùng chung cho `save_artifact`, `build_manifest` và `verify` để ba chỗ không lệch nhau.
