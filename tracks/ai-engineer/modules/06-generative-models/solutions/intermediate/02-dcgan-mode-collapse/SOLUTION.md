# Lời giải: GAN đồ chơi, DCGAN và mode collapse

## Cách làm

**Vòng 8 Gauss.** `ring_centers`: góc $$2\pi k/n$$, toạ độ $$(r\cos, r\sin)$$. `ring_data`: `randint` chọn mode, cộng `std * randn`, cả hai từ `generator`.

**DCGAN.** Đúng bảng trong notebook; `bias=False` cho hai conv transpose trước BatchNorm của G và conv thứ hai của D (BatchNorm trừ mean theo
batch nên bias đứng trước nó bị triệt tiêu, $$\beta$$ của BN làm thay). G nhận `z` shape `(B, z_dim)` và reshape thành `(B, z_dim, 1, 1)`: conv transpose
kernel 7 biến một "pixel" thành feature map 7×7. D trả `net(x).flatten()`, là logit; không sigmoid vì loss tính bằng logits. `dcgan_init` kiểm
kiểu module rồi `nn.init.normal_`, dùng với `model.apply`.

**`gan_step`.**

1. `z` từ `generator` trên CPU rồi `.to(device)`, `fake = G(z)` một lần.
2. Bước D: `D(real)` và `D(fake.detach())`, loss bằng `softplus` (bài Basic 02), `opt_d.zero_grad()`, `backward`, `opt_d.step()`. `detach` cắt
   graph về G: không có nó thì `backward` của loss D tích gradient vào tham số G (rồi bị `opt_g.zero_grad()` xoá, nên chỉ tốn tính toán, nhưng nếu
   ai đó đổi thứ tự `zero_grad` thì G nhận gradient ngược dấu).
3. Bước G: `D(fake)` **lần nữa** (D vừa cập nhật), loss non-saturating `softplus(-l)` hoặc saturating `-softplus(l)`, `opt_g.zero_grad()`, `backward`,
   `opt_g.step()`. Gradient của loss G cũng chảy vào D, nhưng bước D sau gọi `opt_d.zero_grad()` trước nên không sao. Dùng lại logits cũ của bước D
   (trước cập nhật) là lỗi mà test so tham số bắt được.

**`class_histogram`.** `bincount` → tần suất $$\hat p$$; số lớp có $$\hat p \ge$$ `min_frac`; $$\mathrm{KL}(\hat p\,\|\,u) = \sum\hat p_k\log(10\hat p_k)$$ trên các lớp $$\hat p_k > 0$$.

## Kết quả thật

Env gốc (CPU, 4 luồng), torch 2.14.1, seed 0; cả notebook 12 phút 15 giây.

**Vòng 8 Gauss** (3 000 vòng, batch 256; một mode được phủ khi có ≥ 10 mẫu trong 3 độ lệch chuẩn; độ trải là std trung bình hai trục của 2 000
mẫu, dữ liệu thật khoảng 1.41):

| Cấu hình | Mode phủ (seed 0 / 1 / 2) | Mẫu chất lượng cao | Độ trải |
| --- | --- | --- | --- |
| Saturating | 8 / 8 / 8 | 0.637 / 0.405 / 0.675 | 1.41 / 1.42 / 1.40 |
| Non-saturating | 8 / 8 / 8 | 0.650 / 0.535 / 0.577 | 1.39 / 1.41 / 1.44 |
| NS, G cập nhật 5 lần mỗi vòng | 1 / 0 / 0 | 0.012 / 0.000 / 0.000 | 1.03 / **0.14** / **0.10** |
| WGAN-GP (critic 5 lần mỗi vòng, lr 1e-4) | 8 / 8 / 8 | 0.359 / 0.320 / 0.371 | 1.36 / 1.36 / 1.37 |

Số mode phủ mỗi 500 vòng (seed 0): saturating `[2, 4, 6, 5, 8, 8]`, NS `[1, 2, 8, 5, 8, 8]`: số mode **nhảy lên xuống** trước khi ổn định, đúng
động lực "đuổi bắt" của GAN.

**DCGAN trên MNIST** (3 epoch × 20 000 ảnh, batch 128, Adam beta1 0.5; giám khảo CNN 2 epoch, test accuracy 0.9842, trên 10 000 ảnh test thật tự
tin > 0.9 là 0.951; chấm 10 000 mẫu sinh):

| Cấu hình | Tự tin > 0.9 | Số lớp ≥ 1% | KL tới đều | D(x) / D(G(z)) cuối | Histogram 10 lớp |
| --- | --- | --- | --- | --- | --- |
| Chuẩn (lr 2e-4 cả hai), NS | 0.400 | 9 | 0.315 | 0.735 / 0.266 | `[706, 56, 1264, 3029, 517, 898, 219, 1276, 453, 1582]` |
| D mạnh (lr D 2e-3), NS | 0.363 | 9 | 0.357 | 0.816 / 0.180 | `[491, 78, 1344, 3324, 690, 633, 129, 1133, 622, 1556]` |
| D mạnh, saturating | **0.093** | **3** | **1.208** | **1.000 / 0.000** | `[1, 16, 3949, 3829, 0, 2180, 0, 8, 17, 0]` |

Kernel `ai-gpu` (PC, 15 epoch × 60 000 ảnh, cả notebook 12 phút 38 giây; giám khảo test accuracy 0.9832):

| Cấu hình | Tự tin > 0.9 | Số lớp ≥ 1% | KL tới đều | D(x) / D(G(z)) cuối | Histogram 10 lớp |
| --- | --- | --- | --- | --- | --- |
| Chuẩn, NS | 0.617 | 10 | 0.042 | 0.669 / 0.331 | `[1145, 718, 916, 1235, 1051, 851, 664, 1443, 578, 1399]` |
| D mạnh, NS | 0.637 | 10 | 0.032 | 0.778 / 0.221 | `[1071, 798, 807, 1244, 1161, 785, 717, 1477, 714, 1226]` |
| D mạnh, saturating | **0.000** | **2** | **2.171** | **1.000 / 0.000** | `[0, 9710, 0, 0, 0, 290, 0, 0, 0, 0]` |

Train đủ lâu, DCGAN chuẩn cân bằng lớp hơn nhiều (KL 0.307 ở epoch 1 xuống 0.042 ở epoch 15) và D mạnh với NS cũng ổn. Cấu hình D mạnh + saturating thì
hỏng hẳn: từ epoch 2, $$D(x) = 1.000$$, $$D(G(z)) = 0.000$$, loss G bằng -0.000 (không còn gradient), và ở epoch 8 G sụp về gần như một lớp duy nhất (97% mẫu
được chấm là chữ 1, không mẫu nào classifier tự tin). Đây là mode collapse "cổ điển" kèm saturation, đúng kịch bản mục 4 lý thuyết.

Đọc kết quả:

- **Collapse do G "đuổi" một D đứng yên.** Cho G 5 bước mỗi bước D, mẫu co về gần một điểm (độ trải 0.10 và 0.14 so với 1.41 của dữ liệu) và không
  nằm trên mode nào: G tìm điểm D đang chấm cao nhất rồi dồn mọi $$z$$ vào đó. Đó là định nghĩa mode collapse, và loss G lúc đó giảm rất đẹp.
- **Saturating và NS như nhau khi D không quá mạnh** (cả trên vòng tròn lẫn cấu hình chuẩn của DCGAN). Khác biệt chỉ lộ ra khi D thắng sớm: với lr
  của D gấp 10, bản saturating mất gradient ($$D(G(z))$$ về 0.000, loss G về -0.000), G kẹt ở 3 lớp (chủ yếu 2, 3, 5); bản NS vẫn học được 9 lớp. Đó là
  lý do NS là mặc định: nó không giúp lúc mọi thứ ổn, nó cứu lúc mọi thứ lệch.
- **WGAN-GP** phủ đủ 8 mode ở cả 3 seed, nhưng mẫu ít "sắc" hơn (35% chất lượng cao so với khoảng 58% của NS) với cùng số vòng: khoảng cách
  Wasserstein cho gradient ổn định, đổi lại hội tụ chậm hơn và tốn 5 lần bước critic.
- Với ngân sách CPU, ngay cả DCGAN chuẩn cũng **lệch lớp**: chữ 3 chiếm 30% mẫu, chữ 1 chỉ 0.6% (9/10 lớp). KL 0.3 là một mức "collapse nhẹ" mà mắt
  nhìn lưới 64 ảnh không thấy; chỉ histogram mới thấy, và nó giảm dần khi train lâu hơn (bảng GPU).

## Bẫy thường gặp

- Một batch chung `cat([real, fake])` qua D có BatchNorm: thống kê batch trộn thật và giả, D học khác hẳn (DCGAN gốc đưa riêng rẽ).
- Đánh giá G ở chế độ train (BatchNorm dùng thống kê batch của chính mẫu sinh): kết quả phụ thuộc kích thước batch sinh.
- Nhìn loss G giảm rồi kết luận "đang tốt": ở cấu hình D mạnh + saturating, loss G gần 0 đúng lúc G hỏng nặng nhất.
- Số liệu thay đổi theo device và số luồng (chuỗi số ngẫu nhiên khác nhau trên CPU và GPU); thứ bậc giữa các cấu hình giữ nguyên.
