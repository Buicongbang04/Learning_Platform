# Lời giải: Ollama qua REST API thô

## Cách làm

**`chat_payload`** dựng ba khoá bắt buộc, gom sáu option vào một dict rồi lọc `v is not None`. Lọc bằng truthiness
(`if v`) là lỗi phổ biến nhất của bài: `temperature=0` (greedy) và `keep_alive=0` (giải phóng model ngay) bị bỏ âm
thầm, server dùng mặc định (`temperature` 0.8) và bạn không biết. `keep_alive` và `format` nằm ở cấp ngoài vì Ollama
đọc chúng ở đó, không phải trong `options`.

**`parse_stream`** giải mã `bytes` sang `str`, bỏ dòng trắng, `json.loads` từng dòng, ném `RuntimeError` khi gặp khoá
`error` (Ollama gửi lỗi giữa stream dưới dạng một dòng JSON, HTTP status đã là 200 từ trước), nối `message.content`, và
trả ngay khi gặp `done: true`. Hết dòng mà chưa có `done` nghĩa là kết nối đứt giữa chừng: báo lỗi thay vì trả một câu
trả lời cụt như thể nó hoàn chỉnh.

**`speed_stats`** chia nano giây cho `1e9`, dùng `.get(..., 0)` cho mọi trường và trả `0.0` khi thời gian bằng 0.

**`model_facts`** đọc kiến trúc trước rồi dựng khoá `f"{arch}.context_length"`: khoá context khác nhau theo kiến trúc
(`qwen2.context_length`, `llama.context_length`, `gemma3.context_length`). Giấy phép lấy `general.license.name` trước,
rồi `general.license`: GGUF ghi `"other"` ở khoá thứ hai cho mọi giấy phép không chuẩn, tên thật nằm ở khoá thứ nhất.

**`render_modelfile`** ghép từng dòng, list thành nhiều dòng `PARAMETER` cùng tên, mỗi dòng kết thúc bằng `\n`.

## Kết quả thật

PC của track, Ollama 0.13.5, `qwen2.5:3b` nằm hết trên RTX 3060 (GPU dùng chung với việc khác). Cả notebook chạy
khoảng 20 giây khi model đã có trong page cache; lần đầu sau khi khởi động máy, riêng việc nạp model mất 64 giây.

| Số đo | Giá trị |
| --- | --- |
| Nạp model (đã ở page cache) | 2.1 tới 2.4 s |
| Stream 64 token: TTFT / tổng | khoảng 0.3 s / 1.0 s |
| Đọc prompt 48 token / sinh | khoảng 2 000 / 130 token/s |
| `/api/ps` | 2.39 GB, hết trên GPU, `context_length` 4 096 |
| Prompt dài 20 466 ký tự, `num_ctx` mặc định | `prompt_eval_count` 4 096, trả lời `'5'`, sai, 1.4 s |
| Cùng prompt, `num_ctx` 8 192 | `prompt_eval_count` 7 650, trả lời `'7429'`, đúng, 5.1 s (2.9 s là nạp lại model) |
| Đọc prompt dài | khoảng 3 700 tới 4 100 token/s |

Bốn lần gọi lại `/api/chat` với `temperature` 0, `seed` 42 cho cùng một chuỗi với nhau nhưng **khác** lần stream đầu
tiên; `llmkit.chat` khớp các lần gọi lại; `/v1/chat/completions` cho câu thứ ba. Gọi cùng request qua Ollama SDK
(`ollama.Client.chat`, cả không stream lẫn stream) cho đúng cùng `prompt_eval_count` 48, `eval_count` 41,
`done_reason` `"stop"` và cùng câu trả lời với lần gọi REST ngay trước đó: SDK chỉ là lớp mỏng trên `/api/chat`, đổi
dict sang object có thuộc tính và parse NDJSON giúp bạn. Model con `ae09-tro-ly` trả lời "Hugging
Face là gì?" bằng tiếng Trung và "Ollama là gì?" bằng `'Ollama: Không rõ ý định cụ thể.'`.

## Đọc kết quả

- **TTFT**: không stream, người dùng nhìn màn hình trống cả câu trả lời (khoảng 1 giây ở đây, hàng chục giây với câu dài
  hay máy chậm); stream thì chữ đầu hiện sau khoảng 0.3 giây. Lần gọi đầu sau khi model hết `keep_alive` còn cộng thời
  gian nạp: 2 giây khi tệp đã ở page cache, cả phút khi đọc đĩa lạnh.
- **Prefill nhanh hơn decode khoảng 30 lần** với prompt dài. Prompt 48 token đo được tốc độ thấp hơn vì phần cố định
  của mỗi lời gọi chiếm phần lớn thời gian: đo tốc độ prompt bằng prompt dài.
- **Bẫy `num_ctx`**: response sai có HTTP 200, `done_reason` `"stop"`. Prompt thật 7 650 token, chỉ 4 096 được đọc;
  Ollama giữ phần cuối (có câu hỏi) và bỏ phần đầu (có dữ kiện). Đặt `num_ctx` theo độ dài thật và kiểm
  `prompt_eval_count`. Đổi `num_ctx` làm nạp lại model: thấy ngay ở `load_s` 2.9 s của lời gọi 8 192.
- **Không tất định ở temperature 0**: xem câu phỏng vấn tương ứng. Test và eval không được giả định gọi lại sẽ ra cùng
  chuỗi.
- **Modelfile không thêm năng lực**: system prompt "trợ lý tiếng Việt" không ngăn model 3B trả lời bằng tiếng Trung, và
  ép trả lời một câu ngắn về thứ model không chắc sinh ra câu bịa.

Lỗi hay gặp: lọc option bằng truthiness; quên `ensure_ascii` không ảnh hưởng (httpx tự mã hoá UTF-8) nhưng tự ghép
JSON bằng chuỗi thì có; đọc `general.license` và kết luận "giấy phép khác, chắc là mở"; tạo model con rồi xoá mà không
giải phóng nó khỏi bộ nhớ (`keep_alive: 0`), để lại 2.4 GB VRAM dưới một cái tên không còn tồn tại.
