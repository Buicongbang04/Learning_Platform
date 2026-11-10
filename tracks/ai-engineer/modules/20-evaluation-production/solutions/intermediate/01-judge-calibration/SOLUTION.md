# Lời giải: hiệu chuẩn LLM judge với nhãn người

## Cách làm

- `make_items`: đúng một lần `rng.random()` cho mỗi câu, `rng.integers(0, 2)` chỉ cho câu bị đổi, chọn trong hai nhãn còn
  lại theo thứ tự của `LABELS`. Với `seed=0`, 78 trên 150 nhãn ứng viên là đúng.
- `p_yes`: chuẩn hoá trên hai token "yes"/"no" trong `top_logprobs` của token đầu, gộp biến thể viết hoa và dấu cách. Khi
  "yes" không lọt top-5 thì xác suất là 0: một xấp xỉ, đủ cho ECE và chọn ngưỡng.
- `expected_calibration_error`, `pick_threshold`: đúng định nghĩa trong notebook; ngưỡng chọn trên 75 câu đầu, báo trên 75
  câu sau.
- `judge_pair`: hai lời gọi, lần hai đổi chỗ; verdict gộp bằng `resolve_swap` của Basic 02.

## Kết quả tham chiếu

PC của track, Ollama 0.13.5, `temperature` 0, `seed` 0. `qwen2.5:3b` trên GPU dùng chung (trung vị 0.42 s một lượt),
`qwen2.5:7b` chỉ CPU 4 luồng (trung vị 2.7 s một lượt, khoảng 7 phút cho 150 câu). Notebook lời giải chạy khoảng 12 phút.

**Pointwise trên 150 câu UIT-VSFC** (78 nhãn ứng viên đúng, 72 bị đổi sai):

| Judge | Accuracy | Kappa | False pass | False fail | Judge cho qua | ECE | Ngưỡng (nửa đầu) | Accuracy nửa sau: ngưỡng / 0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5:3b` | 0.793 | 0.589 | 0.111 | 0.295 | 0.42 | 0.197 | 0.008 | 0.800 / 0.760 |
| `qwen2.5:7b` | 0.880 | 0.760 | 0.111 | 0.128 | 0.51 | 0.122 | 0.56 | 0.853 / 0.853 |

Kappa giữa hai judge: 0.641. Sai theo lớp (false fail đếm theo nhãn gold, false pass theo nhãn ứng viên):

| Judge | False fail: negative / neutral / positive | False pass: negative / neutral / positive |
| --- | --- | --- |
| `qwen2.5:3b` | 4/30, 8/22, 11/26 | 3/23, 3/23, 2/26 |
| `qwen2.5:7b` | 2/30, 3/22, 5/26 | 3/23, 4/23, 1/26 |

**Pairwise trên 60 câu hỏi Zalo Legal**, `qwen2.5:3b`, đoạn A là điều luật đúng (qrels), B là hard negative, mỗi đoạn cắt
1 000 ký tự, mỗi cặp chấm hai thứ tự:

| Điều kiện | A thắng | B thắng | Hoà | Không nhất quán | Nhất quán | Tỉ lệ thắng của A | Chọn vị trí đầu |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gốc | 14 | 2 | 8 | 36 | 0.400 | 0.600 | 0.679 |
| độn chữ vào đoạn sai | 15 | 0 | 9 | 36 | 0.400 | 0.625 | 0.625 |
| độn chữ vào đoạn đúng | 14 | 3 | 6 | 37 | 0.383 | 0.592 | 0.616 |

Không verdict nào hỏng JSON (Ollama `format` với schema).

## Đọc kết quả

- **Judge 3B khắt khe hơn dễ dãi**: false fail 0.295 so với false pass 0.111; nó cho qua 42% trong khi 52% nhãn ứng viên
  đúng. Phần lớn false fail rơi vào câu **positive** (11/26) và neutral (8/22): judge từ chối nhãn positive của những câu
  khen nhẹ hoặc mô tả ("giảng viên đưa ra bài tập cụ thể", "thầy giảng tương đối dễ hiểu"). Đó cũng là ranh giới mơ hồ của
  bộ nhãn (module 11 mục 7 thấy neutral là lớp khó nhất); một phần "lỗi" của judge là nhãn gold đáng tranh luận.
- **Judge 7B tốt hơn rõ** ở kappa (0.76 so với 0.59) và chủ yếu nhờ giảm false fail; false pass bằng nhau. ECE thấp hơn.
  Hai judge chỉ khớp nhau ở kappa 0.64: đổi judge là đổi thước đo, phải hiệu chuẩn lại.
- **Calibration**: cả hai quá tự tin (ECE 0.12 tới 0.20; hầu hết xác suất dồn sát 0 hoặc 1). Ngưỡng chọn trên nửa đầu cho
  judge 3B là 0.008 (cho qua gần như mọi câu có chút xác suất "yes"), thắng ngưỡng 0.5 ba câu trên 75 câu nửa sau: trong mức
  nhiễu, không phải bằng chứng. Với 7B, ngưỡng chọn được gần 0.5 và không đổi kết quả.
- **Độ nhạy với prompt**: một lần chạy thử trước với system prompt chỉ khác ba chữ ("câu phản hồi" thay vì "câu phản hồi của
  sinh viên") cho judge 3B kappa 0.495 thay vì 0.589. Ghim prompt judge như ghim model.
- **Pairwise với judge 3B không dùng được** ở tác vụ này: 60% cặp đổi ý khi đổi chỗ, 62% tới 68% verdict chọn đoạn đứng
  trước. Khi nó nhất quán thì gần như luôn chọn đúng điều luật (14 so với 2), nên tín hiệu có, nhưng bị thiên vị vị trí lấn át.
  Không chấm hai thứ tự thì kết quả chủ yếu đo vị trí.
- **Độn chữ không đổi gì đo được**: tỉ lệ thắng của đoạn đúng 0.59 tới 0.63 ở cả ba điều kiện, chênh nhau một hai cặp trên 60.
  Thí nghiệm này **không** thấy thiên vị độ dài, nhưng cũng không chứng minh là không có: chữ độn ở đây là câu khuôn mẫu vô
  nghĩa (judge có thể bỏ qua), 60 cặp chỉ thấy được chênh lệch lớn, và thiên vị độ dài của Zheng et al. (2023) đo trên câu
  trả lời dài hơn **có nội dung** chứ không phải đoạn nguồn độn chữ.

## Lỗi hay gặp

- Gọi `rng.integers` cho mọi câu (cả câu không đổi): tập ứng viên khác lời giải, số trắc nghiệm không khớp.
- `p_yes` chỉ xét token đúng chính tả `"yes"`: Ollama trả `"Yes"` hoặc `" yes"` tuỳ ngữ cảnh.
- Chọn ngưỡng và báo accuracy trên cùng một tập: luôn thắng ngưỡng 0.5, tự lừa mình.
- Chỉ chạy một thứ tự trong pairwise, hoặc lấy verdict lượt đầu khi hai lượt khác nhau.
- Kết luận "judge 3B đủ tốt" từ accuracy 0.79 mà không nhìn false fail theo lớp.
