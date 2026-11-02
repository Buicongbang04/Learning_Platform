---
title: DDPM và DDIM tự viết trên FashionMNIST
level: intermediate
services: []
files:
  - path: starter/ddpm.ipynb
    note: 1 lớp, 7 hàm TODO
  - path: tests/test_ddpm_fashion.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/03-ddpm-fashion-mnist/starter/ddpm.ipynb
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/03-ddpm-fashion-mnist -q
---

## Mục tiêu

Ghép các mảnh của bài Basic 03 thành một diffusion model hoàn chỉnh: U-Net nhỏ có time embedding, loss "simple", sampler DDPM tổ tiên
1 000 bước và DDIM ít bước, EMA trọng số. Rồi đo đánh đổi thật sự của người làm diffusion: số bước sinh so với chất lượng, EMA, kẹp
$$\hat x_0$$, schedule linear so với cosine; và đối chiếu từng con số với `diffusers` sau khi đã tự viết.

## Đề bài

**Phần cứng:** GPU 4GB · ~180 phút

Thời gian trên là thời gian làm bài. Kernel `ai-gpu`: train 8 000 bước cho mỗi schedule (khoảng 5 phút mỗi model trên RTX 3060, chậm hơn trên laptop),
cả notebook khoảng 20 phút. Env gốc (CPU) tự chuyển sang 600 bước, 64 mẫu, một schedule: khoảng 10 phút, đủ để kiểm code chạy hết, mẫu còn mờ.
Lần đầu cell đầu tiên tải FashionMNIST (30 MB) vào `data/raw/fashion-mnist` bằng `torchvision`. Test chạy trên CPU với model tí hon và
"oracle" dạng đóng, vài giây.

Đọc mục 5 phần lý thuyết. Mở `starter/ddpm.ipynb`:

1. `make_schedule(T, kind)`: linear hoặc cosine, float32.
2. `sinusoidal_embedding(t, dim)` và `ResBlock(cin, cout, tdim)` đúng mô tả; cell sau (không chấm) ghép chúng thành `UNet`.
3. `ddpm_loss(model, x0, schedule, generator)`, `ddpm_sample(model, shape, schedule, generator, clip)`,
   `ddim_sample(model, shape, schedule, steps, generator, clip)`: đúng thứ tự lấy số ngẫu nhiên như mô tả trong notebook.
4. `EMA(model, decay)` với `shadow`, `update`, `copy_to`.

Rồi chạy các cell `explore`: nhìn forward process của hai schedule, train classifier giám khảo, train DDPM, so các sampler (DDPM 1 000 bước
có và không EMA, DDIM 100/50/20/10 bước, DDIM không kẹp), so linear với cosine (chỉ GPU), đối chiếu với `diffusers`. Sau đó làm phần trắc nghiệm
của bài trong app.

## Tiêu chí đạt

- `make_schedule` đúng hai loại, float32; `sinusoidal_embedding` đúng thứ tự sin rồi cos và tần số; `ResBlock` đúng công thức và time embedding
  làm đổi output; `UNet` ráp được (1 045 729 tham số).
- `ddpm_loss` khớp một cài đặt tham chiếu với cùng generator; `ddpm_sample` và `ddim_sample` khớp từng số với bản tham chiếu (có và không kẹp,
  DDIM với số bước bằng và nhỏ hơn $$T$$).
- Với nhiễu "oracle" của dữ liệu chỉ có một ảnh, cả hai sampler trả đúng ảnh đó; kẹp áp lên $$\hat x_0$$; với dữ liệu Gauss từng pixel và nhiễu
  tối ưu dạng đóng, DDPM 1 000 bước cho mẫu đúng mean và độ lệch chuẩn.
- `EMA` là bản sao riêng, cập nhật đúng công thức, chép buffer kiểu nguyên, `copy_to` nạp đúng.

## Gợi ý

### Gợi ý 1

Viết sampler trước rồi kiểm bằng "oracle" ngay trong notebook: nếu dữ liệu chỉ có một ảnh $$x^*$$ thì nhiễu tối ưu là
$$(x_t - \sqrt{\bar\alpha_t}\,x^*)/\sqrt{1 - \bar\alpha_t}$$, một sampler đúng phải trả lại đúng $$x^*$$. Phép thử này không cần train và bắt được gần
mọi lỗi chỉ số, căn bậc hai, variance. Các test của bài dùng đúng ý đó.

### Gợi ý 2

Ở bước cuối (`t = 0`), $$\bar\alpha$$ "trước đó" bằng 1: mean của posterior đúng bằng $$\hat x_0$$ và variance bằng 0, nên không cộng nhiễu. Trong DDIM, khi
kẹp $$\hat x_0$$ phải tính lại $$\hat\varepsilon = (x_t - \sqrt{\bar\alpha_t}\,\hat x_0)/\sqrt{1 - \bar\alpha_t}$$ để hai đại lượng nhất quán. EMA: `state_dict()` trả
tensor dùng chung bộ nhớ với model, nên `shadow` phải là `clone()`.
