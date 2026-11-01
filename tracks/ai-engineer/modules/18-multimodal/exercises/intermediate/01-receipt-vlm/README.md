---
title: Vision LLM đọc hoá đơn thành JSON, đo từng trường và so với OCR
level: intermediate
services: []
files:
  - path: starter/receipts.ipynb
    note: 6 hàm dán từ Basic 02, 5 hàm TODO
  - path: tests/test_receipts.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cord-v2
  - ollama pull qwen3-vl:2b
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/01-receipt-vlm/starter/receipts.ipynb
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/intermediate/01-receipt-vlm -q
---

## Mục tiêu

Dùng một vision LLM 2B chạy local để đọc hoá đơn thành JSON có cấu trúc, và **đo** nó như một hệ thống thật: độ đúng
của tổng tiền và từng dòng hàng theo bộ chấm tất định, số token ảnh và độ trễ theo độ phân giải, và so với pipeline hai
bước OCR rồi LLM văn bản. Đây là khối đầu tiên của trợ lý tài chính ở bài Advanced 01.

## Đề bài

**Phần cứng:** GPU 4GB · ~90 phút

Thời gian trên là thời gian làm bài. Cell `explore` gọi model khoảng 700 lần; trên PC của track (RTX 3060, Ollama dùng
chung với một tiến trình khác) toàn bộ mất khoảng 25 phút, phần lớn ở bước VLM chép chữ. `qwen3-vl:2b` chiếm khoảng
3.1 GiB khi nạp lên GPU, vừa GPU 4GB của laptop nếu không có chương trình nào khác dùng GPU. Chỉ có CPU: một ảnh
1280×960 mất khoảng 3.5 phút với 4 luồng (mục 2 lý thuyết); đặt `N_RECEIPTS = 20`, chỉ chạy `MAX_SIDES = [768]`, bỏ bước
VLM chép chữ.

**Về dữ liệu.** Đề bài portfolio của track là hoá đơn Việt Nam (MC-OCR 2021), bộ này cần đăng ký với ban tổ chức. Người
học đã đồng ý (2026-11-02) dùng `cord-v2` (hoá đơn bán lẻ Indonesia, CC BY 4.0) thay thế: cùng định dạng số tiền dấu
chấm phân cách nghìn, có nhãn tới từng dòng hàng. Đổi sang MC-OCR: xem mục 2 lý thuyết.

Mở `starter/receipts.ipynb`. Trong cell chấm điểm:

1. Dán sáu hàm của bài Basic 02.
2. `resize_for_vlm`, `encode_jpeg_b64`, `vlm_messages` (message Ollama có **prefill** `"{"`), `parse_reply`, `ocr_lines`
   theo mô tả trong notebook.

Rồi chạy các cell `explore`:

- VLM đọc 100 hoá đơn test ở bốn mức cạnh dài (ảnh gốc, 1024, 768, 512 pixel); bảng: JSON hỏng, tổng đúng, precision,
  recall, F1 dòng hàng, số lượng đúng, token trung bình, độ trễ p50 và p95.
- Pipeline hai bước: (a) văn bản OCR từ nhãn (OCR hoàn hảo) rồi `qwen2.5:3b` với JSON schema; (b) VLM chép chữ rồi
  `qwen2.5:3b`. Cùng bảng.
- Đọc tận mắt các hoá đơn sai tổng.

Sau đó làm phần trắc nghiệm của bài trong app. Câu trả lời của model có thể lệch nhẹ giữa các máy và phiên bản Ollama;
các câu trắc nghiệm số liệu chỉ hỏi về thứ tự và khoảng.

## Tiêu chí đạt

- Sáu hàm dán từ Basic 02 qua kiểm tra nhanh.
- `resize_for_vlm` giữ tỉ lệ, không phóng to; `encode_jpeg_b64` cho JPEG base64 mở lại được, kể cả ảnh RGBA.
- `vlm_messages` đúng hai message, message cuối là prefill `"{"` của `assistant`.
- `parse_reply` đọc được phần model viết sau prefill, có hoặc không có khung ```` ``` ````, bỏ phần tử không phải dict;
  trả `None` cho câu trả lời không phải JSON, JSON cụt, `items` không phải list.
- `ocr_lines` dựng lại dòng theo vị trí dọc, word theo vị trí ngang, không theo thứ tự trong file hay `row_id`.
- Cell `explore` chạy hết và in hai bảng.

## Gợi ý

### Gợi ý 1

`Image.resize((w, h), Image.LANCZOS)` với `w, h` tính từ `scale = max_side / max(img.size)`. Với `parse_reply`, in thử
`repr()` vài câu trả lời thật trong file cache trước khi viết: phần lớn bắt đầu bằng dấu cách và `"items"`, vì model viết
tiếp sau `{`.

### Gợi ý 2

`ocr_lines`: một dict `row_id -> list[(tâm_dọc, x1, text)]`, rồi `sorted(dict.values(), key=...)`. Thứ tự của
`valid_line` trong file theo **nhãn** (tên món, giá, tổng...), không theo vị trí trên hoá đơn.
