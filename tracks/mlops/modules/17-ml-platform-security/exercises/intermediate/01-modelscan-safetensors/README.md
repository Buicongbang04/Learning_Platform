---
title: Pickle, safetensors và modelscan - cổng nhận model theo allowlist
level: intermediate
services: []
files:
  - path: starter/model_io.py
    note: 4 hàm TODO
  - path: tests/test_model_io.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/01-modelscan-safetensors -q
---

## Mục tiêu

Thấy tận mắt vì sao nạp một tệp pickle là chạy code của người tạo ra nó, lưu model ở định dạng không chứa code (safetensors), và viết
cổng nhận model kết hợp hai lớp: **allowlist định dạng theo nội dung tệp** và **quét bằng modelscan**. Bạn cũng thấy giới hạn của máy quét:
nó dò theo danh sách chặn và theo đuôi tệp, nên chỉ một mình nó thì không đủ.

## Đề bài

Cần Docker: test chạy `modelscan` 0.8.8 trong container không mạng, mount chỉ đọc (`mlopskit.modelscan_run`); lần đầu build image
`mlops-modelscan:0.8.8` (xem module README mục 0).

**An toàn khi làm bài.** Pickle "độc hại" của test (`seckit.py` ở thư mục module) đã được vô hại hoá: nạp vào chỉ ghi chữ `pwned` vào một
tệp đánh dấu trong thư mục tạm của test, không gọi lệnh hệ thống, không dùng mạng. Test **không bao giờ** nạp tệp model, trừ đúng một ca
`test_loading_a_pickle_runs_code` cố ý nạp trong thư mục tạm để chứng minh rủi ro. Code của bạn cũng **không được** nạp pickle
(`pickle.load`, `joblib.load`, `torch.load`...) để kiểm tra: test kiểm tệp đánh dấu không xuất hiện sau mỗi lần gọi cổng.

Điền 4 hàm trong `starter/model_io.py`:

1. `export_linear(model, path)`: lưu `coef_` và `intercept_` của model tuyến tính sklearn (đã fit) thành tệp safetensors có hai tensor
   `coef`, `intercept` và metadata `format = "linear"`.
2. `load_linear(path)`: trả hàm `predict(X)` cho kết quả bằng `model.predict(X)` (test dùng Ridge trên bộ diabetes của sklearn), chỉ
   đọc safetensors, không cần pickle.
3. `file_formats(model_dir)`: dict `{đường dẫn tương đối dạng posix: loại}` cho **mọi tệp** trong thư mục (kể cả thư mục con), loại xác
   định **theo nội dung**, không theo đuôi:
   - `symlink`: đường dẫn là symlink (không đọc, không đi theo);
   - `safetensors`: 8 byte đầu là số nguyên little-endian `n > 0`, `8 + n` không vượt kích thước tệp, và `n` byte tiếp theo là JSON object;
   - `json`: cả tệp là JSON hợp lệ (UTF-8);
   - `pickle`: byte đầu `0x80` và byte thứ hai là protocol 2 đến 5;
   - `other`: còn lại. Kiểm theo thứ tự trên.
4. `gate(model_dir, scan, allow_pickle=False)` trả `{"allowed": bool, "reasons": [...]}`, `reasons` đã sắp xếp, `allowed` đúng khi
   `reasons` rỗng. `scan(model_dir)` gọi **đúng một lần** trên thư mục model, trả `CompletedProcess` của modelscan (`returncode`, `stdout`
   là báo cáo JSON; test truyền `mlopskit.modelscan_run` hoặc bản giả). Mã lý do:

| Mã | Khi nào |
| --- | --- |
| `empty` | thư mục không có tệp nào |
| `format:<tệp>` | loại của tệp không thuộc allowlist: `safetensors`, `json`, thêm `pickle` khi `allow_pickle=True` |
| `scan-issue:<module>.<operator>` | báo cáo có issue mức `MEDIUM`, `HIGH` hoặc `CRITICAL` (mỗi cặp một lần); issue `LOW` không chặn |
| `scan-error` | quét không tin được: `returncode` không thuộc 0, 1, 3; `stdout` không phải JSON object; danh sách `errors` khác rỗng; hoặc `returncode` 1 mà không có issue nào |
| `unscanned:<tệp>` | chỉ khi `allow_pickle=True` và quét không lỗi: tệp loại `pickle` không có trong `summary.scanned.scanned_files` của báo cáo |

Mã thoát của modelscan: 0 sạch, 1 có issue, 2 lỗi, 3 không có gì để quét (thư mục chỉ có safetensors và JSON trả 3: hợp lệ), 4 không hỗ
trợ. `allow_pickle=True` là đường cho model cũ đang chuyển dần sang safetensors: pickle được nhận **chỉ khi** modelscan thật sự đã đọc nó
và không thấy gì.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/01-modelscan-safetensors -q` pass.
- Bạn giải thích được ba ca test: payload qua mặt modelscan nhưng bị allowlist chặn; pickle đặt tên `model.safetensors` mà modelscan
  báo "không có gì để quét"; pickle đặt đuôi `.bin` không được quét.
- Bạn nêu được vì sao cổng phải **fail closed** khi máy quét lỗi, và vì sao safetensors an toàn hơn về bản chất chứ không phải vì "đã quét".

## Gợi ý

### Gợi ý 1

`safetensors.numpy.save_file(tensors, path, metadata={...})` và `load_file(path)`. Đầu tệp safetensors: `struct.unpack("<Q", data[:8])`.

### Gợi ý 2

Viết một hàm nhỏ đọc báo cáo modelscan, trả "tin được hay không", danh sách issue chặn, và tập `scanned_files`. `gate` chỉ còn ghép kết
quả của `file_formats` với hàm này.
