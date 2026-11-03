# Lời giải: pipeline hai stage

Xem `dvc.yaml`. Ba điểm quyết định:

1. **`deps` gồm cả script.** Nếu thiếu `prepare.py` trong `deps`, sửa logic lọc mà `dvc repro` vẫn bỏ qua stage (bài sự cố của module này).
2. **Đồ thị suy ra từ tệp, không từ thứ tự khai báo.** `data/clean.csv` là `outs` của `prepare` và `deps` của `split`; DVC nối hai stage
   theo đường dẫn. Đảo thứ tự hai khối trong YAML vẫn chạy đúng.
3. **`params:` theo từng khoá.** `split.test_size` đổi thì chỉ `split` có hash đầu vào khác. Nếu ghi `params.yaml` vào `deps`, mọi thay
   đổi nhỏ nhất trong tệp đó làm cả pipeline chạy lại.

`dvc repro` so hash `cmd` + `deps` + `params` với `dvc.lock`. `dvc.lock` là hợp đồng tái lập: nó ghi md5 của từng dep và out ở lần chạy cuối,
nên commit nó cùng code thì ai checkout cũng dựng lại đúng cùng dữ liệu. Với `outs`, DVC tự thêm vào `.gitignore`.
