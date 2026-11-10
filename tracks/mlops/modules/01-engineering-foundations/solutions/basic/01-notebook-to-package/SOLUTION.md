# Lời giải: từ notebook sang package

## Cách làm

Mỗi cell của notebook thành một hàm có tham số thay cho biến toàn cục:

| Cell cũ | Hàm mới | Thay đổi chính |
| --- | --- | --- |
| Đọc parquet từ `/home/an/Downloads/...` | `data.load_trips(path, max_rows, seed)` | Đường dẫn là tham số; chỉ đọc 5 cột; lấy mẫu theo `seed`; đọc được CSV để test dựng dữ liệu nhỏ |
| Tính `duration_min` và lọc | `data.clean(df)` | Hằng `MAX_MINUTES`, `MAX_MILES` có tên; trả bản sao, không sửa input |
| Dựng `X` | `features.build_features(df)` | Thứ tự cột cố định bằng `FEATURES`, dùng chung cho training và serving |
| Chia, fit, MAE | `model.train(df, seed, max_iter)` | `random_state=seed` ở cả split và model; trả `TrainResult` |
| `joblib.dump(... "C:\\Users\\...")` | `cli.main(argv)` | Đường ra là `--out`; in một dòng JSON để script khác đọc |

`pyproject.toml` dùng `src/` layout: `where = ["src"]` buộc code phải được cài (hoặc `PYTHONPATH=src`) mới import được, nên test không vô tình chạy trên thư mục hiện tại thay vì package đã đóng gói.

## Vì sao

- `random.randint` làm `random_state` là lỗi tái lập kinh điển: mọi lần chạy ra một số khác nên không so sánh được hai thí nghiệm.
- Hàm nhận tham số thay vì đọc biến toàn cục thì test được bằng dữ liệu tổng hợp 3 000 dòng trong 1 giây, còn notebook cần 7 triệu dòng.
- `build_features` dùng chung cho training và `predict` là cách rẻ nhất chống training-serving skew.

## Lỗi hay gặp

- Để `from eta_mini import *` hoặc import tương đối từ thư mục làm việc, nên test chạy được ở máy bạn mà không chạy được khi cài.
- Quên `pyarrow` trong dependencies: đọc parquet lỗi ở máy sạch dù chạy tốt ở máy bạn.
- Lấy mẫu bằng `df.head(n)` thay vì mẫu ngẫu nhiên: tháng bị cắt vào đầu tháng, mẫu lệch theo thời gian.
