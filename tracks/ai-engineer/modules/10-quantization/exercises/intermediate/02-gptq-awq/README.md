---
title: GPTQ và AWQ tự cài trên GPT mini
level: intermediate
services: []
files:
  - path: starter/gptq_awq.ipynb
    note: 7 hàm TODO
  - path: tests/test_gptq_awq.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/10-quantization/exercises/intermediate/02-gptq-awq/starter/gptq_awq.ipynb
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/intermediate/02-gptq-awq -q
---

## Mục tiêu

Tự cài hai thuật toán PTQ có hiệu chỉnh được dùng nhiều nhất cho LLM, GPTQ (bù sai số theo Hessian) và AWQ (scale theo độ lớn
activation), ở mức một `nn.Linear`, rồi áp lên cả GPT mini và so với round-to-nearest ở cùng số bit. Làm xong bạn hiểu các
tham số `damp_percent`, `group_size`, `desc_act`, `sym` của các công cụ GPTQ/AWQ (GPTQModel, `llm-compressor`) nghĩa là gì.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Thời gian máy chạy hết notebook lời giải: khoảng 4 phút trên CPU (4 luồng, checkpoint cấu
hình PC, 20 bài validation); khoảng 2 phút trên GPU dùng chung (đủ 100 bài; GPTQ/AWQ vẫn chạy trên CPU).

Checkpoint như bài Intermediate 01. Trong `starter/gptq_awq.ipynb` (`rtn_quantize`, `quant_params`, `quant_column` cho sẵn):

1. `capture_inputs(model, batches, names)`: input của từng lớp trên dữ liệu hiệu chỉnh, bằng forward hook.
2. `hessian(X, damp)`: $$\frac{2}{N}X^\top X$$ cộng dampening tương đối.
3. `gptq_quantize(W, H, bits, group_size, symmetric)`: duyệt cột theo thứ tự, bù sai số bằng nhân tử Cholesky của $$H^{-1}$$.
4. `awq_scales(x_absmean, alpha)` và `awq_quantize(W, X, bits, group_size, n_grid, symmetric)`: tìm $$\alpha$$ trên lưới.
5. `apply_layerwise(model, inputs, quantize_fn)`: áp một phương pháp lên mọi lớp, trả bản sao.

Rồi chạy các cell `explore`: 32 đoạn hiệu chỉnh từ tập train, thống kê ngoại lai activation theo kênh, bảng RTN/GPTQ/AWQ ở
3 cấu hình (int4 nhóm 128, int3 nhóm 128, int3 nhóm 32 zero-point), và so sai số trọng số với sai số đầu ra từng lớp. Cuối cùng
làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `capture_inputs` trả đúng input (đưa lại vào lớp cho ra đúng output đã ghi), nối các batch, gỡ hook.
- `hessian` đúng công thức và dampening tương đối, kiểu `float64`.
- `gptq_quantize`: với $$H = I$$ trùng RTN; trên ví dụ 3 cột tính tay, bù sai số đúng chiều, đúng thứ tự; tham số của nhóm
  tính từ trọng số **đã được cập nhật**; trên Hessian dày 4-6 cột khớp phép Optimal Brain Surgeon trực tiếp (nghịch đảo lại
  Hessian của các cột còn tự do ở mỗi bước); không sửa `W` đầu vào; trên dữ liệu có tương quan, sai số đầu ra nhỏ hơn RTN rõ rệt.
- `awq_scales` đúng công thức chuẩn hoá; `awq_quantize` dùng trung bình $$\lvert x\rvert$$ theo kênh, hoà thì giữ $$\alpha$$ nhỏ
  nhất, với lưới một điểm trùng RTN, chọn $$\alpha > 0$$ và giảm sai số đầu ra
  hơn một nửa khi có vài kênh activation lớn gấp trăm lần.
- `apply_layerwise` gọi đúng hàm cho đúng lớp, không sửa model gốc, giữ weight tying.

## Gợi ý

### Gợi ý 1

Viết GPTQ theo đúng ba bước trong notebook trước, kiểm bằng $$H = I$$ (phải ra RTN) và bằng ví dụ 2 cột: sau khi quantize cột 0,
cột 1 nhận thêm $$(w_0 - q_0)\,H_{01}/H_{11}$$. Nếu kết quả ngược dấu, xem lại bạn trừ $$e\,U_{j,j+1:}$$ hay cộng.

### Gợi ý 2

`torch.cholesky_inverse(L)` nhận nhân tử Cholesky **dưới** $$L$$ của $$H$$ và trả $$H^{-1}$$; `torch.linalg.cholesky(A,
upper=True)` cho nhân tử trên. Tính $$U$$ một lần trước vòng lặp. Với AWQ, phép nhân $$W \cdot s$$ broadcast theo cột (mỗi kênh
input một hệ số), và sai số đo trên **đầu ra** $$XW^\top$$, không trên trọng số.
