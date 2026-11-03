---
title: Hồ sơ dữ liệu Oxford-IIIT Pets và trimap trước khi serving
level: basic
services: []
files:
  - path: starter/pets_profile.ipynb
    note: 6 hàm TODO, cell explore
  - path: tests/test_pets_profile.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py oxford-pets
  - uv run python data/download_dataset.py oxford-pets-trimaps
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/basic/03-pets-trimap-profile -q
---

## Mục tiêu

Trước khi viết service phân đoạn, đo dữ liệu thật mà service sẽ nhận: ảnh lớn cỡ nào, mode màu gì, trimap ghép được với ảnh không, lớp nào hiếm. Các con số này quyết định giới hạn kích thước của service, bước tiền xử lý và metric dùng để chấm model.

## Đề bài

Làm việc trong `starter/pets_profile.ipynb`. Trimap là PNG một kênh, giá trị `1` thú cưng, `2` nền, `3` viền (hằng `TRIMAP_CLASSES`). Ảnh nằm trong hai tệp parquet `data/train-00000-of-00001.parquet` và `data/test-00000-of-00001.parquet` (cột `image` là struct có `bytes`, cột `image_id`). Điền 6 hàm:

- `list_trimaps(trimap_dir)`: list `Path` các tệp `*.png` trong thư mục, sắp xếp, **bỏ** tệp có tên bắt đầu bằng `._` (metadata AppleDouble của macOS, không phải ảnh).
- `trimap_profile(paths)`: DataFrame cột đúng thứ tự `image_id` (tên tệp bỏ đuôi), `height`, `width`, `pet`, `background`, `border`; ba cột cuối là tỉ lệ pixel có giá trị 1, 2, 3.
- `image_table(pets_dir)`: DataFrame cột `image_id`, `split` (`train`/`test` theo tệp), `height`, `width`, `mode` (PIL mode). Chỉ đọc cột `image` và `image_id`; lấy kích thước bằng `Image.open(...).size`, không cần decode cả ảnh.
- `join_report(trimaps, images)`: dict `matched` (số dòng ghép được theo `image_id`), `trimap_only`, `image_only`, `size_mismatch` (trong số ghép được, số cặp có `height` hoặc `width` khác nhau).
- `share_over(images, max_side)`: tỉ lệ ảnh có cạnh dài nhất **lớn hơn** `max_side` (float).
- `without_pet(trimaps)`: list `image_id` (sắp xếp) có tỉ lệ `pet` bằng 0.

Chạy các cell `explore` (tải dữ liệu nếu thiếu, in hồ sơ, vẽ `pets_profile.png`), rồi làm phần trắc nghiệm trong app. Test chạy trên dữ liệu nhỏ sinh trong test và trên dữ liệu thật (tự skip nếu chưa tải; khoảng 10 giây).

## Tiêu chí đạt

- Test pass trên dữ liệu sinh và trên dữ liệu thật (7 390 trimap, 7 349 ảnh).
- Tự kiểm (test không chạy cell `explore`): notebook chạy trọn vẹn, không lỗi.
- Chọn được giới hạn cạnh dài cho service từ phân phối kích thước và nói được bao nhiêu phần trăm ảnh của tập này bị từ chối với giới hạn đó.
- Trắc nghiệm đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`np.bincount(values.ravel(), minlength=4)` đếm pixel từng giá trị trong một lần. `pq.read_table(path, columns=["image", "image_id"]).column("image").to_pylist()` trả list dict có khoá `bytes`.

### Gợi ý 2

`trimaps.merge(images, on="image_id", suffixes=("_trimap", "_image"))` rồi so `height_trimap` với `height_image`. Tập hợp `set(a) - set(b)` cho phần không ghép được.
