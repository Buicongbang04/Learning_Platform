# Lời giải: hook, cache và phân rã residual stream

## Cách làm

Mỗi khoá trong cache là input hoặc output của **một** module con của lớp `GPT` module 05, nên chọn đúng loại hook là xong:

| Khoá | Hook | Vì sao |
| --- | --- | --- |
| `resid_pre.l` | pre-hook trên `blocks[l]` | input của Block là stream **trước** `ln1`; hook output của `ln1` sẽ ra stream đã chuẩn hoá |
| `attn_out.l` | hook trên `blocks[l].attn` | output đã qua `proj`, trước khi cộng vào stream |
| `resid_mid.l` | pre-hook trên `blocks[l].ln2` | input của `ln2` chính là `x + attn(ln1(x))` |
| `mlp_out.l` | hook trên `blocks[l].mlp` | |
| `resid_post.l` | hook trên `blocks[l]` | |
| `pattern.l` | hook trên `blocks[l].attn.attn_dropout` | output của dropout là ma trận softmax (dropout tắt ở eval) |
| `z.l` | pre-hook trên `blocks[l].attn.proj` | input của `proj` là output các head nối liền; `view(B, T, H, D)` |

Ba chi tiết làm hàm dùng được lâu dài: `detach().clone()` (cache không giữ graph, không bị sửa ngầm nếu sau này ai đó viết phép
tại chỗ); `model.eval()` + `torch.no_grad()` rồi trả lại chế độ cũ (pattern với dropout bật không còn là phân phối); gỡ hook trong
`finally` (một hook sót lại sẽ âm thầm sửa mọi lần forward sau, lỗi khó tìm nhất của interpretability).

**`head_contributions`.** `proj` tính $$y = zW_O^\top + b$$. Viết $$z = [z_1, \dots, z_H]$$ theo head thì
$$zW_O^\top = \sum_h z_h W_{O,h}^\top$$ với $$W_{O,h}$$ là cột `h*D .. (h+1)*D` của `proj.weight`. `W_O.view(C, H, D)` tách đúng các
cột đó; `einsum("bthd,chd->bthc")` tính mọi head một lần. Bias không thuộc head nào nên không cộng vào.

**`residual_components`.** Pre-norm nghĩa là stream cuối là tổng thuần: $$x_L = e_{tok} + e_{pos} + \sum_l (\text{attn}_l + \text{mlp}_l)$$.
Đây là lý do logit lens, direct logit attribution và patching từng sublayer có nghĩa: mỗi thành phần "ghi" một vector vào cùng một
không gian.

## Kiểm bằng gì

Test dựng GPT 3 tầng tí hon, bias và LayerNorm khác mặc định, `proj` phóng to 10 lần để đóng góp từng head không nhỏ tới mức sai
vẫn lọt. Các phép kiểm sổ sách (`resid_mid = resid_pre + attn_out`, tổng thành phần bằng stream cuối, `lm_head(ln_f(·))` bằng
logits) bắt mọi lỗi đặt hook sai chỗ. Những cài sai đã thử và bị test bắt: lấy output của `ln1` làm `resid_pre`, lấy output của
`ln2` làm `resid_mid`, không gọi `eval()`, gỡ hook ngoài `finally`, không trả lại chế độ train, tách `proj.weight` theo thứ tự
`(D, H)`, cộng bias vào từng head, quên `pos_emb`.

## Bẫy thường gặp

- Hook output của `attn.attn_dropout` khi model đang train: đó là ma trận **sau** dropout, không phải attention.
- Tách head bằng `view(B, T, D, H)`: shape đúng, số sai.
- Model dùng `F.scaled_dot_product_attention` (bản tối ưu của PyTorch) không lộ ma trận attention: phải tính lại từ q, k, hoặc
  tắt đường nhanh. Lớp `GPT` của module 05 tính tay nên hook được.
