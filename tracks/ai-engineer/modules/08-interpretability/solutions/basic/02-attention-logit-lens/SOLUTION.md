# Lời giải: chấm điểm head attention, logit lens và direct logit attribution

## Cách làm

**`repeated_tokens`.** Một lệnh `torch.randint(vocab_size, (batch, half), generator=g)`, `cat([r, r])`, thêm cột `prefix` ở đầu
nếu có. Token ngẫu nhiên đều trên vocab gần như không bao giờ là một cụm có nghĩa, nên model không thể đoán bản thứ nhất (loss
cỡ $$\ln V$$ hoặc hơn) và chỉ đoán được bản thứ hai bằng cách nhìn lại: đây là phép thử sạch cho cơ chế chép trong ngữ cảnh.

**Ba điểm head.** Đều là "attention trung bình đặt vào một vị trí key xác định theo vị trí query":

| Điểm | Query | Key |
| --- | --- | --- |
| previous-token | $$t = 1..T-1$$ | $$t - 1$$ (`diagonal(offset=-1)`) |
| duplicate-token | $$t$$ thuộc `half` vị trí cuối | $$t - h$$ (lần xuất hiện trước của chính token) |
| induction | $$t$$ thuộc `half` vị trí cuối | $$t - h + 1$$ (token đứng **sau** lần xuất hiện trước) |

Lấy query theo "`half` vị trí cuối" thay vì `range(half, 2*half)` để hàm đúng cả khi có token đầu. Fancy indexing
`pattern[:, :, queries, keys]` lấy đúng một phần tử mỗi query.

**`logit_lens`.** `lm_head(ln_f(resid))`: stream cuối đi qua `ln_f` rồi mới tới unembedding, nên stream giữa chừng cũng phải đi
cùng đường. Bỏ `ln_f` thì logits sai thang (stream giữa chừng có norm khác hẳn) và lệch hướng (bỏ mất $$\gamma$$, $$\beta$$).

**`token_rank`.** Đếm số logit **lớn hơn hẳn** logit đích; hoà không tính, nên token đúng hoà với token khác vẫn hạng 0.

**`direct_logit_attribution`.** LayerNorm cuối là $$\frac{x - \mu(x)}{\sigma(x)}\gamma + \beta$$. Giữ $$\sigma$$ cố định bằng độ lệch chuẩn
của stream cuối, phần còn lại tuyến tính: với $$x = \sum_i c_i$$,

$$
\mathrm{LN}(x)\cdot d = \sum_i \frac{c_i - \mu(c_i)}{\sigma(x)} \cdot (\gamma \odot d) + \beta \cdot d
$$

Mỗi số hạng là DLA của một thành phần. Với $$d = W_U[a] - W_U[b]$$ tổng đúng bằng chênh lệch logit, đến từng chữ số. "Giữ
$$\sigma$$ cố định" là một xấp xỉ khi diễn giải: nếu bỏ một thành phần thì $$\sigma$$ cũng đổi, nên DLA đo đóng góp **trực tiếp**,
không phải hiệu ứng khi xoá thành phần đó (việc của ablation và patching).

## Kiểm bằng gì

Pattern dựng tay (head lý tưởng của từng loại, có và không có token đầu), một GPT tí hon có bias và LayerNorm khác mặc định cho
logit lens và DLA. Cài sai đã thử và bị bắt: chia cho $$T$$ thay vì $$T - 1$$ ở previous-token, lệch một vị trí (`t - h` thay
`t - h + 1`), lấy query bỏ qua token đầu, logit lens không có `ln_f`, hạng dùng `>=`, DLA không trừ trung bình từng thành phần,
DLA chuẩn hoá từng thành phần bằng độ lệch chuẩn của chính nó, DLA quên $$\gamma$$, đặt `prefix` ở cuối.

## Bẫy thường gặp

- Điểm previous-token đo trên dãy ngẫu nhiên lặp lại cho số khác với trên văn bản thật: head induction ở bản thứ hai cũng tình cờ
  nhìn gần đường chéo. Đo previous-token trên văn bản thật.
- Hiểu attention cao là "quan trọng": head có thể nhìn rất mạnh vào một vị trí mà value ở đó gần 0 (ví dụ vị trí đầu, "attention
  sink"). Điểm attention là tương quan; tầm quan trọng đo bằng ablation hoặc patching.
