---
title: Sự cố - hai lần train ra MAE khác nhau
level: intermediate
services: []
files:
  - path: starter/pipeline.py
    note: Pipeline đang chạy, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/intermediate/02-incident-training-not-reproducible -q
---

## Mục tiêu

Chẩn đoán một pipeline train không tái lập chỉ từ triệu chứng, tìm đủ các nguồn ngẫu nhiên và viết test chứng minh đã sửa.

## Đề bài

Thứ Năm, 10:15. Chị Lan chạy `train("trips/", seed=0)` hai lần liên tiếp trên cùng một thư mục dữ liệu và ra **hai MAE khác nhau**.
Anh Minh chạy cùng lệnh trên máy khác cũng ra số thứ ba. Code ghi rõ `seed=0` và còn có `np.random.seed(seed)` ở dòng đầu hàm `train`, nhóm đã tin là xong.
Việc release model đang bị chặn vì không ai chứng minh được con số nào là thật.

`starter/pipeline.py` là pipeline đang chạy. Tìm nguyên nhân và sửa để kết quả tái lập được. Có thể có hơn một nguyên nhân; sửa xong một cái có thể lộ ra cái khác.

Test chạy trên bốn tệp CSV nhỏ trong thư mục tạm. Nó thay đổi trạng thái `random` và `np.random` toàn cục giữa hai lần chạy, và giả lập hệ tệp trả danh sách tệp theo thứ tự khác nhau, như hai máy khác nhau.

## Tiêu chí đạt

- Hai lần `train` cùng `seed` cho đúng cùng một MAE, dù trạng thái `random` và `np.random` toàn cục khác nhau.
- MAE không phụ thuộc thứ tự mà hệ tệp liệt kê các tệp trong thư mục.
- `seed` khác nhau vẫn cho cách chia dữ liệu khác nhau (seed thật sự được dùng).
- `train` không làm đổi trạng thái `random` và `np.random` toàn cục của chương trình gọi nó.
- Tệp không phải `.csv` (vd. `_SUCCESS`) bị bỏ qua, mô hình vẫn học được.

## Gợi ý

### Gợi ý 1

Liệt kê mọi nơi có yếu tố "ngẫu nhiên" hoặc "thứ tự không xác định": thư viện nào được gọi, nó lấy ngẫu nhiên từ đâu, và dữ liệu vào hàm chia có thứ tự cố định không.

### Gợi ý 2

`np.random.seed` chỉ gieo hạt cho `np.random` toàn cục, không phải cho module `random` của Python. `os.listdir` không đảm bảo thứ tự.

### Gợi ý 3

Dùng bộ sinh cục bộ `np.random.default_rng(seed)` và `random_state=seed` cho model thay vì gieo hạt toàn cục; sắp xếp danh sách tệp trước khi đọc.
