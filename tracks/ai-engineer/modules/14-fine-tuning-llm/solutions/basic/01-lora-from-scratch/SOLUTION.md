# Lời giải: tự cài LoRA trên nn.Linear

## Cách làm

**Phép tính.** Lớp gốc $$y = x W^\top + b$$, $$W \in \mathbb R^{d_{out} \times d_{in}}$$. LoRA thêm
$$\Delta W = \frac{\alpha}{r} B A$$ với $$A \in \mathbb R^{r \times d_{in}}$$, $$B \in \mathbb R^{d_{out} \times r}$$:

$$
y = x W^\top + b + \frac{\alpha}{r}\,\big(\mathrm{dropout}(x)\, A^\top\big) B^\top
$$

Tính theo thứ tự `x @ A.T @ B.T` (qua chiều $$r$$ nhỏ) thay vì dựng $$B A$$ rồi nhân: với $$d = 896$$, $$r = 16$$, cách
đầu tốn $$2 \cdot 896 \cdot 16$$ phép nhân mỗi token thay vì $$896^2$$.

**Khởi tạo.** $$B = 0$$ nên $$\Delta W = 0$$ lúc đầu: model sau khi gắn LoRA cho **đúng** output của model gốc, train bắt
đầu từ điểm đã biết là tốt. $$A$$ phải ngẫu nhiên: gradient của $$A$$ là $$\frac{\alpha}{r} B^\top \cdot (\ldots)$$,
bằng 0 khi $$B = 0$$, nên ở bước đầu chỉ $$B$$ học (đúng điều test kiểm), sang bước sau $$B \ne 0$$ thì $$A$$ học theo.
Nếu cả hai bằng 0 thì cả hai gradient bằng 0 mãi mãi; nếu đảo (A = 0, B ngẫu nhiên) thì vẫn chạy được nhưng khác chuẩn
của PEFT và paper. `kaiming_uniform_(a=sqrt(5))` cho phân phối đều trong $$\pm 1/\sqrt{d_{in}}$$, giống khởi tạo mặc
định của `nn.Linear`.

**Đóng băng.** `requires_grad_(False)` cho `base.weight`, `base.bias`; `inject_lora` đóng băng **cả model** trước (embedding,
norm, lớp không phải đích) rồi mới gắn LoRA, vì tham số mới tạo ra mặc định `requires_grad=True`. Optimizer chỉ nhận
tham số còn `requires_grad`, nên state của AdamW chỉ tốn cho vài triệu tham số LoRA.

**Merge.** `base.weight += delta_weight()` (trong `no_grad`, tính ở fp32 rồi đổi về dtype gốc), đặt cờ `merged` để
`forward` bỏ nhánh LoRA và để gọi lại không cộng hai lần. `merge_and_unload` thay mỗi `LoRALinear` bằng chính
`nn.Linear` bên trong: model xuất ra giống hệt kiến trúc gốc, phục vụ không tốn thêm độ trễ nào.

## Con số

Với `r = 16` trên cả 7 lớp tuyến tính của mỗi tầng (`q, k, v, o, gate, up, down`), Qwen2.5-0.5B có
$$24 \times 16 \times \big[(896 + 896) \cdot 2 + (896 + 128) \cdot 2 + (896 + 4864) \cdot 3\big] = 8\,798\,208$$ tham số
train được, 1.78% của 494 032 768; đúng bằng số PEFT in ra. Chỉ `q_proj`, `v_proj` thì còn 1 081 344.

## Bẫy thường gặp

- `scaling = alpha` (quên chia `r`) hoặc `r / alpha`: đổi `r` là đổi luôn learning rate hiệu dụng của nhánh LoRA.
- Áp dropout lên `x` trước cả lớp gốc: output của model gốc bị nhiễu khi train. Dropout chỉ thuộc nhánh LoRA.
- Gắn LoRA mà không đóng băng phần còn lại: test đếm tham số và PEFT sẽ lệch, VRAM cho optimizer tăng vọt.
- Sửa cây module trong lúc duyệt `named_modules()`: lớp vừa thay bị duyệt tiếp, bọc LoRA hai lần.
- Merge vào trọng số bf16: phép cộng làm tròn, nên `unmerge` không trả **chính xác** trọng số cũ (ở fp32 như test thì sai
  số cỡ `1e-7`). Khi cần đổi adapter liên tục, giữ trọng số gốc và không merge.
