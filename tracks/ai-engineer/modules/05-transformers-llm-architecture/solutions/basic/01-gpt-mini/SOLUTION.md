# Lời giải: GPT mini tự dựng

## Cách làm

Model là một chồng phép biến đổi giữ nguyên shape `(B, T, C)` trên **residual stream**: embedding ghi vào stream, mỗi
Block đọc một bản đã chuẩn hoá, tính một "độ chỉnh" và **cộng** vào stream, cuối cùng `ln_f` + `lm_head` đọc stream ra
logits. Mọi chi tiết của lời giải đi từ hình ảnh này.

| Thành phần | Cài đặt | Vì sao |
| --- | --- | --- |
| `LayerNorm` | $$\frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} \gamma + \beta$$, $$\sigma^2$$ lệch (`mean((x-μ)²)`) | đúng định nghĩa của Ba và cộng sự; `x.var()` mặc định chia $$D-1$$ (lệch $$\sqrt{D/(D-1)}$$) |
| Mask | `torch.tril(ones(T_max, T_max))` bool, `register_buffer(..., persistent=False)` | buffer đi theo `.to(device)`; không lưu vào checkpoint vì tính lại được |
| Tách head | `view(B, T, H, D).transpose(1, 2)` | head $$h$$ là cột $$hD..(h+1)D$$ của mỗi token; `view(B, H, T, D)` trộn token với nhau |
| Score | `q @ k.transpose(-2, -1) / sqrt(D)`, `masked_fill(~mask, -inf)` rồi softmax | chia $$\sqrt{D}$$ (không phải $$\sqrt{C}$$) để phương sai score ≈ 1 |
| Block | `x = x + attn(ln1(x)); x = x + mlp(ln2(x))` | pre-norm: đường residual không đi qua norm, gradient tới embedding trực tiếp |
| Weight tying | `lm_head.weight = tok_emb.weight` | tiết kiệm $$V \cdot C$$ tham số (với $$V = 8000, C = 256$$ là 2.05 triệu: model 4 tầng còn 5.24 triệu thay vì 7.29 triệu) |
| Khởi tạo | $$\mathcal{N}(0, 0.02)$$; `*.proj.weight` $$\mathcal{N}(0, 0.02/\sqrt{2L})$$ | mỗi Block cộng 2 lần vào stream; thu nhỏ để phương sai stream không lớn theo độ sâu (GPT-2) |
| Loss | `F.cross_entropy(..., ignore_index=-1)` | vị trí đệm hoặc phần prompt không tính loss |
| `generate` | cắt `idx[:, -block_size:]`, logits vị trí cuối, temperature, top-k, `multinomial(generator=g)` | pos_emb chỉ có `block_size` dòng |

Với $$C = 32, L = 2, V = 50, T = 16$$, mỗi Block có $$12C^2 + 13C = 12\,704$$ tham số (qkv $$3C^2 + 3C$$, proj $$C^2 + C$$,
fc $$4C^2 + 4C$$, proj MLP $$4C^2 + C$$, hai LayerNorm $$4C$$), tổng $$VC + TC + L(12C^2 + 13C) + 2C = 27\,584$$. Công thức
"$$12 L C^2$$" của scaling laws (mục 7 lý thuyết) chính là phần lớn nhất của con số này.

Khởi tạo nhỏ cho loss ban đầu khoảng $$\ln V$$ (model đoán đều) với target ngẫu nhiên. Test dùng target **ngẫu nhiên**
chứ không phải chính `idx`: vì weight tying, logit của chính token đầu vào là $$\langle h, e_{x}\rangle$$ với $$h$$ chứa $$e_x$$, nên
model mới khởi tạo đã "đoán" token hiện tại tốt hơn đều.

## Kiểm bằng gì

- Attention so với `F.scaled_dot_product_attention(is_causal=True)` dùng **cùng** `qkv`, `proj`: bắt sai cách tách head,
  sai hệ số chia, thiếu mask.
- Tính nhân quả kiểm trên cả model: đổi token 7, logits 0..6 phải giữ nguyên. Đây là test quan trọng nhất của một
  language model: thiếu mask, loss train giảm rất nhanh (model nhìn trộm token cần đoán) nhưng sinh văn bản vô nghĩa.
- Chuỗi toàn một token: không có position embedding thì attention trên các key giống hệt nhau cho cùng output ở mọi vị
  trí. Self-attention không có thông tin vị trí là phép toán trên **tập hợp**, không phải chuỗi.
- `generate` được kiểm bằng độ dài ngữ cảnh thật sự đưa vào model qua một hook, và so với vòng argmax tính tay.

## Bẫy thường gặp

- `x.var(dim=-1)` (không lệch) hoặc `sqrt(var) + eps`: sai lệch nhỏ nhưng thấy rõ khi phương sai nhỏ.
- Đặt mask là `nn.Parameter` hoặc tensor thường: không theo model lên GPU, hoặc bị optimizer cập nhật.
- Post-norm (`ln(x + attn(x))`): đúng với Transformer gốc 2017, nhưng train sâu cần warmup kỹ hơn (mục 2 lý thuyết).
- Gán tying **sau** `self.apply(init)` rồi khởi tạo lại `lm_head`: tensor dùng chung bị khởi tạo hai lần, vô hại; nhưng
  gán `lm_head.weight.data = tok_emb.weight.data.clone()` thì hai tensor tách rời, không còn tying.
- `generate` quên `self.eval()`: dropout vẫn bật khi sinh.
