# Lời giải: đếm token tiếng Việt và tiếng Anh

## Cách làm

- **`detokenize`**: `html.unescape`, rồi ba `re.sub` theo đúng thứ tự: `\s+([,.!?;:%)\]])` thành `\1`, `([(\[$])\s+`
  thành `\1`, `\s+'(?=[A-Za-z])` thành `'`; cuối cùng `" ".join(s.split())`. Lookahead giữ chữ cái sau dấu nháy, và
  vì chỉ chấp nhận `A-Za-z` nên `' tự` (dấu nháy mở trích dẫn trong tiếng Việt) không bị dính vào chữ trước.
- **`token_stats`**: ba tổng (`len(t)`, `len(t.split())`, `len(encode(t))`) rồi hai tỉ lệ, mẫu số 0 thì `0.0`.
- **`token_tax`**: tỉ lệ của **tổng**. Trung bình tỉ lệ từng cặp cho câu ngắn trọng số ngang câu dài: câu tiếng Anh
  "OK." một token dịch thành "Được rồi." ba token đóng góp tỉ lệ 3 vào trung bình như một câu 40 token. Hoá đơn tính
  theo tổng, nên chỉ số đúng là tỉ lệ tổng.
- **`truncate_to_budget`**: cộng dồn, `break` ở đoạn đầu tiên làm vượt.

## Kết quả trên tst2013 (1 268 cặp câu)

| Cách đếm | Token en | Token vi | vi/en | Token mỗi từ (vi) | Ký tự mỗi token (vi) |
| --- | --- | --- | --- | --- | --- |
| ký tự | 123 769 | 133 496 | 1.079 | 4.333 | 1.000 |
| byte UTF-8 | 123 800 | 178 601 | 1.443 | 5.797 | 0.747 |
| từ (split) | 23 093 | 30 809 | 1.334 | 1.000 | 4.333 |
| `cl100k_base` | 27 842 | 67 320 | 2.418 | 2.185 | 1.983 |
| `o200k_base` | 27 312 | 39 078 | 1.431 | 1.268 | 3.416 |
| Qwen2.5 | 28 088 | 38 298 | 1.364 | 1.243 | 3.486 |

Trung vị tỉ lệ từng cặp: 2.40 với `cl100k_base`, 1.43 với `o200k_base`. Ngân sách 3 000 token chứa được 57 câu tiếng
Việt với `cl100k_base`, 99 với `o200k_base`, 103 với Qwen2.5; bản tiếng Anh 142 câu với `cl100k_base` và Qwen2.5, 147
câu với `o200k_base`. Mỗi token tiếng Anh của `o200k_base` chứa trung bình 4.53 ký tự (`cl100k_base` 4.45, Qwen2.5 4.41).

Trả lời câu hỏi cuối notebook:

- **Ký tự**: bản Việt chỉ dài hơn 7.9%. Phần chênh còn lại là **của tokenizer**: với `cl100k_base`, phần lớn âm tiết có
  dấu bị chặt thành 2 tới 3 mảnh (mỗi token chỉ chứa 1.98 ký tự, gần như chặt theo ký tự); với `o200k_base` và Qwen2.5,
  từ vựng 200 nghìn và 151 nghìn token đã học đủ âm tiết tiếng Việt nên mỗi token chứa khoảng 3.4 tới 3.5 ký tự, gần
  một âm tiết. Tiếng Anh gần như không đổi giữa ba tokenizer (27 312 tới 28 088): tokenizer cũ vốn đã tốt cho tiếng Anh.
- **Từ theo khoảng trắng**: tiếng Việt viết cách giữa các **âm tiết**, không giữa các từ ("thế giới" là một từ hai âm
  tiết), nên "từ" theo khoảng trắng thực chất là âm tiết. Muốn đếm từ thật cần công cụ tách từ (word segmentation),
  module 04.
- **So giá**: với văn bản như tst2013, model A tốn 67 320 / 39 078 = 1.72 lần số token của model B, nên A thực tế tốn
  $$1.72 \times 1 = 1.72$$ đơn vị so với $$1.5$$ của B: **B rẻ hơn khoảng 13%** dù giá niêm yết cao hơn 50%. So giá phải so
  chi phí mỗi tác vụ trên văn bản thật.
- **Ghép bằng `"\n"`**: prompt ghép 103 câu cho 2 979 token Qwen2.5, khác tổng từng câu một chút vì BPE có thể gộp ký tự
  ở ranh giới (khoảng trắng, xuống dòng) với token bên cạnh khác khi đếm riêng, và mỗi `"\n"` có thể là một token. Đếm
  ngân sách thật thì đếm trên chuỗi cuối cùng gửi đi.

## Bẫy thường gặp

- Đếm trên văn bản còn tách từ và entity: `&apos;` là 6 ký tự, làm số token tiếng Anh phình lên (491 dấu nháy trong
  tst2013 tiếng Anh).
- Dùng `split(" ")`: hai dấu cách liền nhau sinh ra "từ" rỗng.
- Lấy "token ≈ 4 ký tự" (quy tắc nhẩm cho tiếng Anh) áp vào tiếng Việt: với `cl100k_base` lệch hơn gấp đôi.
- Quên context window chứa cả output: prompt 3 500 token cộng 1 000 token trả lời vượt 4 096; tuỳ hệ thống, request bị
  từ chối, câu trả lời bị cắt giữa chừng, hoặc (Ollama) đầu prompt bị cắt mà không báo lỗi.
