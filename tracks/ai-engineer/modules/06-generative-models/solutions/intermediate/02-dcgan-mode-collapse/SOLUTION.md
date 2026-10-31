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

Env gốc (CPU, 4 luồng), torch 2.14.1, seed 0; cả notebook 13 phút 37 giây (phần 2D 333 giây, mỗi cấu hình DCGAN khoảng 2 phút).

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
| Chuẩn, saturating | **0.074** | **5** | **0.945** | 0.987 / 0.008 | `[15, 0, 3881, 2072, 61, 456, 0, 247, 3219, 49]` |
| D mạnh (lr D 2e-3), NS | 0.363 | 9 | 0.357 | 0.816 / 0.180 | `[491, 78, 1344, 3324, 690, 633, 129, 1133, 622, 1556]` |
| D mạnh, saturating | **0.093** | **3** | **1.208** | **1.000 / 0.000** | `[1, 16, 3949, 3829, 0, 2180, 0, 8, 17, 0]` |

Kernel `ai-gpu` (PC, 15 epoch × 60 000 ảnh, cả notebook 16 phút; giám khảo test accuracy 0.9838). Hai lần chạy cùng seed trên GPU **không** cho cùng
số (conv transpose và BatchNorm trên CUDA không tất định), và với cấu hình D mạnh + saturating chúng khác nhau về chất:

| Cấu hình (GPU) | Tự tin > 0.9 | Số lớp ≥ 1% | KL tới đều | D(G(z)) epoch 1 / cuối | Histogram 10 lớp |
| --- | --- | --- | --- | --- | --- |
| Chuẩn, NS | 0.630 | 10 | 0.040 | 0.288 / 0.330 | `[1131, 742, 913, 1174, 1015, 702, 676, 1455, 718, 1474]` |
| Chuẩn, saturating | 0.607 | 10 | 0.035 | 0.073 / 0.306 | `[1079, 724, 876, 1227, 1070, 867, 671, 1446, 690, 1350]` |
| D mạnh, NS | 0.607 | 10 | 0.033 | 0.157 / 0.224 | `[956, 823, 912, 1265, 1085, 635, 687, 1410, 860, 1367]` |
| D mạnh, saturating (lần 2) | 0.605 | 10 | 0.068 | **0.003** / 0.171 | `[1272, 654, 764, 1282, 778, 819, 618, 1634, 626, 1553]` |
| D mạnh, saturating (lần 1, notebook trước khi thêm cấu hình chuẩn saturating) | **0.000** | **2** | **2.171** | 0.021 / **0.000** | `[0, 9710, 0, 0, 0, 290, 0, 0, 0, 0]` |

Ở lần 1, từ epoch 2 $$D(x) = 1.000$$, $$D(G(z)) = 0.000$$, loss G bằng -0.000 và ở epoch 8 G sụp về gần như một lớp (97% mẫu được chấm là chữ 1). Ở lần 2,
epoch đầu cũng gần như sụp ($$D(G(z)) = 0.003$$, giám khảo 0.000, 4 lớp) nhưng G thoát ra được và tới epoch 15 thì đuổi kịp NS. Với 15 epoch trên đủ dữ
liệu, saturating ở lr chuẩn cũng ổn trên GPU, khác với cấu hình CPU ngắn. Thứ **tái lập được** qua cả ba lần chạy (CPU, hai lần GPU) là epoch đầu: với
D mạnh, saturating có $$D(G(z))$$ chỉ 0.003 tới 0.021, còn NS là 0.09 tới 0.16.

Đọc kết quả:

- **Collapse do G "đuổi" một D đứng yên.** Cho G 5 bước mỗi bước D, cả ba seed gần như không phủ mode nào (1, 0, 0) và gần như không có mẫu chất lượng
  cao, nhưng theo hai cách: seed 1 và 2 co về gần một điểm (độ trải 0.14 và 0.10 so với 1.41 của dữ liệu), đúng nghĩa đen của mode collapse; seed 0
  vẫn dàn ra (độ trải 1.03) mà lệch khỏi mọi mode. G tối ưu theo một D gần như đứng yên thì dồn mẫu về vùng D đang chấm cao, vùng đó không nhất thiết
  trùng dữ liệu. Loss G lúc đó vẫn giảm đẹp.
- **Saturating và NS như nhau trên vòng 8 Gauss, nhưng không như nhau trên DCGAN.** Với MLP nhỏ trên dữ liệu 2D, hai loss phủ đủ 8 mode như nhau. Với
  DCGAN trên MNIST, D phân biệt ảnh thật và giả dễ hơn hẳn ngay từ đầu, và với ngân sách CPU ngắn bản saturating hỏng **ngay ở lr chuẩn**: $$D(G(z))$$ chỉ còn 0.008, giám khảo
  tự tin 0.074, 5 lớp, KL 0.945; bản NS cùng cấu hình học được 9 lớp. Khi D còn mạnh hơn (lr gấp 10), saturating hỏng nặng hơn (3 lớp, $$D(G(z))$$ về
  0.000, loss G về -0.000) còn NS vẫn học được. Trên GPU với ngân sách dài hơn, saturating có lúc hồi phục, có lúc sụp hẳn (bảng GPU): hỏng của nó là
  **ngẫu nhiên**, còn NS học được ở mọi lần chạy. Đó là lý do NS là mặc định: gradient của nó không biến mất khi D thắng. Kết luận về GAN cần nhiều
  seed; một lần chạy may mắn không chứng minh cấu hình an toàn.
- **WGAN-GP** phủ đủ 8 mode ở cả 3 seed, nhưng mẫu ít "sắc" hơn (35% chất lượng cao so với khoảng 58% của NS) với cùng số vòng: khoảng cách
  Wasserstein cho gradient ổn định, đổi lại hội tụ chậm hơn và tốn 5 lần bước critic.
- Với ngân sách CPU, ngay cả DCGAN chuẩn cũng **lệch lớp**: chữ 3 chiếm 30% mẫu, chữ 1 chỉ 0.6% (9/10 lớp). KL 0.3 là một mức "collapse nhẹ" mà mắt
  nhìn lưới 64 ảnh không thấy; chỉ histogram mới thấy, và nó giảm dần khi train lâu hơn (bảng GPU).

## Bẫy thường gặp

- Một batch chung `cat([real, fake])` qua D có BatchNorm: thống kê batch trộn thật và giả, D học khác hẳn (DCGAN gốc đưa riêng rẽ).
- Đánh giá G ở chế độ train (BatchNorm dùng thống kê batch của chính mẫu sinh): kết quả phụ thuộc kích thước batch sinh.
- Nhìn loss G giảm rồi kết luận "đang tốt": ở cấu hình D mạnh + saturating, loss G gần 0 đúng lúc G hỏng nặng nhất.
- Số liệu thay đổi theo device và số luồng (chuỗi số ngẫu nhiên khác nhau trên CPU và GPU), và trên GPU còn đổi giữa hai lần chạy cùng seed (các
  kernel CUDA không tất định). Với một GAN gần ranh giới hỏng như D mạnh + saturating, điều đó đủ để đổi kết cục.
