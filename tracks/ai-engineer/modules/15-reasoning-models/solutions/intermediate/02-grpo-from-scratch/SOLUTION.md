# Lời giải: vòng GRPO tự viết

## Cách làm

- `completion_mask`: `cumsum` của "là token dừng" trừ chính nó cho biết token dừng đã xuất hiện **trước** vị trí hiện tại
  chưa; mask là phủ định của điều đó. Token dừng đầu tiên được giữ (model phải học nhả `<|im_end|>`), mọi thứ sau nó (pad
  của `generate`) bị bỏ.
- `completion_logprobs`: ghép prompt (pad trái) với completion (pad phải) nên completion luôn ở C vị trí cuối; một lượt
  forward với `logits_to_keep=C + 1`, bỏ logits cuối, chia `temperature`, rồi `gather` logit của token cần trừ `logsumexp`.
  Chia `temperature` để log-prob là của **đúng phân phối đã lấy mẫu** (TRL cũng làm vậy); với ratio policy mới / policy cũ
  thì hai bên cùng chia nên không đổi gì, nhưng KL tới reference và log-prob tuyệt đối thì có.
- Reference là chính model với adapter LoRA tắt (`model.disable_adapter()`), không tốn thêm bộ nhớ.
- Vòng lặp: sinh (model `eval`, có KV cache), reward, advantage nhóm, `old_logp` và `ref_logp` không gradient, rồi `iters = 2`
  lượt gradient trên cùng batch (lượt thứ hai mới có ratio khác 1, nên mới thấy phép cắt), micro-batch 2 chuỗi, loss mỗi
  micro-batch nhân tỉ lệ số chuỗi để tổng bằng loss của cả batch.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB, dùng chung với Ollama của agent khác), `Qwen2.5-0.5B-Instruct` bf16, LoRA r = 16 mọi lớp tuyến
tính, 30 bước × 8 câu × 8 lời giải, `temperature` 0.7, tối đa 320 token khi train, lr 2e-5, `beta` 0.04, 2 lượt gradient
mỗi batch, micro-batch 2, gộp loss theo chuỗi. Train 29.7 phút, VRAM đỉnh (PyTorch cấp phát) 2.56 GiB: vừa GPU 4GB.

Đo greedy trên 200 câu test đầu, tối đa 512 token:

| | accuracy (trích dễ dãi) | boxed_correct (như reward) | đúng khung | token TB |
| --- | --- | --- | --- | --- |
| trước | 0.430 | 0.415 | 0.690 | 304 |
| sau 30 bước | 0.470 | 0.470 | 0.845 | 272 |

Hiệu accuracy: +0.040 [−0.025, +0.110] (bootstrap theo cặp); 27 câu sai thành đúng, 19 câu đúng thành sai.

Theo bước (trung bình 5 bước đầu → 5 bước cuối, trên lời giải lấy mẫu của câu train, mỗi bước một nhóm câu khác nhau
nên rất nhiễu): reward 0.42 → 0.63, đúng đáp số 0.35 → 0.50, đúng khung 0.37 → 0.61, độ dài 273 → 244 token. KL k3 tăng
từ khoảng 0.002 lên 0.026; clip fraction trung bình 0.002; tỉ lệ nhóm std = 0 trung bình 0.16. Mỗi bước khoảng 59 giây,
trong đó sinh 27.5 giây (46%); phần còn lại là ba lượt forward (policy cũ, reference, rồi 2 lượt forward/backward) qua 32
micro-batch 2 chuỗi.

## Đọc kết quả

- **Thứ GRPO dạy đầu tiên là khung.** Đúng khung tăng 15.5 điểm, khoảng cách giữa hai cột accuracy (0.430 so với 0.415)
  biến mất: model thôi viết chữ sau hộp và thôi để đáp số ngoài hộp. Accuracy theo bộ trích dễ dãi tăng 4 điểm nhưng khoảng
  tin cậy chứa 0, và 19 câu tệ đi: chưa thể nói model **giải toán** giỏi hơn sau 240 câu train. Bài Advanced 01 chạy lâu hơn,
  nhiều seed để trả lời câu đó.
- **Lời giải ngắn đi** vì reward phạt chữ thừa sau hộp và lời giải dài dễ bị cắt ở 320 token khi train (cắt là mất hộp,
  reward 0).
- **KL và clip ở mức thấp** so với vùng bình thường của PPO (module 07 mục 6): lr 2e-5 với LoRA là thận trọng. Clip fraction
  nhỏ vì chỉ lượt thứ hai trên mỗi batch có ratio khác 1, và lr nhỏ nên ratio ít khi ra ngoài [0.8, 1.2].
- **Sinh chiếm gần một nửa** dù micro-batch 2 làm phần cập nhật chậm đi nhiều; với micro-batch lớn hơn (GPU lớn hơn) phần sinh
  chiếm phần lớn bước. Đó là lý do các thư viện RL cho LLM dồn sức vào sinh (vLLM).

## Bẫy thường gặp

- Log-softmax cả vocab cho micro-batch lớn: bản tham chiếu đầu tiên với micro-batch 8 hết VRAM (7.2 GB) khi GPU đang chia
  với Ollama. Micro-batch 2 cho đỉnh 2.56 GiB.
- Quên chia loss mỗi micro-batch theo tỉ lệ số chuỗi: gradient lớn gấp số micro-batch lần.
- Tính `old_logp` sau khi đã cập nhật: ratio luôn 1, phép cắt không bao giờ bật.
- Để dropout của LoRA khác 0: policy cũ và mới khác nhau chỉ vì dropout, ratio nhiễu (TRL có `disable_dropout`).
- So reward lúc train giữa đầu và cuối như thể là accuracy: mỗi bước là một nhóm câu khác, độ khó khác nhau.
