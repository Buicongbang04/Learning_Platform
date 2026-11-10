# Lời giải: vòng sinh token và KV cache với Qwen2.5-0.5B

## Cách làm

**`decode`** giữ hai danh sách: `ids` (prompt cộng token đã sinh, đưa cho model) và `out` (chỉ token đã sinh, trả về).
Mỗi bước gọi `next_logits(list(ids))`, chọn bằng `pick(logits, list(out))` **trước** khi thêm token mới, ép `int(...)`
(hàm chọn có thể trả `np.int64`), thêm vào cả hai danh sách, rồi `break` nếu token thuộc `eos_ids`. Chép `prompt_ids`
thành list mới ngay đầu hàm, nên prompt của người gọi không bị sửa và tuple cũng dùng được.

**`hf_next_logits`** là closure quanh model: tạo tensor `torch.long` shape `(1, n)`, gọi model trong `torch.no_grad()`,
lấy `out.logits[0, -1]`, đổi `.float().numpy()`. `import torch` nằm trong hàm để import notebook (và chạy test) không
kéo torch khi chưa cần.

**`cached_next_logits`** giữ `seen` (chuỗi đã đưa vào model) và `past` (cache của chuỗi đó), sửa bằng `nonlocal`:

- chuỗi mới dài hơn và bắt đầu đúng bằng `seen`: chỉ đưa phần đuôi `ids[len(seen):]` kèm `past_key_values=past`;
- ngược lại (lần đầu, chuỗi khác, hoặc chuỗi bằng hệt `seen` nên không còn token mới): chạy lại cả chuỗi với
  `past_key_values=None`;
- luôn `use_cache=True` và lưu `seen = ids`, `past = out.past_key_values` sau mỗi lần gọi.

Điều kiện "dài hơn" quan trọng: gọi lại đúng chuỗi cũ thì không có token mới để đưa vào, và cache cũ đã chứa vị trí
cuối nên không lấy lại được logits của nó.

**`fertility`** là tổng token chia tổng từ, **không** phải trung bình tỉ lệ của từng câu: câu ngắn sẽ có trọng số quá
lớn nếu lấy trung bình tỉ lệ. **`distinct_n`** tạo n-gram trong từng văn bản rồi gộp, nên không có n-gram nối qua ranh
giới hai câu trả lời.

## Kết quả thật

PC của track, `torch` 2.14.1+cpu, 4 luồng (`taskset` lên 12 nhân, `OMP_NUM_THREADS=4`), model float32. Cả notebook
chạy khoảng 3 phút khi model đã có trong cache Hugging Face (lần đầu cộng thời gian tải khoảng 1 GB).

| Cách greedy (câu hỏi thủ đô, prompt 46 token) | Token | Token/s | Kết quả |
| --- | --- | --- | --- |
| `decode` không cache | 13 | 3.8 | "Thủ đô của Việt Nam là thành phố Hà Nội." |
| `decode` có KV cache | 13 | 13.9 | giống hệt |
| `generate`, `repetition_penalty=1.0` | 13 | 14.4 | giống hệt |
| `generate` mặc định | 11 | 13.9 | "Thủ đô của Việt Nam là Hà Nội." |

| Chuỗi đã có | Không cache, ms/bước | Có cache, ms/bước |
| --- | --- | --- |
| 64 | 302 | 62 |
| 256 | 842 | 65 |
| 1 024 | 3 480 | 68 |

Phân phối token đầu: `'Th'` 0.952, `'Tr'` 0.021, `'The'` 0.008; top-20 chiếm 0.9945; entropy 0.322 nat.

Distinct-n (8 câu, top-p 0.9, 40 token, seed 0) và fertility trên 1 268 cặp câu: như bảng ở mục 4 và 5 lý thuyết.
Tổng token: Qwen2.5 en 28 091, vi 38 298; Phi-3 en 30 964, vi 90 749; `cl100k_base` vi 67 319; `o200k_base` vi
39 077. Distinct-n và fertility ra **đúng cùng số** trên laptop RTX 3050 và PC: sinh có seed ghim trên CPU và đếm token
là tái lập được; thời gian thì không.

## Đọc kết quả

- **Vòng của bạn đúng bằng `generate` khi tắt penalty**: không có phép màu trong `generate`, chỉ là vòng lặp này cộng
  các logits processor đọc từ `generation_config.json`. Bản mặc định khác vì repetition penalty 1.1 phạt cả token của
  **prompt**: "thành phố" có trong câu hỏi nên bị đẩy xuống.
- **KV cache**: ở 1 024 token, cache nhanh hơn khoảng 50 lần. Bước có cache gần như hằng số vì nó bị chặn bởi việc
  đọc 1.84 GiB trọng số mỗi bước (khoảng 30 GiB/s), không phải bởi độ dài chuỗi, cho tới khi chuỗi đủ dài để attention
  trên cache chiếm phần đáng kể.
- **Model rất chắc ở bước đầu**: top-p 0.9 chỉ giữ 1 token. Temperature chỉ tạo khác biệt ở các bước model phân vân,
  như câu mở đầu truyện ngắn.
- **Fertility là chi phí**: cùng nội dung, tiếng Việt qua tokenizer 32k tốn gấp 2.4 lần Qwen2.5. Với API tính theo
  token, chọn model có tokenizer tốt cho tiếng Việt là giảm chi phí và tăng context dùng được cùng lúc.

Lỗi hay gặp: `pick` nhận `out` sau khi đã thêm token mới (lệch một bước); quên `int(...)` nên kết quả là `np.int64`;
cache không kiểm điều kiện nối tiếp nên dùng cache của prompt cũ cho prompt mới (logits sai mà không lỗi); so vòng tự
viết với `generate` mặc định rồi kết luận vòng tự viết sai.
