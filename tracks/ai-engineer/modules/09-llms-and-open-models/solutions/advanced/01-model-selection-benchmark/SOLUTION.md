# Hướng làm: chọn model local bằng benchmark của chính bạn

Bài không có code lời giải chạy được: thí nghiệm và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân
nhắc, kết quả của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Mẫu | 30 câu mỗi chủ đề từ tập test, seed 0 (120 câu) | tập test lệch mạnh (72% "giảng viên"); mẫu cân bằng cho mỗi nhãn đủ câu để macro-F1 có nghĩa |
| Thước đo chính | macro-F1, kèm accuracy | accuracy trên dữ liệu lệch thưởng cho model đoán nhãn đa số; macro-F1 đặt 4 nhãn ngang nhau |
| Câu không đọc được | `None`, tính là sai, đếm ở cột riêng | bỏ chúng khỏi mẫu sẽ thưởng cho model hay trả lời lan man |
| Đọc nhãn | cụm từ nguyên vẹn, đúng một nhãn | model nhỏ hay chép lại cả danh sách nhãn; "nhãn đầu tiên tìm thấy" chấm những câu đó theo thứ tự nhãn trong prompt |
| Prompt | một system prompt mô tả từng nhãn bằng ví dụ từ khoá, dùng chung mọi model | so model chứ không so prompt; prompt riêng cho từng model là một thí nghiệm khác |
| Tham số sinh | `temperature` 0, `seed` 0, `num_predict` 24; HF: `do_sample=False`, `repetition_penalty=1.0` | tắt mọi mặc định ẩn (mục 5 lý thuyết) để model nào cũng giải mã greedy như nhau |
| `qwen2.5:7b` | `num_gpu` 14 (14 tầng trên GPU, 2.86 GB VRAM), 4 luồng CPU | giữ VRAM dưới 4 GB như laptop, và vì GPU của PC dùng chung |
| Biến thể cấu hình | `qwen2.5:3b` với `format` là JSON schema có `enum` 4 nhãn; `qwen2.5:3b` chỉ CPU | structured output là cách rẻ nhất để có output đọc được; CPU so với GPU đo nhiễu do phần cứng |
| Độ bất định | bootstrap theo cặp 2 000 lần cho hiệu macro-F1 | 120 câu: một câu là 0.008 accuracy; khoảng tin cậy cho biết chênh lệch có đáng tin không |
| Cache | mỗi cấu hình một tệp JSON, mỗi câu `reply`, `seconds`, `eval_count`, `eval_s` | đổi cách đọc nhãn hay thước đo không phải gọi model lại; độ trễ lưu lúc gọi, không đo lại khi đọc cache |

Lỗi hay gặp: so model trên tập test nguyên (macro-F1 bị nhãn "giảng viên" chi phối, accuracy của model luôn trả "giảng
viên" đã là 0.72); để `generate` dùng `generation_config.json` (repetition penalty 1.1, sampling) trong khi Ollama chạy
greedy; đo độ trễ có lẫn lần nạp model đầu tiên; parser lấy nhãn đầu tiên tìm thấy; kết luận từ chênh lệch 0.02 trên 120
câu.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB dùng chung, CPU giới hạn 4 luồng), Ollama 0.13.5, `transformers` 5.22.0, ngày 2026-10-31.
Prompt: system prompt liệt kê 4 nhãn, mỗi nhãn kèm vài từ khoá ("giảng viên: người dạy, cách dạy, thái độ, kiến thức
của giảng viên", ...), "Chỉ trả lời tên chủ đề, không giải thích."; user là `"Phản hồi: <câu>"`.

| Cấu hình | macro-F1 | Accuracy | Không đọc được | p50 / p95 (s) | Token/s | Bộ nhớ / VRAM (GB) |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5-0.5B (HF, CPU 4 luồng, float32) | 0.179 | 0.283 | 4 | 0.70 / 1.77 | 10 | 1.98 / 0 |
| `qwen2.5:3b` (hết trên GPU) | 0.600 | 0.608 | 0 | 0.38 / 0.42 | 129 | 2.39 / 2.39 |
| `qwen2.5:3b` + JSON schema | 0.663 | 0.683 | 0 | 0.78 / 0.97 | 129 | 2.39 / 2.39 |
| `qwen2.5:3b` (chỉ CPU, 4 luồng) | 0.624 | 0.633 | 0 | 1.25 / 2.21 | 18.5 | 2.07 / 0 |
| `qwen2.5:7b` (14 tầng GPU) | **0.782** | **0.783** | 0 | 1.25 / 1.88 | 14 | 5.37 / 2.86 |

Bootstrap theo cặp, 2 000 lần, khoảng tin cậy 95% của hiệu macro-F1:

| So sánh | Hiệu | Khoảng tin cậy | Số câu đổi nhãn |
| --- | --- | --- | --- |
| 3B + JSON schema so với 3B | +0.063 | [-0.012, 0.138] | 23 |
| 7B so với 3B + JSON schema | +0.119 | [0.041, 0.201] | 25 |
| 3B chỉ CPU so với 3B trên GPU | +0.024 | [-0.032, 0.084] | 12 |

Confusion matrix của `qwen2.5:3b`: 16/30 câu "cơ sở vật chất" bị gắn "chương trình đào tạo", 11/30 câu "khác" bị gắn
"giảng viên". `qwen2.5:7b` chỉ nhầm 3/30 câu cơ sở vật chất, nhưng vẫn gắn 9/30 câu "khác" thành "giảng viên". Qwen2.5-0.5B
gắn "chương trình đào tạo" cho 109/120 câu; 4 câu không đọc được nhãn, 3 trong đó là chép lại danh sách nhãn của system
prompt thay vì trả lời.

Đọc kết quả:

- **7B hơn rõ** (khoảng tin cậy không chứa 0), đổi lại chậm hơn 3 lần ở cấu hình nửa GPU và tốn gấp đôi bộ nhớ. Trên GPU
  đủ VRAM nó sẽ nhanh hơn nhiều (không đo ở đây để giữ VRAM dưới 4 GB).
- **JSON schema** cho 23 câu đổi nhãn và +0.06 macro-F1, nhưng khoảng tin cậy chứa 0: chưa đủ bằng chứng trên 120 câu.
  Nó gấp đôi độ trễ vì output JSON dài hơn một tên nhãn. Lợi ích chắc chắn của nó là định dạng, không phải độ chính xác.
- **Cùng model, cùng prompt, temperature 0, chỉ đổi GPU sang CPU**: 12/120 câu đổi nhãn, macro-F1 lệch 0.024. Đó là
  sàn nhiễu của benchmark này: mọi chênh lệch cỡ đó giữa hai model là không có nghĩa.
- **0.5B không dùng được** cho tác vụ này với zero-shot: gần như luôn trả một nhãn. Rẻ và nhanh không bù được.
- **Nhãn "khác" là điểm yếu chung**: câu như "năng động ." hay "sinh viên không hiểu lắm ." mơ hồ cả với người đọc;
  model kéo chúng về "giảng viên", nhãn chiếm 72% dữ liệu thật. Với lưu lượng thật (lệch về "giảng viên"), accuracy của
  mọi model sẽ cao hơn bảng trên, và lỗi ở "khác" ít ảnh hưởng hơn: báo cáo phải nói rõ con số nào áp cho phân phối nào.
- **Giấy phép**: `qwen2.5:3b` mang Qwen Research License (không thương mại), `qwen2.5:7b` Apache-2.0. Với sản phẩm
  thương mại, 3B bị loại trước khi xét chất lượng; một báo cáo không đọc `/api/show` sẽ bỏ sót điều này.

Khuyến nghị của bản tham chiếu: `qwen2.5:7b` nếu chấp nhận khoảng 1.3 giây một câu (xử lý theo lô, không cần tức thì)
hoặc có GPU 8 GB trở lên; nếu cần nhanh trên GPU 4 GB, `qwen2.5:3b` chỉ hợp cho nghiên cứu vì giấy phép, và lúc đó nên
cân nhắc fine-tune một model nhỏ giấy phép mở (module 14) hơn là cố thêm prompt.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Thiết lập công bằng | 20 | Cùng mẫu, cùng prompt, cùng tham số sinh tường minh (không để `generate` dùng mặc định ẩn), độ trễ không gồm lần nạp model, cache kết quả |
| Chất lượng và chi phí | 15 | Có đủ macro-F1, accuracy, không đọc được, p50/p95, token/s, bộ nhớ và VRAM cho mọi cấu hình, kể cả biến thể tự chọn |
| Diễn giải trung thực | 25 | Có khoảng tin cậy bootstrap theo cặp; không khuyên dựa trên chênh lệch trong mức nhiễu; nói được sàn nhiễu (vd. cùng model khác phần cứng) |
| Phân tích lỗi | 15 | Confusion matrix, ít nhất 5 câu sai đọc tận mắt, nguyên nhân có phân loại; nói về khác biệt giữa mẫu cân bằng và phân phối thật |
| Báo cáo | 10 | Khuyến nghị có số ở đầu, điều kiện phần cứng, giấy phép từng model, giới hạn |

Đạt từ 70 điểm. Báo cáo chọn model dựa trên một chênh lệch không có khoảng tin cậy, hoặc so model dùng prompt khác nhau
mà không nói, không quá 50 điểm.
