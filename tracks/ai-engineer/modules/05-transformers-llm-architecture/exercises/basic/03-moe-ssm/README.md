---
title: Mixture-of-Experts và state space model chọn lọc (Mamba) tự viết
level: basic
services: []
files:
  - path: starter/moe_ssm.py
    note: 8 hàm/phương thức TODO
  - path: tests/test_moe_ssm.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/basic/03-moe-ssm -q
---

## Mục tiêu

Tự viết hai ý tưởng đang định hình các LLM mới: lớp **Mixture-of-Experts** với router top-k và loss cân tải (Mixtral,
DeepSeek-V3, Qwen3-MoE), và **state space model** từ bản bất biến theo thời gian (S4) tới bản chọn lọc của Mamba. Làm xong
bạn giải thích được bằng code vì sao MoE có nhiều tham số mà ít phép tính mỗi token, và vì sao Mamba sinh token với bộ nhớ
cố định thay vì KV cache lớn dần.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Đọc mục 5 và 6 phần lý thuyết. Trong `starter/moe_ssm.py`, điền các chỗ `# TODO` theo docstring:

1. `MoE.route`: top-k expert theo logit của `gate`, trọng số là softmax trên k logit được chọn, cùng xác suất trên mọi expert.
2. `MoE.forward`: mỗi expert chạy **một lần** trên đúng các token được route tới nó; cộng output có trọng số về vị trí
   token; trả thêm loss cân tải.
3. `load_balancing_loss(probs, top_idx, n_experts)` kiểu Switch Transformer.
4. `discretize` (zero-order hold), `ssm_scan` (hồi quy theo thời gian), `ssm_kernel` và `causal_conv` (SSM bất biến theo
   thời gian là một phép tích chập), `selective_scan` (Δ, B, C đổi theo token).

## Tiêu chí đạt

- `route` đúng top-k và đúng cách chuẩn hoá trọng số; với top-1 trọng số bằng 1.
- `forward` khớp bản tính dày từng token; mỗi expert nhận đúng số token được route; router nhận gradient từ output (không
  chỉ từ loss phụ).
- Loss cân tải bằng 1 khi chia đều, bằng `n_experts` khi dồn hết về một expert, đúng công thức trên ví dụ top-2.
- `discretize` đúng ZOH; `ssm_scan` khớp ví dụ tính tay; SSM bất biến theo thời gian cho cùng kết quả khi quét và khi tích
  chập với `ssm_kernel`.
- `selective_scan` khớp vòng lặp tham chiếu; với Δ, B, C hằng thì trùng SSM bất biến; Δ rất lớn xoá trạng thái cũ,
  Δ = 0 bỏ qua input; nhân quả.

## Gợi ý

### Gợi ý 1

Phẳng hoá input về `(N, dim)` trước. Với mỗi expert $$e$$, `(top_idx == e).nonzero(as_tuple=True)` cho cả chỉ số token
và vị trí của $$e$$ trong top-k của token đó (để lấy đúng trọng số). `index_add_` cộng kết quả về đúng hàng. Với loss cân
tải, `F.one_hot` đếm số lượt chọn.

### Gợi ý 2

Với A chéo, mọi thứ là phép toán từng phần tử: không cần `matrix_exp`. Viết ra $$y_0, y_1, y_2$$ của hồi quy với $$h_{-1} = 0$$
sẽ thấy $$y_t = \sum_k C \bar A^k \bar B x_{t-k}$$, đó là kernel. Ở `selective_scan`, Δ có shape `(T, D)` còn A có shape
`(D, N)`: thêm trục cho khớp để ra $$\bar A$$ shape `(T, D, N)`; B, C dùng chung cho mọi kênh $$d$$.
