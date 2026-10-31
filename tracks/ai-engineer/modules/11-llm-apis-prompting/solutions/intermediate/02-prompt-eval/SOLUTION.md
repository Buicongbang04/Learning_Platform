# Lời giải: đánh giá prompt có số đo

## Cách làm

- `build_messages`: một message `user` chung `"Phản hồi: <câu>"`; `zero_shot`, `cot`, `json_schema` chỉ khác phần đuôi
  của system (`ONE_WORD`, `COT`, `JSON_INSTR`); `few_shot` chèn mỗi ví dụ thành cặp lượt `user`/`assistant` giữa
  system và câu hỏi.
- `parse_label`: một từ thì gom các từ Latinh là nhãn vào `set`, đúng một phần tử mới nhận; CoT dùng
  `re.compile(r"nhãn\s*:[\s*`]*(negative|neutral|positive)", re.IGNORECASE)` và lấy lần khớp cuối; JSON thì
  `json.loads` trong `try`, kiểm là dict và `label` thuộc `LABELS`.
- `macro_f1`: F1 từng nhãn là $$\frac{2\,TP}{2\,TP + FP + FN}$$, nhãn không có TP thì 0, lấy trung bình.
- `paired_bootstrap`: đúng thứ tự mô tả: `default_rng(seed)`, mỗi vòng một `idx` dùng cho cả A và B, phân vị 2.5 và
  97.5.

## Vì sao các lựa chọn này

- **Ví dụ few-shot là các lượt hội thoại** (user hỏi, assistant trả nhãn), không phải một khối chữ trong system: model
  chat đã được SFT trên đúng dạng đó, và lượt assistant trong ví dụ dạy luôn **định dạng** câu trả lời.
- **Parser khắt khe**: "positive hoặc negative" là `None`, không phải nhãn đầu tiên. Parser dễ dãi thưởng cho model
  trả lời lan man theo thứ tự nhãn trong prompt (module 09 Advanced 01 gặp đúng lỗi này). Đếm `None` như một cột riêng.
- **Bootstrap theo cặp**: hai biến thể chạy trên **cùng** 150 câu. Câu khó thì khó với cả hai; lấy mẫu lại cùng chỉ
  số giữ được tương quan đó, nên khoảng tin cậy của **hiệu** hẹp hơn nhiều so với so hai khoảng tin cậy riêng lẻ (hai
  khoảng chồng nhau không có nghĩa là hiệu không có ý nghĩa).
- **Gọi REST thay vì `llmkit.chat`**: cần `num_predict`, `seed` và các trường `prompt_eval_count`, `eval_count` để báo
  token. `llmkit` giấu chúng để giữ giao diện chung cho mọi nhà cung cấp.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB dùng chung với một job train khác, Ollama 0.13.5, `qwen2.5:3b`, `temperature` 0, `seed` 0),
ngày 2026-11-01, 150 câu ghim:

| Biến thể | macro-F1 | CI 95% | Accuracy | p50 giây | Token vào | Token ra |
| --- | --- | --- | --- | --- | --- | --- |
| zero-shot | 0.804 | [0.732, 0.864] | 0.807 | 0.12 | 131 | 2.0 |
| few-shot (6 ví dụ) | 0.740 | [0.666, 0.808] | 0.773 | 0.33 | 284 | 2.0 |
| CoT-lite | 0.823 | [0.755, 0.879] | 0.827 | 1.86 | 180 | 53.5 |
| JSON schema | 0.852 | [0.791, 0.906] | 0.853 | 0.81 | 129 | 8.6 |

So với zero-shot (bootstrap theo cặp, 2 000 lần): few-shot -0.064 [-0.143, +0.021], CoT +0.020 [-0.043, +0.084], JSON
schema +0.049 [+0.001, +0.103]. Sàn nhiễu: chạy lại zero-shot y hệt trên GPU cho đúng cùng 150 câu trả lời; chạy cùng
prompt chỉ trên CPU (`num_gpu` 0) làm 7 câu zero-shot và 8 câu JSON đổi nhãn, và trên CPU JSON schema chỉ hơn zero-shot
+0.002 [-0.035, +0.042].

Đọc kết quả:

- **Few-shot tệ hơn**, và ma trận nhầm lẫn cho biết vì sao: với 6 ví dụ này model đoán neutral ít hơn hẳn, đẩy câu
  neutral sang negative và positive. Hai ví dụ neutral ("cho em xin ít con chip nfc", "không ý kiến thêm") là một lời
  xin và một câu "không ý kiến": model học rằng neutral là "không nói gì", trong khi tập test có nhiều câu neutral
  dạng mô tả. Ví dụ là tín hiệu mạnh hơn định nghĩa trong system prompt.
- **CoT-lite** tốn 27 lần token ra và 15 lần thời gian, cho chênh lệch nằm trong nhiễu. Với phân loại một câu ngắn,
  không đáng.
- **JSON schema** có khoảng tin cậy vừa không chứa 0 trên GPU, nhưng hiệu ứng **không lặp lại** trên CPU, và cùng biến
  thể JSON chỉ đổi phần cứng đã lệch 0.035. Kết luận trung thực: "JSON schema không tệ hơn, đọc output chắc chắn hơn;
  chưa chứng minh được nó chính xác hơn". Một khoảng tin cậy sát 0 trên một lần chạy không phải bằng chứng.
- Nhãn UIT-VSFC có câu đáng ngờ ("em xin cảm ơn thầy" là neutral; nhiều lời góp ý "nên..." là negative): một phần
  "lỗi" của mọi biến thể là bất đồng về định nghĩa nhãn, không sửa được bằng prompt.

## Bẫy thường gặp

- Lấy nhãn **đầu tiên** trong câu trả lời CoT: câu suy luận hay nhắc nhãn ("không phải negative").
- Coi `None` là một lớp trong macro-F1 (thành 4 lớp) hoặc bỏ câu `None` khỏi mẫu: cả hai thưởng cho output hỏng.
- Bootstrap từng biến thể riêng rồi so hai khoảng tin cậy chồng nhau và kết luận "không khác": bỏ mất tính theo cặp.
- So biến thể trên hai lần chạy ở hai máy khác nhau mà không đo sàn nhiễu.
