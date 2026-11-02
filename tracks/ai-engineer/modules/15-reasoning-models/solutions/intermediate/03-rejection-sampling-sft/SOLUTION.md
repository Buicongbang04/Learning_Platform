# Lời giải: rejection sampling và SFT

## Cách làm

- `select_traces`: lọc bằng **cả hai** reward của Basic 01 (đúng đáp số và đúng khung chặt), khử trùng bằng khoá đã gộp
  khoảng trắng, rồi `sorted(..., key=len)` (ổn định) và cắt `max_keep`. Lọc cả khung vì model sẽ học **nguyên văn** lời giải:
  lời giải đúng đáp số mà có chữ thừa sau hộp dạy lại đúng thói quen mà reward GRPO phạt.
- `word_ngrams` / `contaminated`: gộp mọi n-gram của tập đo vào một `set`, mỗi câu train một phép giao; 7 473 câu × 500 câu
  chạy dưới một giây.
- `to_sft_record`: dạng prompt-completion hội thoại; `SFTTrainer` của TRL tự áp chat template và chỉ tính loss trên phần
  completion (`completion_only_loss` mặc định bật cho dạng này), đúng quy tắc của module 14 mục 2.
- SFT: LoRA r = 16 mọi lớp tuyến tính, 2 epoch, lr 1e-4 cosine, batch 4 × tích luỹ 4. Batch nhỏ vì logits 151 936 cột
  của 8 chuỗi dài làm hết VRAM khi GPU chia với job khác.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB, dùng chung), `Qwen2.5-0.5B-Instruct` bf16. 800 câu đầu của tập train trộn theo seed 0, 4 lời
giải mỗi câu ở `temperature` 0.7 (3 200 lời giải, 12.8 phút với batch 128). Kiểm nhiễm bẩn với 500 câu test ghim: 8-gram
cho 42 câu trong toàn bộ tập train, 13-gram cho 0; 800 câu nguồn giữ nguyên.

| Thống kê lọc | Giá trị |
| --- | --- |
| lời giải đúng đáp số | 45.1% |
| lời giải đúng cả đáp số và khung | 30.1% |
| câu có ít nhất một lời giải đúng (pass@4) | 73.6% |
| câu đóng góp mẫu SFT | 446 / 800 |
| số mẫu SFT (tối đa 2 mỗi câu) | 735 |
| độ dài TB mẫu giữ / mọi lời giải | 879 / 1 005 ký tự |

SFT 2 epoch: 3.3 phút, loss phần completion giảm từ 0.19 xuống 0.13. Đo greedy trên 500 câu test ghim, tối đa 512 token:

| | accuracy | boxed_correct | đúng khung | token TB | bị cắt |
| --- | --- | --- | --- | --- | --- |
| model gốc | 0.430 | 0.420 | 0.654 | 302 | 19 |
| sau SFT | 0.452 | 0.442 | 0.820 | 301 | 22 |

Hiệu accuracy: +0.022 [−0.018, +0.066]; 63 câu sai thành đúng, 52 câu đúng thành sai. Cả notebook chạy khoảng 25 phút
(sinh 13, SFT 3, hai lần đo 3 và 5 phút: model có adapter chưa merge sinh chậm hơn).

## Đọc kết quả

- **Trần của tự học**: 26% câu train không có lời giải đúng nào trong 4 lần thử; chúng không bao giờ vào dữ liệu, nên model
  học lại chủ yếu những gì nó đã làm được. Bộ lọc khung còn cắt thêm một phần ba lời giải đúng: chỉ 446 câu đóng góp mẫu.
- **Thứ đổi rõ là khung**: đúng khung từ 65% lên 82%, vì mọi mẫu SFT đều đúng khung. Accuracy tăng 2.2 điểm, khoảng tin cậy
  chứa 0, và 115 câu đổi chiều cho thấy model đổi nhiều hơn con số ròng nói.
- **Lọc ngắn trước** giữ lời giải ngắn hơn trung bình 13%, nhưng độ dài lời giải trên tập đo gần như không đổi: hai mẫu mỗi
  câu không đủ để kéo phong cách đi xa.
- **8-gram không phải nhiễm bẩn**: đọc các cặp trùng thấy cụm "what was the original price of" hay "the first 40 hours she
  works each week": đề khác, số khác. 13-gram không bắt câu nào: tập train và test của GSM8K tách sạch.
- So với Intermediate 02 (GRPO 30 bước, đo trên 200 câu) và Advanced 01/02: mọi nhánh đều tăng định dạng trước; bài
  Advanced 02 đặt chúng trên cùng 500 câu.

## Bẫy thường gặp

- Giữ mọi lời giải đúng của câu dễ (4 bản gần giống nhau): tập SFT lệch về câu dễ; `max_keep` và khử trùng giữ cân bằng.
- Kiểm nhiễm bẩn bằng so khớp nguyên câu: bỏ sót câu chép lại có đổi một chữ; n-gram bắt được.
- SFT trên toàn chuỗi (cả prompt): model học thuộc system prompt và đề (module 14 mục 2).
- Đo trước/sau với `max_new_tokens` khác nhau: số câu bị cắt khác, accuracy khác mà model không đổi.
