# Lời giải: DPO loss và một bước train với reference đóng băng

## Cách làm

**`sequence_logps`.** Dịch một vị trí (`logits[:, :-1]` với `labels[:, 1:]`), `log_softmax` ở `float32` (bf16 chỉ có 8 bit
mantissa: log-prob của từng token đã thô, cộng hàng chục cái thì sai số cộng dồn), thay `-100` bằng 0 để `gather` không lỗi chỉ số, nhân
với mask rồi **cộng** theo chiều thời gian. Cộng chứ không lấy trung bình: DPO so log-xác suất của **cả câu**,
$$\log\pi(y \mid x) = \sum_t \log\pi(y_t \mid x, y_{<t})$$. Lấy trung bình theo độ dài là một biến thể khác (SimPO làm
vậy), đổi cả ý nghĩa của $$\beta$$.

**`dpo_loss`.** Với $$h = \big(\log\pi_\theta(y_w) - \log\pi_{\text{ref}}(y_w)\big) - \big(\log\pi_\theta(y_l) - \log\pi_{\text{ref}}(y_l)\big)$$:

$$
L = -\log\sigma(\beta h), \qquad \frac{\partial L}{\partial h} = -\beta\,\sigma(-\beta h)
$$

Gradient luôn đẩy $$h$$ lên (chosen lên, rejected xuống), với trọng số $$\sigma(-\beta h)$$: cặp mà model đang **sai**
(reward ngầm của rejected cao hơn chosen) được đẩy mạnh, cặp đã đúng xa thì gần như bỏ qua. Policy trùng reference thì
$$h = 0$$, loss $$\log 2 \approx 0.693$$: con số đầu tiên bạn phải thấy trong log của mọi lượt DPO (TRL cũng vậy); khác
$$\log 2$$ ở bước đầu là dấu hiệu reference không phải bản sao của policy, hoặc dropout đang bật.

**Reward ngầm** $$\beta(\log\pi_\theta - \log\pi_{\text{ref}})$$ đúng là cột `rewards/chosen`, `rewards/rejected` của TRL;
`rewards/margins` là hiệu, `rewards/accuracies` là tỉ lệ margin dương. Trả về đã `detach` vì chỉ để log.

**`dpo_step`.** Reference chạy trong `torch.no_grad()`: không đồ thị, không `.grad`, bộ nhớ chỉ cho activation của một
lượt forward. Không cho reference vào optimizer là chưa đủ: nếu forward của nó có gradient, `backward` vẫn tính và ghi
`.grad` vào tham số của nó (test kiểm). Thực tế còn hai cách rẻ hơn: tính trước log-prob của reference cho cả bộ dữ liệu
(`precompute_ref_log_probs` của TRL), hoặc khi dùng LoRA thì reference chính là model khi **tắt adapter**, không cần bản
sao thứ hai (TRL làm vậy khi bạn truyền `peft_config`).

## Bẫy thường gặp

- Đặt $$\beta$$ ngoài sigmoid ($$-\beta\log\sigma(h)$$): loss vẫn giảm nhưng $$\beta$$ chỉ còn là learning rate, mất vai trò
  "độ chặt của ràng buộc KL" trong nghiệm đóng.
- Bỏ reference ($$h = \log\pi_\theta(y_w) - \log\pi_\theta(y_l)$$): thành một loss xếp hạng thuần, model dễ đẩy cả hai câu
  xuống rất thấp và lệch khỏi phân phối SFT.
- Tính log-prob trên cả prompt: prompt giống hệt nhau ở hai câu nên triệt tiêu trong $$h$$ về lý thuyết, nhưng với
  reference khác policy thì không, và tốn thêm sai số số học. Label của prompt là `-100`.
- Quên `model.eval()` hoặc tắt dropout cho reference: log-prob của reference đổi theo mỗi lần gọi.
