# Lời giải: đọc GPT-2 small từ bên trong

## Cách làm

**`gpt2_into_gpt_mini`.** GPT-2 và lớp `GPT` của module 05 cùng kiến trúc, chỉ khác tên và chiều lưu trọng số. Ánh xạ tên:
`wte → tok_emb`, `wpe → pos_emb`, `h.i.ln_1 → blocks.i.ln1`, `attn.c_attn → attn.qkv` (thứ tự q | k | v và cách chia head
giống hệt), `attn.c_proj → attn.proj`, `mlp.c_fc → mlp.fc`, `mlp.c_proj → mlp.proj`, `ln_f → ln_f`. `Conv1D` tính
$$xW + b$$ với $$W$$ shape `(in, out)` nên phải chuyển vị sang `nn.Linear`. `lm_head.weight` trong state dict của ta là cùng tensor với
`tok_emb.weight`; nạp `wte` vào cả hai khoá giữ nguyên tying (load_state_dict chỉ chép giá trị). Hai bẫy im lặng: ma trận vuông
`attn.c_proj` không báo lỗi shape khi quên chuyển vị, và GELU chính xác thay cho bản tanh làm logits lệch cỡ $$10^{-3}$$, đủ để
đổi top-1 ở vài vị trí. Bản đúng lệch Hugging Face $$8.4 \times 10^{-5}$$ (float32, khác thứ tự phép cộng).

**`ablate_heads`.** Pre-hook trên `attn.proj` nhận `z` shape `(B, T, C)`, `view` thành `(B, T, n_head, head_dim)`, gán head được
chọn bằng 0 hoặc `means[layer][head]`, trả `(z,)` để thay input. Clone trước khi sửa (không sửa tại chỗ tensor của autograd), gỡ
hook trong `finally`.

**`in_context_loss`.** Với dãy dài $$T$$, bản 2 bắt đầu ở $$s_2 = T - h$$, bản 1 ở $$s_1 = s_2 - h$$. Logits ở vị trí $$p$$ dự đoán token
$$p + 1$$, nên "token thứ 2 tới thứ $$h$$ của bản 1" là NLL ở các vị trí $$s_1 .. s_1 + h - 2$$; tương tự cho bản 2. Token đầu của
bản 2 không đoán được bằng induction (token đứng trước nó là token cuối của bản 1, chưa từng xuất hiện trước đó).

**`repeated_token_labels`** duyệt từng hàng với một `set`. **`lens_metrics`** dùng `log_softmax` cho cả hai phân phối, KL theo
chiều $$\sum p_{\text{model}}(\log p_{\text{model}} - \log p_{\text{lens}})$$: "lens mất bao nhiêu thông tin so với model".

## Kết quả thật

GPT-2 small (`openai-community/gpt2`) trong lớp `GPT` của module 05, CPU 4 luồng, torch 2.14.1, ngày 2026-11-01; dãy lặp
lại: 20 dãy, `half` 50, token đầu `<|endoftext|>`, generator seed 0 (ablation dùng seed 1); văn bản: 80 ngữ cảnh 128 token từ
IWSLT15 `tst2012.en` + `tst2013.en` (TED). Cả notebook chạy khoảng 2 phút (128 giây, PC dùng chung).

### Bản đồ head

| Loại | Head mạnh nhất (tầng.head = điểm) |
| --- | --- |
| Induction | 5.5 = 0.93, 6.9 = 0.91, 5.1 = 0.90, 7.10 = 0.90, 7.2 = 0.83, rồi 10.1 = 0.52 |
| Duplicate-token | 3.0 = 0.66, 0.5 = 0.64, 0.1 = 0.27 |
| Previous-token (văn bản) | 4.11 = 1.00, 2.2 = 0.58, 3.2 = 0.39, 3.7 = 0.36 |

Thứ tự tầng khớp cơ chế hai bước: head previous-token (tầng 2–4) chép "token trước tôi là gì" vào từng vị trí, head induction
(tầng 5–7) dùng thông tin đó làm key (K-composition). Đây là tương quan; câu hỏi "có cần không" thuộc về ablation.

### Ablation (dãy seed 1, loss nat)

| Cấu hình | Loss bản 1 | Loss bản 2 |
| --- | --- | --- |
| Không ablation | 13.24 | 0.22 |
| Top 1 induction: zero / mean | 13.39 / 13.24 | 0.32 / 0.27 |
| Top 2: zero / mean | 13.56 / 13.24 | 0.42 / 0.46 |
| Top 4: zero / mean | 15.63 / 13.23 | 2.19 / 8.73 |
| Top 6: zero / mean | 16.14 / 13.23 | 6.93 / 10.06 |
| 4 head ngẫu nhiên (không phải induction), mean, 5 lần | | 0.23, 0.30, 0.32, 0.26, 0.93 |
| 6 head ngẫu nhiên, mean, 5 lần | | 0.31, 0.42, 1.19, 0.87, 0.21 |

Đọc kết quả:

- Tắt một hai head gần như không đổi gì: các head induction **dự phòng** cho nhau. Phải tắt cả bốn mới thấy loss bản 2 vọt lên.
  "Tắt một head không ảnh hưởng" vì thế không chứng minh head đó vô dụng.
- Zero ablation làm loss **bản 1** (phần không cần induction) tăng 2–3 nat; mean ablation giữ nguyên. Output bằng 0 là một trạng
  thái model chưa bao giờ thấy, nên zero ablation đo cả "hỏng vì lạ" lẫn "hỏng vì thiếu head". Mean ablation sạch hơn, và nó cho
  thấy hiệu ứng thật trên bản 2 còn lớn hơn (8.73 so với 2.19 với 4 head). Với 4 head, zero ablation cho loss bản 2 thấp hơn mean
  ablation: phép can thiệp lạ có thể vô tình bật đường khác.
- Tắt cùng số head ngẫu nhiên chỉ làm loss bản 2 tăng dưới 1.2 nat: hiệu ứng là của head induction chứ không phải của "tắt 4 head
  bất kỳ". Ablation chứng minh 5 head này **cần** cho hành vi trên dữ liệu này; nó không chứng minh chúng **đủ**, cũng không nói
  chúng làm gì trên văn bản thường.

### Logit lens (20 ngữ cảnh TED)

| Stream | CE (nat) | Trùng top-1 với model | KL | Hạng trung vị của token đúng |
| --- | --- | --- | --- | --- |
| `resid_pre.0` | 49.06 | 0.000 | 45.17 | 19 558 |
| `resid_post.0` | 9.05 | 0.085 | 5.57 | 75 |
| `resid_post.3` | 8.25 | 0.094 | 4.79 | 39 |
| `resid_post.6` | 7.35 | 0.167 | 3.90 | 18 |
| `resid_post.8` | 6.40 | 0.305 | 2.99 | 9 |
| `resid_post.9` | 5.83 | 0.420 | 2.46 | 6 |
| `resid_post.10` | 4.75 | 0.596 | 1.35 | 3 |
| `resid_post.11` | 3.54 | 1.000 | 0.00 | 2 |

Dự đoán hình thành dần: hạng của token đúng giảm đều qua các tầng, top-1 của lens trùng model ở quá nửa số vị trí từ
`resid_post.10`. Ở `resid_pre.0` (embedding), lens gần như dự đoán lại chính token hiện tại (weight tying): CE 49. Quên `ln_f` ở
`resid_post.6`: CE 40.2 vì stream giữa chừng có norm lớn (logits bị phóng to, softmax quá tự tin), dù top-1 trùng model lại
0.235: lỗi chủ yếu ở thang đo chứ không ở hướng. Logit lens chỉ cho thấy những gì **đọc được bằng unembedding của tầng cuối**;
tầng sớm có thể mang thông tin theo hướng khác (tuned lens, mục 4 lý thuyết).

### Probe "token đã xuất hiện chưa" (10 160 token, chia theo ngữ cảnh 75/25)

Majority baseline 0.605; baseline tra theo loại token (chỉ dùng token id) 0.747.

| Stream | GPT-2 task / control / selectivity | GPT-2 khởi tạo ngẫu nhiên task / control |
| --- | --- | --- |
| `resid_pre.0` | 0.778 / 0.887 / −0.109 | 0.769 / 0.894 |
| `resid_post.0` | 0.979 / 0.867 / +0.112 | 0.745 / 0.853 |
| `resid_post.1` | 0.976 / 0.850 / +0.127 | 0.748 / 0.820 |
| `resid_post.3` | 0.939 / 0.835 / +0.103 | 0.743 / 0.817 |
| `resid_post.6` | 0.900 / 0.814 / +0.086 | 0.738 / 0.811 |
| `resid_post.11` | 0.807 / 0.739 / +0.068 | 0.722 / 0.791 |

Đọc kết quả:

- Ở embedding, probe chỉ ngang baseline tra theo loại token: token phổ biến ("the", ",") hầu như luôn đã xuất hiện, nên token id
  một mình đoán được ba phần tư. Đó là sàn phải vượt, không phải 0.5 hay 0.605.
- Sau tầng 0, probe vọt lên 0.98: thông tin "đã xuất hiện" được ghi vào stream rất sớm, khớp với head duplicate ở tầng 0 (0.5, 0.1)
  và tầng 3 (3.0). Thông tin mờ dần ở tầng sau (0.81 ở tầng cuối): stream dành chỗ cho việc dự đoán token kế tiếp.
- GPT-2 khởi tạo ngẫu nhiên đứng yên ở mức baseline loại token mọi tầng: kiến trúc một mình (attention trung bình các vị trí
  trước) không đủ tạo ra thông tin này dưới dạng đọc tuyến tính được; nó do train mà có.
- Control task cao ở mọi nơi (0.74–0.89): probe tuyến tính 768 chiều dư sức học thuộc một nhãn ngẫu nhiên theo loại token.
  Selectivity âm ở embedding và dương khoảng 0.1 ở tầng sớm.
- Probe cho thấy thông tin **giải mã tuyến tính được**; nó không cho thấy GPT-2 **dùng** hướng đó. Muốn nói "dùng" phải can thiệp
  (ablation head duplicate rồi đo hành vi, hoặc patching), đó là bài Intermediate 02.

### GPT mini tiếng Việt (tuỳ chọn, checkpoint cấu hình PC của module 05)

Với checkpoint tham chiếu (6 tầng × 384, bpc 1.347): head induction mạnh nhất 5.5 = 0.62 và 5.0 = 0.55, đều ở tầng **cuối**; logit
lens trên `tst2013.vi` trùng top-1 với model 0.23, 0.20, 0.30, 0.44, 0.58, 1.00 qua 6 tầng. Model nhỏ train ngắn có induction head
yếu hơn và muộn hơn GPT-2. Checkpoint của bạn sẽ cho số khác.

## Bẫy thường gặp

- So điểm induction mà quên token đầu: dãy không có `<|endoftext|>` làm GPT-2 dồn attention bất thường ở vị trí 0.
- Kết luận từ zero ablation mà không so với mean ablation hoặc với head ngẫu nhiên.
- Probe chia train/test theo token thay vì theo ngữ cảnh, hoặc chuẩn hoá trên toàn bộ dữ liệu: số đẹp hơn mà sai.
- Đọc logit lens như "tầng 6 nghĩ rằng...": lens đo cái đọc được bằng unembedding cuối, không phải "ý nghĩ" của tầng đó.
