# Hướng làm: gỡ lỗi một pipeline DDPM hỏng mà không báo lỗi

Bài không có code lời giải: bản sửa chỉ là 5 chỗ, giá trị nằm ở quy trình khoanh vùng và `BUGS.md`. Dưới đây là 5 bug, triệu chứng đo
được của **từng bug khi chỉ còn mình nó** (4 bug kia đã sửa), cách phát hiện và cách sửa. Số liệu: PC (RTX 3060, GPU đang chia với bài
khác; mỗi lần chạy khoảng 3 phút), torch 2.14.1, `train()` mặc định (3 000 bước, batch 128, seed 0), sinh 1 000 ảnh DDIM 50 bước seed 1, giám khảo là CNN MNIST 2 epoch
(test accuracy 0.9842; trên 1 000 ảnh test thật: tự tin > 0.9 là 0.931, độ sáng trung bình 0.122).

## Năm bug

| # | Bug | Ở đâu | Loss 100 bước cuối | Giám khảo (EMA) | Giám khảo (thô) |
| --- | --- | --- | --- | --- | --- |
| | Đã sửa cả 5 | | 0.0273 | **0.560 / 10 / 0.167** | 0.626 / 10 / 0.155 |
| | Đủ 5 bug (notebook gốc) | | 0.0154 | 0.282 / 10 / 0.049 | 0.277 / 10 / 0.050 |
| 1 | dữ liệu ở [0, 1] | `preprocess` | 0.0180 | 0.110 / 10 / 0.611 | 0.142 / 10 / 0.578 |
| 2 | thiếu căn ở hệ số $$x_0$$ | `q_sample` | 0.0227 | 0.301 / 9 / 0.279 | 0.318 / 9 / 0.274 |
| 3 | sampler không gọi `eval()` | `ddim_sample` | 0.0273 | 0.527 / 10 / 0.173 | 0.601 / 10 / 0.159 |
| 4 | EMA không `clone` | `EMA.__init__` | 0.0273 | 0.635 / 10 / 0.156 | 0.635 / 10 / 0.156 |
| 5 | không đổi thang khi đánh giá | `postprocess` | 0.0273 | 0.658 / 10 / **-0.667** | 0.729 / 10 / -0.690 |

Mỗi dòng 1–5 là bản đã sửa cộng đúng một bug. "Giám khảo (EMA)" là bộ ba (tỉ lệ tự tin > 0.9, số lớp ≥ 1%, độ sáng trung bình) như notebook in
ra, đo trên ảnh **sau** `postprocess` của chính cấu hình đó (nên bug 5 làm giám khảo nói sai); "thô" là cùng phép đo với trọng số không EMA.

### Bug 1: dữ liệu ở [0, 1] thay vì [-1, 1]

- **Ở đâu.** `preprocess`: `images.float().unsqueeze(1) / 255.0`.
- **Triệu chứng.** Ảnh sinh xám, nền không đen: độ sáng trung bình 0.611 so với 0.122 của ảnh thật, giám khảo tự tin chỉ 0.110. Loss lại **thấp
  hơn** bản đúng (0.018 so với 0.027): dữ liệu ở thang nhỏ hơn thì nhiễu dễ đoán hơn. Loss thấp không có nghĩa là model đúng.
- **Phát hiện.** In `min`, `max`, `mean` của `preprocess(X_train[:1000])`: 0, 1, 0.13 thay vì -1, 1, -0.74. Hoặc đi vòng
  `postprocess(preprocess(x))` phải ra lại `x / 255`. Sampler kẹp $$\hat x_0$$ vào $$[-1, 1]$$ và nhiễu chuẩn có thang lớn gấp đôi tín hiệu: dữ liệu và
  sampler đang giả định hai miền khác nhau.
- **Sửa.** `images.float().unsqueeze(1) / 127.5 - 1`.

### Bug 2: forward process thiếu căn bậc hai

- **Ở đâu.** `q_sample`: `ab * x0 + (1 - ab).sqrt() * noise`.
- **Triệu chứng.** Giám khảo 0.301 (bản đúng 0.560), mất một lớp, ảnh sáng và nhoè hơn (độ sáng 0.279); loss vẫn giảm bình thường (0.023). Model học khử nhiễu cho một forward process khác (tín hiệu tắt nhanh gấp đôi theo log, phương sai không còn
  bằng 1), trong khi `ddim_sample` dùng đúng công thức với $$\sqrt{\bar\alpha}$$: train và sinh lệch nhau.
- **Phát hiện.** So `q_sample` với công thức trên giấy cho một `t` giữa (với `t = 499`: hệ số $$x_0$$ phải là 0.280, bản lỗi cho 0.079), hoặc kiểm phương
  sai: dữ liệu chuẩn hoá có phương sai khoảng 1 phải cho $$x_t$$ phương sai khoảng 1 ở mọi $$t$$ (bài Basic 03).
- **Sửa.** `ab.sqrt() * x0 + (1 - ab).sqrt() * noise`.

### Bug 3: sampler chạy model ở chế độ train

- **Ở đâu.** `ddim_sample` không gọi `model.eval()`; U-Net có dropout 0.1, `train()` để model ở chế độ train và `UNet()` mới tạo (để nạp
  EMA) cũng ở chế độ train.
- **Triệu chứng.** Nhẹ: giám khảo 0.527 so với 0.560 (dropout 0.1 làm mỗi bước khử nhiễu thêm nhiễu). Không có số nào kêu to; chỉ phép thử tất định
  mới lộ. DDIM với $$\eta = 0$$ đáng lẽ tất định, nhưng hai lần sinh cùng seed cho hai ảnh khác nhau.
- **Phát hiện.** Sinh hai lần cùng `torch.Generator().manual_seed(1)` rồi so: khác nhau là có ngẫu nhiên ngoài generator (dropout). Hoặc in
  `model.training` ngay trong `ddim_sample`.
- **Sửa.** Thêm `model.eval()` đầu `ddim_sample` (và gọi `model.train()` lại khi tiếp tục train).

### Bug 4: EMA không phải bản sao

- **Ở đâu.** `EMA.__init__`: `self.shadow = dict(model.state_dict())`. `state_dict()` trả tensor **dùng chung bộ nhớ** với tham số.
- **Triệu chứng.** Giám khảo trên "EMA" và trên trọng số thô ra **đúng cùng một bộ số** (0.635 / 10 / 0.156). Ở ngân sách 3 000 bước, EMA 0.999 thật
  còn mang một phần trọng số đầu (bản đúng: EMA 0.560 so với thô 0.626), nên bug này thậm chí làm số đẹp hơn: bằng chứng rằng "số tốt hơn" không
  chứng minh code đúng. Với train dài (bài Intermediate 03, Advanced 01), EMA thật thắng rõ. "EMA" luôn trùng trọng số hiện tại (và `update` còn nhân nhẹ tham số với $$2d - d^2$$ mỗi bước, một weight decay vô
  tình), nên mọi lợi ích của EMA biến mất mà không báo gì.
- **Phát hiện.** So `ema.shadow[k].data_ptr()` với `model.state_dict()[k].data_ptr()`; hoặc sau train, `ema.shadow` trùng hệt trọng số thô; hoặc
  giám khảo trên EMA và trên trọng số thô cho cùng một bộ số.
- **Sửa.** `{k: v.detach().clone() for k, v in model.state_dict().items()}`.

### Bug 5: đường đánh giá không đổi thang

- **Ở đâu.** `postprocess` trả `x.clamp(-1, 1)` mà không đưa về $$[0, 1]$$.
- **Triệu chứng.** Độ sáng trung bình **âm** (-0.667), ảnh lưu ra gần như đen hết. Giám khảo vẫn cho 0.658, **cao hơn** bản đúng: classifier nhận ảnh
  ngoài miền nó được train và cho điểm vô nghĩa. Ảnh sinh có thể hoàn toàn ổn nhưng mọi thứ đi sau `postprocess` (giám khảo, ảnh lưu, độ sáng) đều sai: model bị
  chấm oan. Đây là loại bug nguy hiểm nhất khi tune, vì bạn sẽ "sửa" model để chiều một thước đo hỏng.
- **Phát hiện.** Đưa ảnh **thật** qua đúng đường của ảnh sinh: `judge(postprocess(preprocess(X_test[:1000])))` phải bằng giám khảo trên ảnh thật;
  bản lỗi cho độ sáng âm.
- **Sửa.** `((x.clamp(-1, 1) + 1) / 2).float()`.

### Thứ tự gỡ gợi ý và bug che bug

Thứ tự rẻ nhất: bug 5 trước (một phép đi vòng với ảnh thật, vài giây, và sửa nó trước thì mọi số đo sau mới đáng tin), rồi bug 1 (in min/max), bug
2 (so công thức hoặc chuỗi Markov), bug 3 (chạy hai lần cùng seed), bug 4 (so `data_ptr`). Không cần train lại lần nào cho tới khi sửa xong cả 5.

Bug che bug: với đủ 5 bug, độ sáng trung bình là 0.049, trông "gần đúng" hơn bất kỳ bug đơn lẻ nào, vì bug 1 (dữ liệu dương, ảnh sinh dương) và
bug 5 (bỏ phép đổi thang) bù trừ một phần cho nhau. Sửa bug 5 trước mà chưa sửa bug 1 thì độ sáng tăng vọt (bug 1 khi chỉ còn mình nó cho 0.611): số đo xấu
đi dù bạn vừa sửa đúng một lỗi. Người không biết điều này sẽ hoàn tác bản sửa đúng. Bug 4 thì ngược lại: sửa nó làm giám khảo giảm (0.635 xuống 0.560) ở ngân sách
3 000 bước.

Checklist trước khi train diffusion lâu: (1) dữ liệu vào model đúng miền, đi vòng qua hàm đảo ngược ra đúng ảnh; (2) forward process khớp công thức và
giữ phương sai; (3) sampler trả lại đúng ảnh với oracle của dữ liệu một điểm, tất định với $$\eta = 0$$; (4) EMA là bản sao riêng, được cập nhật;
(5) ảnh thật đi qua đường đánh giá cho đúng điểm của ảnh thật; (6) chỉ sau đó mới train vài nghìn bước và nhìn mẫu.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 20 | Mọi test pass, không đổi siêu tham số, schedule, kiến trúc |
| Sửa đúng gốc | 20 | 5 bug sửa đúng chỗ; không thêm bước train, không đổi sampler hay lr để bù |
| Triệu chứng có số | 15 | Mỗi bug có con số (giám khảo, độ sáng, loss, phương sai, chênh lệch hai lần sinh) |
| Cách phát hiện | 25 | Mỗi bug có một phép thử độc lập, rẻ, chỉ ra đúng chỗ (oracle, đi vòng, so `data_ptr`, chạy hai lần...) chứ không "đọc code thấy lạ" |
| Thứ tự và tương tác | 10 | Ghi thứ tự gỡ, giám khảo sau mỗi lần sửa, và ít nhất một chỗ bug che bug (bug 5 làm sai mọi số đo khác) |
| Checklist | 10 | Checklist dùng được cho pipeline khác, mỗi mục là một phép thử chạy được |

Đạt từ 70 điểm. `BUGS.md` chỉ liệt kê dòng đã sửa mà không có triệu chứng và cách phát hiện, hoặc sửa bằng cách bù triệu chứng (vd. kẹp lại
ảnh ở chỗ khác), không quá 50 điểm.
