# Lời giải: driver, CUDA và container toolkit

Lời giải ở `cuda_compat.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/01-cuda-compat -q
```

## Cách làm

1. **So phiên bản bằng tuple số nguyên.** `"580.9" > "580.65.06"` khi so chuỗi; `(580, 9) < (580, 65, 6)` khi so tuple.
   Mốc chỉ có nhánh (`"590"`) so tự nhiên: `(590,) <= (590, 44, 1)`.
2. **Hai bảng là hai hằng số dict**, không suy diễn: bảng 1 theo `X.Y`, bảng 2 theo major. `X.Y` không có trong bảng
   (12.7 chưa bao giờ phát hành, 10.2 ngoài phạm vi) là `ValueError`, không đoán "chắc giống 12.6".
3. **Driver xét theo thứ tự**: đạt mốc của đúng `X.Y` thì không có vấn đề; không đạt nhưng đạt mốc major thì
   `minor_version_compat` (cảnh báo: chạy được, không JIT PTX, tính năng mới có thể báo `cudaErrorCallRequiresNewerDriver`);
   không đạt cả hai thì `driver_too_old`. Thứ tự này quan trọng ở 11.x: mốc GA của 11.0 (450.51.05) **thấp hơn** mốc
   minor compatibility của cả major (450.80.02), nên kiểm mốc major trước sẽ báo sai `driver_too_old` cho tổ hợp 11.0 +
   450.51.05 vốn chạy đúng chuẩn.
4. **Card**: hai chiều độc lập. CUDA bỏ kiến trúc (`cuda_drops_gpu`: 12.x cần CC ≥ 5.0, 13.x cần ≥ 7.5) và driver bỏ kiến
   trúc (`driver_drops_gpu`: từ R495 bỏ Kepler, từ R590 bỏ CC < 7.5). K80 với driver 470 và CUDA 12.2 dính
   `driver_too_old` và `cuda_drops_gpu` cùng lúc: hai lý do, hai việc khác nhau.
5. **Toolkit**: CDI cần toolkit ≥ 1.12.0 và Docker ≥ 25.0; Docker 25–28.2 cần bật `features.cdi`, 28.3.0 trở đi bật sẵn.
   Phiên bản Docker chỉ xét khi đi đường CDI (`--gpus` chạy từ Docker 19.03). Toolkit < 1.19.1 là cảnh báo bảo mật, không
   phải lỗi tương thích: máy vẫn chạy, nhưng báo cáo phải có dòng đó (CVE-2024-0132, CVE-2025-23266, CVE-2026-24260 đều
   là thoát container).

## Đọc kết quả cho khách

`compatible` chỉ là bước đầu. Một máy `compatible` với `minor_version_compat` + `toolkit_cve` nghĩa là "chạy được hôm nay,
cần lên kế hoạch nâng toolkit ngay và nâng driver ở đợt bảo trì sau". Viết `detail` như câu bạn sẽ đọc cho IT khách:
có mốc phiên bản cụ thể, không viết "driver cũ".

Bảng ghim theo tài liệu ngày 2026-11-11. Khi NVIDIA ra CUDA mới, cập nhật bảng (và test) chứ không nới quy tắc: một công
cụ tương thích "đoán" là tệ hơn không có công cụ.
