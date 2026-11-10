# Lời giải: vision LLM đọc hoá đơn

## Cách làm

- Sáu hàm của Basic 02 dán nguyên.
- `resize_for_vlm`: trả nguyên ảnh khi `max_side` là `None` hoặc cạnh dài đã nhỏ hơn; ngược lại `scale = max_side / max(size)`,
  `img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)`, tối thiểu 1 pixel.
- `encode_jpeg_b64`: `img.convert("RGB").save(buf, "JPEG", quality=quality)` (JPEG không có kênh alpha, RGBA phải chuyển
  trước), `base64.b64encode(...).decode("ascii")`.
- `vlm_messages`: message `user` có `images`, rồi `{"role": "assistant", "content": "{"}`.
- `parse_reply`: `strip`, bỏ khung ```` ``` ```` và chữ `json`, thêm `"{"` nếu thiếu, cắt tới `}` cuối, `json.loads` trong
  `try`, kiểm `dict` và `items` là list, lọc phần tử không phải dict.
- `ocr_lines`: dict `row_id -> [(tâm dọc, x1, text)]`, sắp dòng theo tâm dọc nhỏ nhất, word theo `x1`.

## Kết quả của lời giải mẫu

100 hoá đơn test của `cord-v2`, `qwen3-vl:2b` (Ollama 0.13.5, Q4_K_M), PC của track (RTX 3060, Ollama dùng chung với
tiến trình khác lúc đo). Log: `.superpowers/scratch/logs/exp_receipts_score.log` và output của notebook.

| Cấu hình | JSON hỏng | Tổng đúng | P dòng | R dòng | F1 dòng | SL đúng | Token prompt TB | Giây p50 | Giây p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VLM, ảnh gốc | 0 | 0.947 | 0.908 | 0.925 | 0.916 | 0.988 | 1 206 | 2.61 | 5.58 |
| VLM, cạnh dài 1024 | 0 | 0.968 | 0.877 | 0.910 | 0.893 | 0.971 | 712 | 1.95 | 4.39 |
| VLM, cạnh dài 768 | 0 | 0.926 | 0.835 | 0.891 | 0.862 | 0.958 | 488 | 1.65 | 3.63 |
| VLM, cạnh dài 512 | 1 | 0.895 | 0.646 | 0.733 | 0.687 | 0.923 | 290 | 1.54 | 4.00 |
| OCR từ nhãn + `qwen2.5:3b` (JSON schema) | 0 | 0.853 | 0.839 | 0.763 | 0.799 | 0.926 | 212 (chữ) | 9.63 | 23.47 |
| VLM chép chữ + `qwen2.5:3b` | 0 | 0.653 | 0.644 | 0.504 | 0.565 | 0.896 | 467 (chữ) | 9.39 | 35.34 |

Độ trễ của hai dòng `qwen2.5:3b` cao bất thường (khoảng 10 giây mỗi hoá đơn cho vài trăm token) vì lúc đo GPU bị chia với
tiến trình khác; so sánh độ chính xác vẫn dùng được. Pipeline VLM chép chữ cộng hai bước: trung vị 12.2 giây mỗi hoá đơn.

Đọc bảng:

- **Token tỉ lệ diện tích**: từ ảnh gốc xuống 512, token prompt giảm khoảng 4.2 lần (1 206 xuống 290); phần chữ của prompt
  luôn là 120 token, nên phần ảnh giảm khoảng 6.4 lần (1 086 xuống 170, tính bằng công thức Basic 03 trên kích thước thật). Từ ảnh gốc tới 768,
  F1 dòng hàng chỉ giảm 0.05; từ 768 xuống 512 nó rơi 0.18 (0.862 xuống 0.687): dưới một ngưỡng, chữ số nhỏ trên hoá đơn
  không còn đọc được. Cột tổng tiền bền hơn (chữ tổng thường to và đậm).
- **1024 so với ảnh gốc**: tổng đúng 0.968 so với 0.947 (2 hoá đơn), F1 0.893 so với 0.916 (khoảng 2 điểm): cả hai chênh
  lệch đều ở mức một hai hoá đơn, không đủ để nói cấu hình nào tốt hơn; 1024 rẻ hơn 41% token. Đây là cấu hình bài
  Advanced 01 dùng.
- **VLM end-to-end thắng pipeline OCR hoàn hảo** ở cả tổng đúng (0.968 so với 0.853 ở cấu hình 1024) và F1 dòng hàng (0.893 so
  với 0.799). Văn bản OCR dựng từ nhãn mất bố cục cột (tên món và tiền thường cùng dòng nhưng không phải lúc nào cũng vậy,
  món kèm nằm dòng riêng). Đọc 14 hoá đơn sai tổng của pipeline này: 9 trong số đó là `qwen2.5:3b` **viết lại** số tiền
dù prompt dặn giữ nguyên ("63.000" thành `63`, "93.500" thành `93.5`), số còn lại là lấy nhầm dòng (tạm tính, tiền khách
đưa). JSON schema bảo đảm `total` là chuỗi, không bảo đảm chuỗi đó là con số in trên giấy. Đây là cận trên của mọi pipeline OCR với
  **cùng** LLM và prompt; một LLM văn bản mạnh hơn sẽ đẩy cận trên lên.
- **VLM chép chữ rồi trích xuất** tệ nhất (F1 0.565) và chậm nhất: lỗi của bước chép chữ (bỏ dòng, gộp cột) cộng dồn với
  lỗi của bước trích xuất. Tách bước chỉ có lợi khi bước đầu là một OCR chuyên dụng tốt.
- Sai tổng ở ảnh gốc (5 hoá đơn): #4 model cộng lại các dòng (194 000) thay vì đọc tổng sau giảm giá (174 600); #59 đọc
  nhầm một chữ số (660 500 so với 680 500); #67 đọc "9,500,00" (định dạng lạ, `parse_amount` trả `None`); #71 đọc 200 200
  thay vì 198 000 (lẫn với tiền khách đưa); #95 đọc 62 000 (tổng đã làm tròn trên hoá đơn) so với nhãn 61 799. Ít nhất một
  trường hợp (#95) là tranh cãi về nhãn chứ không hẳn lỗi model: luôn đọc tận mắt trước khi kết luận.

## Đổi sang dữ liệu Việt Nam

Bộ là hoá đơn Indonesia. Trước khi dùng cho người Việt: đo lại trên MC-OCR (mục 2 lý thuyết), viết lại prompt bằng tiếng
Việt hoặc giữ tiếng Anh và đo cả hai, thêm trường người bán và thời điểm, và kiểm `parse_amount` với "đ", "VNĐ", "1.250.000đ".

## Bẫy thường gặp

- Gửi `format` (JSON schema) cho bản thinking: nội dung rỗng hoặc lời gọi chạy rất lâu.
- `json.loads` trên câu trả lời thiếu `{` đầu (phần model viết **tiếp** sau prefill).
- Lưu ảnh RGBA thành JPEG: Pillow báo lỗi.
- Ghép dòng OCR theo thứ tự trong `valid_line`: đó là thứ tự nhãn, không phải thứ tự trên giấy.
- Tính độ trễ khi đọc từ cache: luôn đo ở chỗ gọi model và lưu số đo vào cache cùng câu trả lời.
