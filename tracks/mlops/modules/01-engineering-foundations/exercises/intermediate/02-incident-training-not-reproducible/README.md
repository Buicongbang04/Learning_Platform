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

Chẩn đoán một pipeline train không tái lập chỉ từ triệu chứng, tìm đủ các nguồn khiến kết quả đổi và sửa cho đến khi test chứng minh được.

## Đề bài

Thứ Năm, 10:15. Chị Lan chạy `train("trips/", seed=0)` hai lần liên tiếp trên cùng một thư mục dữ liệu và ra **hai MAE khác nhau**.
Anh Minh chạy cùng lệnh trên máy khác cũng ra số thứ ba. Code ghi rõ `seed=0` và nhóm đã tin là xong. Việc release model đang bị chặn vì không ai chứng minh được con số nào là thật.

`starter/pipeline.py` là pipeline đang chạy. Tìm nguyên nhân và sửa để kết quả tái lập được. Có thể có hơn một nguyên nhân; sửa xong một cái có thể lộ ra cái khác.

**Hợp đồng test dựa vào** (giữ nguyên tên và kiểu trả về):

- `train(data_dir, seed=0)` trả một số `float`, là MAE trên tập test.
- `load_trips(data_dir)` trả một DataFrame gồm toàn bộ dòng của mọi tệp `.csv` trong thư mục (các cột `trip_distance`, `hour`, `duration_min`); tệp khác đuôi `.csv` bị bỏ qua.
- Dữ liệu test là bốn tệp CSV nhỏ trong thư mục tạm. Giữa các lần chạy, test thay đổi trạng thái `random` và `np.random` toàn cục, và giả lập hệ tệp liệt kê tệp theo các thứ tự khác nhau (qua `os.listdir` và `os.scandir`).

## Tiêu chí đạt

- Hai lần `train` cùng `seed` cho đúng cùng một MAE, dù trạng thái `random` và `np.random` toàn cục khác nhau.
- MAE không phụ thuộc thứ tự hệ tệp liệt kê các tệp trong thư mục.
- `seed` khác nhau vẫn cho cách chia dữ liệu khác nhau (seed thật sự được dùng): MAE của seed 0 và seed 1 khác nhau.
- `train` không làm đổi trạng thái `random` và `np.random` toàn cục của chương trình gọi nó.
- `load_trips` bỏ qua tệp không phải `.csv` (vd. `_SUCCESS`) và mô hình vẫn học được: MAE nhỏ hơn 0,6 lần MAE của cách đoán trung bình.

## Gợi ý

### Gợi ý 1

Liệt kê mọi nơi trong pipeline mà kết quả có thể thay đổi giữa hai lần chạy: mọi chỗ lấy số ngẫu nhiên, và mọi chỗ phụ thuộc vào thứ tự mà môi trường trả về.

### Gợi ý 2

Chạy `train` hai lần trong cùng một tiến trình rồi so. Sau đó thay đổi một yếu tố môi trường mỗi lần và xem so sánh có còn bằng nhau không; làm vậy bạn biết nguồn nào còn sót.

### Gợi ý 3

So sánh dữ liệu (hash của DataFrame) sau từng bước `load`, `split`, `fit` giữa hai lần chạy: bước đầu tiên hai hash khác nhau là nơi cần sửa.
