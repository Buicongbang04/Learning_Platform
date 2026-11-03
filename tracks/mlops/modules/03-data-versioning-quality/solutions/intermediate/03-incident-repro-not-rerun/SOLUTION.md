# Lời giải: dvc repro không chạy lại

**Nguyên nhân.** `dvc.yaml` chỉ khai `data/raw/trips.csv` trong `deps`. DVC không đọc code của bạn để đoán stage cần gì: nó chỉ
băm những gì được liệt kê. `prepare.py` và `prepare.min_distance` đều bị bỏ sót, nên hash đầu vào không đổi khi bạn sửa chúng,
và `dvc.lock` vẫn khớp. Đây là lỗi im lặng nguy hiểm: pipeline "xanh" nhưng dữ liệu cũ.

**Cách chẩn đoán.**

1. `dvc status` báo up to date sau khi sửa script: manh mối đầu tiên.
2. Mở `dvc.lock`: phần `deps` của stage chỉ có một dòng. Mọi tệp stage đọc phải xuất hiện ở đó.
3. `strace -f -e openat dvc repro` hoặc đọc code script để liệt kê tệp thật sự được mở.

**Cách sửa** (xem `dvc.yaml`): thêm `prepare.py` vào `deps` và `prepare.min_distance` vào `params`. Không thêm cả `params.yaml` vào `deps`,
vì khi đó đổi `train.seed` cũng chạy lại `prepare`; tiêu chí cuối của đề kiểm điều này.

**Phòng ngừa.** Dùng `dvc stage add -d ... -p ...` thay vì viết tay, thêm một test CI kiểu "sửa script rồi `dvc repro --dry`
phải báo stage cần chạy", và chạy `dvc repro` ở CI trên repo sạch để phát hiện stage chỉ chạy được nhờ tệp có sẵn trên máy bạn.
