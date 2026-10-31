# Lời giải: DDPM và DDIM tự viết trên FashionMNIST

## Cách làm

**Schedule.** Tính $$\beta$$ bằng float64 (linear: `linspace`; cosine: $$\bar\alpha(u) = f(u)/f(0)$$, $$\beta_t = 1 - \bar\alpha(t + 1)/\bar\alpha(t)$$, chặn 0.999), `cumprod` bằng
float64 rồi mới đổi sang float32. Tích luỹ 1 000 thừa số bằng float32 lệch khoảng 1e-6 tương đối, nhỏ nhưng là lý do test so tới `assert_close`
mặc định của float32.

**Time embedding và ResBlock.** $$\omega_i = \exp(-\ln(10000)\,i/h)$$, nối `[sin | cos]`. Trong `ResBlock`, chiếu embedding bằng `Linear(tdim, cout)` rồi
cộng như một bias theo kênh (`[:, :, None, None]`): mỗi mức nhiễu dịch các feature map một lượng riêng. Đây là cách DDPM gốc làm; biến thể
mạnh hơn (FiLM, adaptive GroupNorm) nhân thêm một hệ số scale.

**Loss.** `t` rồi `noise` từ `generator` trên CPU, `.to(device)`; $$x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1 - \bar\alpha_t}\varepsilon$$; `F.mse_loss(model(x_t, t), noise)`.

**DDPM.** Mỗi bước: $$\hat\varepsilon$$, $$\hat x_0 = (x_t - \sqrt{1 - \bar\alpha_t}\hat\varepsilon)/\sqrt{\bar\alpha_t}$$, kẹp, mean posterior
$$\tilde\mu(x_t, \hat x_0)$$, cộng $$\sqrt{\tilde\beta_t}z$$ nếu $$t > 0$$. Viết qua $$\hat x_0$$ (thay vì công thức mean theo $$\varepsilon$$ của bài Basic 03) để kẹp được: hai cách
trùng nhau khi không kẹp. **DDIM.** `ts = linspace(0, T-1, steps).round()`, đi ngược; $$x_{t'} = \sqrt{\bar\alpha_{t'}}\hat x_0 + \sqrt{1 - \bar\alpha_{t'}}\hat\varepsilon$$ với
$$\hat\varepsilon$$ tính lại sau khi kẹp. Cả hai gọi `model.eval()` và chạy trong `torch.no_grad()`.

**EMA.** `shadow = {k: v.detach().clone()}`; `update`: `shadow.mul_(d).add_(v, alpha=1 - d)` cho tensor số thực, `copy_` cho buffer nguyên. Không
`clone` thì `shadow` dùng chung bộ nhớ với model: EMA trùng trọng số hiện tại (bài Advanced 02 có đúng lỗi này).

## Test kiểm bằng gì

- **Oracle một điểm.** Dữ liệu chỉ có một ảnh $$x^*$$ thì nhiễu tối ưu là $$(x_t - \sqrt{\bar\alpha_t}x^*)/\sqrt{1 - \bar\alpha_t}$$, khi đó $$\hat x_0 = x^*$$ ở mọi bước và mọi
  sampler đúng phải trả đúng $$x^*$$. Bắt lỗi căn bậc hai, lệch chỉ số, nhầm hệ số posterior.
- **Oracle Gauss.** Dữ liệu $$\mathcal{N}(0.3, 0.2^2)$$ từng pixel có nhiễu tối ưu dạng đóng
  $$\mathbb{E}[\varepsilon \mid x_t] = \sqrt{1 - \bar\alpha_t}(x_t - \sqrt{\bar\alpha_t}m)/(\bar\alpha_t s^2 + 1 - \bar\alpha_t)$$; DDPM 1 000 bước phải sinh đúng mean và độ lệch chuẩn. Với
  schedule ngắn 50 bước, variance $$\tilde\beta$$ cho độ lệch chuẩn 0.164 thay vì 0.2: "fixed small" chỉ tối ưu khi dữ liệu là một điểm, cần $$T$$ lớn để
  sai lệch biến mất (mục 5 lý thuyết).
- **So từng số với bản tham chiếu** cho thứ tự lấy số ngẫu nhiên, kẹp, và dãy bước DDIM.

## Kết quả thật

Kernel `ai-gpu` trên PC (RTX 3060, GPU đang chia với một bài khác), torch 2.14.1, seed 0: U-Net 1 045 729 tham số, 8 000 bước, batch 128, AdamW
2e-4, EMA 0.999; mỗi model train khoảng 7.7 phút, cả notebook 23.5 phút. Giám khảo: CNN 2 epoch, test accuracy 0.8904; trên 1 000 ảnh test thật nó
tự tin > 0.9 ở **0.674** số ảnh (FashionMNIST khó hơn MNIST: áo, áo khoác, áo sơ mi dễ lẫn), 10 lớp, KL 0.010. Sinh 1 000 ảnh, cùng nhiễu ban đầu.

| Model linear, sampler | Tự tin > 0.9 | Số lớp | KL tới đều | Thời gian sinh |
| --- | --- | --- | --- | --- |
| DDPM 1 000 bước, EMA | **0.499** | 10 | 0.064 | 108.5 s |
| DDPM 1 000 bước, trọng số thô | 0.433 | 10 | 0.262 | 107.9 s |
| DDIM 100 bước, EMA | 0.448 | 10 | 0.060 | 11.0 s |
| DDIM 50 bước, EMA | 0.445 | 10 | 0.059 | 5.5 s |
| DDIM 20 bước, EMA | 0.424 | 10 | 0.068 | 2.2 s |
| DDIM 10 bước, EMA | 0.380 | 10 | 0.078 | 1.1 s |
| DDIM 50 bước, EMA, không kẹp | 0.450 | 10 | 0.052 | 5.5 s |
| `DDIMScheduler` của diffusers 50 bước, cùng model | 0.453 | 10 | 0.080 | |

Linear và cosine cùng ngân sách (seed nhiễu khác bảng trên): loss 500 bước cuối 0.0400 và 0.0721; DDIM 50 bước 0.471 và 0.420; DDPM 1 000 bước
0.466 và 0.485. `alpha_bars` của bạn lệch `diffusers` tối đa 2.4e-07 (linear) và 3.0e-07 (cosine), đúng mức làm tròn float32.

Đọc kết quả:

- **Loss không phải thước đo chất lượng**: loss giảm từ 0.182 xuống 0.040 (linear) rồi gần như đứng yên, còn mẫu vẫn khác nhau rõ giữa các
  sampler. Loss của cosine cao gần gấp đôi linear mà mẫu ngang ngửa: cosine dành nhiều bước hơn ở mức nhiễu nhỏ, nơi đoán đúng nhiễu từ một ảnh gần
  sạch là việc khó, nên loss trung bình cao hơn. So loss chỉ có nghĩa giữa hai model cùng schedule.
- **DDIM 50 bước nhanh gấp 20 lần** DDPM 1 000 bước, mất khoảng 0.05 điểm "tự tin" theo giám khảo; xuống 10 bước thì mất thêm 0.065, sai số rời rạc
  hoá bắt đầu lộ (mẫu mịn và mờ hơn). Với 1 000 mẫu, đổi seed nhiễu đã làm lệch khoảng 0.03 (0.445 so với 0.471 cho cùng cấu hình), nên chênh lệch
  giữa 100 và 50 bước là trong nhiễu đo.
- **EMA** thắng rõ nhất ở **độ đa dạng**: KL tới phân phối đều 0.064 so với 0.262 của trọng số thô (trọng số thô ở một bước bất kỳ thiên về vài lớp,
  tuỳ batch gần nhất). Đây là lý do mọi codebase diffusion đều sinh bằng EMA.
- **Kẹp $$\hat x_0$$** gần như không đổi gì ở 50 bước với model đã train tốt; nó quan trọng khi model còn kém hoặc ít bước (trên CPU 600 bước, bản không kẹp
  khác hẳn). `DDIMScheduler` của `diffusers` với cùng model cho kết quả cùng mức, dù dãy bước khác (`[980, 960, ...]`).
- Env gốc (CPU, 600 bước, 64 mẫu) chỉ để kiểm code: loss cuối 0.060, mẫu mờ, và EMA 0.999 sau 600 bước còn mang phần lớn trọng số khởi tạo nên tệ
  hơn trọng số thô (0.062 so với 0.203). Khi train ngắn, chọn decay sao cho $$1/(1 - d)$$ nhỏ hơn hẳn số bước.

## Bẫy thường gặp

- Dữ liệu $$[0, 1]$$ thay vì $$[-1, 1]$$; kẹp vào $$[-1, 1]$$ khi dữ liệu không ở miền đó.
- DDIM kẹp $$\hat x_0$$ nhưng không tính lại $$\hat\varepsilon$$: hai đại lượng mâu thuẫn, ảnh lệch sáng tối khi số bước ít.
- Sinh bằng model ở chế độ train (dropout) hoặc quên nạp EMA; đánh giá bằng loss thay vì mẫu.
- Dãy bước của `diffusers` (`[980, 960, ...]`, "leading") khác `linspace(0, 999, 50)`: so số với thư viện phải cùng dãy.
