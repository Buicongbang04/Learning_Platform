# Hướng làm: reasoning model mini bằng GRPO

Bài không có code lời giải: thí nghiệm và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả
của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Khung trả lời | `\boxed{}` với prompt Qwen khuyến nghị | khung thẻ `<think>`/`<answer>` gần như không bao giờ xuất hiện ở 0.5B: mọi nhóm std = 0 (mục 4 lý thuyết) |
| Reward | đúng đáp số trong hộp cuối (1.0) + đúng khung chặt (0.2), hai hàm riêng, `reward_weights=[1.0, 0.2]` | TRL log từng phần, thấy được phần nào tăng; khung nhỏ để không thắng nhóm chỉ bằng khung |
| LoRA | r = 16, alpha 32, mọi lớp tuyến tính | như module 14; reference = adapter tắt, không tốn bộ nhớ |
| Loss | mặc định TRL 1.17: `loss_type="dapo"`, `beta=0`, `scale_rewards="group"` | reward kiểm được khó hack bằng KL; bỏ reference forward, nhanh hơn |
| Batch | 8 câu × G = 8 lời giải mỗi bước (`per_device_train_batch_size=4`, `gradient_accumulation_steps=16`) | micro-batch 4 giữ logits vừa VRAM khi GPU chia với Ollama |
| Lấy mẫu | `temperature` 0.7, `top_k=0`, tối đa 384 token | ở 1.0 (mặc định TRL) model 0.5B sinh câu vô nghĩa, accuracy một mẫu tụt mạnh (mục 4 lý thuyết đo khung ở 1.0) |
| Đo | greedy, 500 câu test đầu, tối đa 512 token, cùng hàm trước/sau; 8 mẫu ở 0.7 cho 200 câu đầu để có pass@k | tập ghim chung với Intermediate 03 và Advanced 02 để so được |

Lỗi hay gặp: đo trước và sau bằng hai hàm sinh khác nhau (batch, `max_new_tokens`, prompt): bản tham chiếu thấy cùng model
gốc cho 0.430 với batch 64 và 0.436 với batch 128 trên cùng 500 câu (sai khác số học của bf16 theo kích thước batch), nên
trước/sau phải cùng một cấu hình sinh; báo reward lúc train thay cho accuracy trên tập giữ lại; để `temperature=1.0` mặc định
với model 0.5B; quên `reward_weights` làm khung nặng ngang đáp số.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB, dùng chung với Ollama của agent khác), TRL 1.17, cấu hình `PC` của notebook nhưng **60 bước**
(480 câu train, 3 840 lời giải) với lr 4e-5: khoảng 39 phút train mỗi seed (`step_time` 36 tới 39 giây), VRAM đỉnh
2.1 tới 2.2 GiB, thêm khoảng 12 phút đo mỗi seed. Tổng cho hai seed cùng lần đo gốc: khoảng 1 giờ 45 phút.

Greedy trên 500 câu test ghim, tối đa 512 token, batch 128 (cùng hàm trước và sau):

| | accuracy | boxed_correct | đúng khung | token TB | bị cắt ở 512 |
| --- | --- | --- | --- | --- | --- |
| model gốc | 0.436 | 0.424 | 0.646 | 305 | 22 |
| GRPO seed 0 | 0.482 | 0.480 | 0.970 | 160 | 2 |
| GRPO seed 1 | 0.468 | 0.468 | 0.976 | 250 | 6 |

Hiệu so với model gốc (bootstrap theo cặp, 2 000 lần):

| | accuracy | boxed_correct | sai → đúng | đúng → sai |
| --- | --- | --- | --- | --- |
| seed 0 | +0.046 [+0.004, +0.088] | +0.056 [+0.014, +0.098] | 72 | 49 |
| seed 1 | +0.032 [−0.008, +0.074] | +0.044 [+0.002, +0.088] | 66 | 50 |

Độ phủ trên 200 câu đầu, lời giải lấy mẫu ở 0.7 (model gốc: 16 lời giải mỗi câu của Intermediate 01; sau GRPO: 8 lời giải):

| | pass@1 | pass@8 | maj@8 |
| --- | --- | --- | --- |
| model gốc | 0.398 | 0.736 | 0.540 |
| seed 0 | 0.394 | 0.790 | 0.540 |
| seed 1 | 0.454 | 0.775 | 0.620 |

Log của TRL (trung bình 10 bước đầu → 10 bước cuối, trên lời giải lấy mẫu của câu train):

| | reward đúng đáp số | reward khung | độ dài | bị cắt ở 384 | nhóm std = 0 |
| --- | --- | --- | --- | --- | --- |
| seed 0 | 0.54 → 0.67 | 0.57 → 0.96 | 284 → 173 | 15% → 1% | 10% → 30% |
| seed 1 | 0.56 → 0.53 | 0.56 → 0.91 | 282 → 256 | 15% → 7% | 11% → 33% |

`clip_ratio/*` bằng 0 ở mọi bước (`num_iterations=1`), `entropy` quanh 0.12 tới 0.14, không có `kl` vì `beta=0`.

## Đọc kết quả

- **Thay đổi lớn nhất là tỉ lệ đúng khung; mức tăng accuracy nhỏ.** Đúng khung từ 65% lên trên 97% ở cả hai seed: đó là
  thứ GRPO học chắc chắn nhất trong 60 bước. Phần accuracy do khung thì nhỏ: `boxed_correct` tăng 5.6 / 4.4 điểm, accuracy
  dễ dãi tăng 4.6 / 3.2 điểm, tức khoảng 1 điểm đến từ việc đáp số đúng nay nằm trong hộp (32 câu gốc không có hộp xuống 3
  và 5). Tách theo câu: trong 72 / 66 câu sai → đúng chỉ 6 câu là câu gốc không có hộp; trên 468 câu mà model gốc đã có hộp,
  accuracy dễ dãi vẫn tăng 0.455 → 0.494 / 0.479. 2 tới 4 điểm còn lại đó nằm ở cột dễ dãi, nhưng chỉ seed 0 có khoảng tin
  cậy không chứa 0.
- **Hai seed, hai phong cách.** Seed 0 bỏ hẳn kiểu "To determine..., 1. 2. 3." (384 lời giải có danh sách bước xuống 5),
  viết một đoạn liền, ngắn còn một nửa; seed 1 giữ phong cách cũ, chỉ ngắn đi 18%. Cùng cấu hình, khác seed, khác hẳn độ dài:
  một seed thì không kết luận được "GRPO làm lời giải ngắn đi bao nhiêu". Một nguồn đo được của áp lực rút ngắn: lời giải chạm 384 token
  bị cắt trước hộp nên reward 0, và tỉ lệ bị cắt lúc train giảm từ 15% xuống 1% (seed 0) và 7% (seed 1). Phần do cách gộp
  loss (DAPO theo token) thì bản tham chiếu chưa tách bằng thí nghiệm: muốn biết, chạy lại với `loss_type="grpo"`.
- **Reward lúc train không phải accuracy.** Ở seed 1, reward đúng đáp số trung bình 10 bước cuối còn thấp hơn 10 bước đầu
  (mỗi bước là 8 câu khác nhau, độ khó khác nhau), vậy mà accuracy trên tập giữ lại vẫn tăng. Tỉ lệ nhóm std = 0 tăng từ
  khoảng 10% lên 30%: khung đã gần 1 nên nhiều nhóm có reward giống nhau hơn, tín hiệu học ít dần; muốn train tiếp thì cần câu
  khó hơn hoặc dynamic sampling.
- **Độ phủ không tụt ở k = 8; thay đổi trong vài điểm.** pass@8 0.736 → 0.790 / 0.775; bootstrap theo cặp +0.054
  [+0.001, +0.105] (seed 0) và +0.039 [−0.008, +0.087] (seed 1): sát hoặc trong nhiễu. Hai bên đo không cùng cách: model gốc
  lấy 16 mẫu (Intermediate 01, batch 64, pass@8 ước lượng không chệch từ 16), sau GRPO lấy 8 mẫu ở batch 128. Kết quả của Yue
  và cộng sự (RL thu hẹp độ phủ) nói về k vài trăm và train dài; 60 bước và k = 8 không đủ để thấy.
- **Không thấy reward hacking.** Không lời giải nào có hai hộp hay hộp rỗng; số câu sai mà đáp số chép lại một số trong đề
  giảm (33 xuống 23 và 22). Đọc các câu đúng → sai thấy lỗi suy luận thật: tính overtime 45 giờ thay vì 5 giờ, trả lời "hiệu
  hai tuổi" khi đề hỏi tuổi của một người, lấy quãng đường còn lại chia cho thời gian đã đi. Lời giải ngắn hơn bỏ bớt bước
  diễn giải đề, và đó là chỗ model nhỏ hay hiểu sai.
- **So với hai nhánh khác** (bảng ở Advanced 02): tự học (Intermediate 03) +2.2 điểm, GRPO +3.2 tới +4.6; cả ba nhánh đổi tỉ
  lệ đúng khung nhiều nhất, còn accuracy tăng vài điểm, phần lớn trong nhiễu.
## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Thiết lập tái lập được | 15 | Tập đo ghim (500 câu test đầu), cùng hàm đo trước/sau, cấu hình GRPO đầy đủ (G, batch, lr, beta, loss, temperature, độ dài), phần cứng, thời gian, VRAM; log và câu trả lời lưu ra đĩa |
| Số đo trung thực | 25 | Ít nhất hai seed (hoặc một seed kèm lý do và khoảng tin cậy), hiệu kèm khoảng tin cậy theo cặp, đếm câu đổi chiều; không gọi một chênh lệch trong nhiễu là "cải thiện" |
| Tách định dạng khỏi năng lực | 20 | Báo cả `accuracy` (trích dễ dãi) và `boxed_correct` (như reward); giải thích mức tăng đến từ đâu bằng số |
| Đường cong và độ phủ | 15 | Đường cong reward từng phần, độ dài, tỉ lệ nhóm std = 0 có giải thích; pass@1 và pass@8 trước/sau |
| Phân tích lỗi | 15 | Ít nhất 20 câu đọc tận mắt, có đếm theo kiểu lỗi, có kết luận về reward hacking (có hay không, bằng chứng) |

Đạt từ 70 điểm. Báo cáo chỉ có một con số "accuracy sau train" không có baseline cùng bộ đo, hoặc chỉ báo reward lúc train
thay cho accuracy trên tập giữ lại, không quá 40 điểm.
