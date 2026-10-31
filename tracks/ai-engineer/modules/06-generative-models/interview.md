# Câu hỏi phỏng vấn: Generative Models

## So sánh autoencoder, VAE, GAN và diffusion. Khi nào bạn chọn họ nào?

Bốn họ khác nhau ở cách định nghĩa và học $$p(x)$$:

| Họ | Học bằng | Sinh mẫu | log p(x) | Điểm mạnh | Điểm yếu |
| --- | --- | --- | --- | --- | --- |
| Autoencoder | tái tạo | không sinh được tử tế | không | nén, phát hiện bất thường | latent có "lỗ" |
| VAE | ELBO | một forward | cận dưới | latent liền, train ổn định | mẫu mờ |
| GAN | minimax | một forward | không | mẫu sắc, nhanh | mode collapse, train khó |
| Diffusion | khử nhiễu (ELBO đơn giản hoá) | 10 tới 1 000 forward | cận dưới | chất lượng và độ phủ tốt nhất | sinh chậm |

Chọn theo ràng buộc của sản phẩm: sinh ảnh chất lượng cao có điều kiện (text, class) là diffusion, thường trong latent space;
cần một lần forward thời gian thực, miền hẹp, hay một loss phụ cho ảnh sắc thì GAN; cần biểu diễn nén, phát hiện bất thường,
hay latent cho model khác thì autoencoder/VAE. Ứng viên senior nói thêm các họ này **ghép với nhau**: Stable Diffusion là VAE
(nén) + diffusion (sinh) + loss adversarial (cho decoder sắc) + CLIP (điều kiện text).

## Suy ra ELBO. Vì sao nó là cận dưới, và khi nào cận này chặt?

Với $$q(z \mid x)$$ bất kỳ:

$$
\log p(x) = \mathbb{E}_q\left[\log\frac{p(x, z)}{q(z \mid x)}\right] + \mathrm{KL}\big(q(z \mid x)\,\|\,p(z \mid x)\big)
$$

Số hạng KL không âm nên kỳ vọng đầu (ELBO) là cận dưới; bằng nhau khi $$q$$ đúng bằng posterior thật. Viết lại ELBO thành
$$\mathbb{E}_q[\log p(x \mid z)] - \mathrm{KL}(q(z \mid x)\,\|\,p(z))$$: tái tạo trừ "chi phí" mã hoá. Cũng có thể suy bằng Jensen trên
$$\log\mathbb{E}_q[p(x, z)/q]$$, nhưng cách trên cho biết **khoảng hở** chính là KL tới posterior thật.

Để đo khoảng hở: cận IWAE $$\mathcal{L}_K$$ với $$K$$ mẫu. Trên VAE MLP latent 16 cho MNIST, $$-\mathcal{L}_1 = 103.5$$ và $$-\mathcal{L}_{100} = 99.8$$
nats/ảnh: khoảng 3.7 nats là cái giá của posterior Gauss đường chéo. Muốn hẹp lại: posterior linh hoạt hơn (normalizing flow trên
$$q$$), hoặc train bằng chính $$\mathcal{L}_K$$ (IWAE).

## Reparameterization trick là gì, vì sao cần nó, và khi nào không dùng được?

ELBO có kỳ vọng theo $$q_\phi$$, nên lấy gradient theo $$\phi$$ phải đi "qua" phép lấy mẫu. Viết $$z = \mu_\phi + \sigma_\phi\odot\varepsilon$$ với
$$\varepsilon \sim \mathcal{N}(0, I)$$ cố định: kỳ vọng chuyển sang theo $$\varepsilon$$, gradient đi qua $$\mu, \sigma$$ bằng autograd thường. Phương sai thấp
hơn hẳn score function estimator (REINFORCE): trên bài $$\nabla_\mu\mathbb{E}[z^2]$$ với 100 mẫu, độ lệch chuẩn 0.194 so với 0.697.

Không dùng được khi $$z$$ **rời rạc** (không có phép biến đổi khả vi từ nhiễu sang lựa chọn rời rạc). Khi đó: score function với
baseline giảm phương sai (như policy gradient ở module 07), Gumbel-softmax (nới lỏng liên tục, có chệch), hoặc straight-through
estimator (VQ-VAE). Chi tiết hay hỏi thêm: encoder trả `logvar` chứ không phải $$\sigma$$, và $$\sigma = e^{\text{logvar}/2}$$.

## Posterior collapse là gì? Phát hiện và xử lý thế nào?

Khi số hạng KL quá mạnh hoặc decoder quá mạnh, decoder học cách bỏ qua $$z$$: $$q(z_j \mid x) = p(z_j)$$ với mọi $$x$$ ở một số chiều, KL các
chiều đó bằng 0, chúng không mang thông tin. Đo bằng **active units**, số chiều có $$\mathrm{Var}_x(\mathbb{E}_q[z_j]) > 0.01$$, và KL theo từng chiều. Trên
VAE-16 MNIST: $$\beta = 1$$ còn 16/16 chiều sống, $$\beta = 4$$ còn 12, $$\beta = 10$$ còn 6.

Nguyên nhân hay gặp nhất trong code thật không phải lý thuyết mà là **bug thang đo**: tái tạo lấy trung bình trên pixel
(`reduction="mean"`) trong khi KL cộng trên chiều latent, tương đương $$\beta$$ bằng số pixel. Cách chữa: sửa thang đo trước; rồi KL
annealing ($$\beta$$ từ 0 lên 1), free bits (không phạt KL dưới ngưỡng mỗi chiều), decoder yếu hơn (với decoder autoregressive cho text,
collapse gần như mặc định), hoặc dropout từ ở decoder để buộc nó dựa vào $$z$$.

## Vì sao mẫu của VAE thường mờ hơn GAN?

Decoder dự đoán tham số của $$p(x \mid z)$$, và thứ ta hiển thị là **trung bình** (hoặc mode) của nó. Mỗi $$z$$ trong vùng dày đặc của
posterior ứng với nhiều ảnh hơi khác nhau; với likelihood Gauss phương sai cố định (MSE), trung bình tối ưu là ảnh trung bình của chúng:
nét nhoè. Lấy mẫu từ $$p(x \mid z)$$ đúng nghĩa (cộng nhiễu từng pixel độc lập) còn tệ hơn: thành ảnh lấm tấm. Gốc vấn đề là likelihood
**tách rời từng pixel** không mô tả được tương quan giữa các pixel.

GAN không bị vì không có likelihood từng pixel: D đánh giá cả ảnh. Diffusion tránh bằng cách chia việc sinh thành nhiều bước nhỏ, mỗi
bước chỉ cần một Gauss gần đúng. VAE hiện đại chữa bằng decoder autoregressive, hierarchical VAE (NVAE, VDVAE), hoặc thêm loss
perceptual/adversarial (decoder của Stable Diffusion).

## Viết loss của GAN. Vì sao dùng bản "non-saturating" cho generator?

D: $$-\big[\mathbb{E}\log D(x) + \mathbb{E}\log(1 - D(G(z)))\big]$$, binary cross-entropy với nhãn thật 1, giả 0. G trong minimax gốc minimize
$$\mathbb{E}\log(1 - D(G(z)))$$. Với logit $$l$$ của mẫu giả, đạo hàm là $$-\sigma(l)$$: khi D phân biệt dễ (đầu quá trình train, $$\sigma(l) \approx 0$$),
gradient biến mất. Bản non-saturating $$-\mathbb{E}\log D(G(z))$$ có đạo hàm $$-(1 - \sigma(l)) \approx -1$$ đúng lúc đó, cùng điểm cố định. Với logit
-8: $$-0.0003$$ so với $$-0.9997$$.

Ý cài đặt cần nói: tính bằng logits với `softplus` (hay `BCEWithLogitsLoss`), không `sigmoid` rồi `log`; ở bước D phải `detach()` mẫu
giả; ở bước G cho mẫu giả qua **D đã cập nhật**. Và $$D^*(x) = p_{data}/(p_{data} + p_g)$$ biến bài toán thành minimize
$$-\log 4 + 2\,\mathrm{JS}(p_{data}\,\|\,p_g)$$.

## Mode collapse là gì, vì sao xảy ra, và bạn đo nó thế nào?

G sinh chỉ một phần các mode của dữ liệu (MNIST: chỉ vài chữ số; cực đoan: mọi $$z$$ cho cùng một ảnh). Nguyên nhân: G tối ưu để lừa D
**hiện tại**; nếu D đang coi một vùng là "rất thật", đổ mọi $$z$$ vào đó là cách giảm loss rẻ nhất. Gradient descent xen kẽ không phân biệt
được $$\min_G\max_D$$ với $$\max_D\min_G$$, và nghiệm của bài sau là collapse. Thí nghiệm dễ thấy: cho G nhiều bước cập nhật hơn D, G "đuổi"
theo một D đứng yên và gom mẫu vào ít vùng.

Đo: trên dữ liệu đồ chơi biết tâm (8 Gauss trên vòng tròn), đếm mode có đủ mẫu chất lượng cao. Trên dữ liệu thật, dùng classifier làm
giám khảo: histogram lớp của mẫu sinh, KL tới phân phối đều, số lớp vắng mặt; hoặc recall (Kynkäänniemi et al.) và FID (collapse làm
covariance co lại). Loss G và D **không** cho biết collapse. Chữa: WGAN-GP hoặc spectral norm, minibatch std, TTUR, unrolled GAN,
hoặc đổi sang diffusion.

## Giải thích forward process của DDPM và vì sao có dạng đóng q(x_t | x_0).

Forward process cộng nhiễu Gauss qua $$T$$ bước: $$x_t = \sqrt{1 - \beta_t}\,x_{t-1} + \sqrt{\beta_t}\,\varepsilon_t$$. Hệ số $$\sqrt{1 - \beta_t}$$ giữ phương sai ổn
định. Vì mọi nhiễu là Gauss độc lập, gộp lại vẫn là Gauss: $$x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1 - \bar\alpha_t}\,\varepsilon$$ với $$\bar\alpha_t = \prod_{s \le t}(1 - \beta_s)$$.
Chứng minh bằng quy nạp: phần $$x_0$$ nhân dồn các $$\sqrt{\alpha_s}$$, phần nhiễu có phương sai $$\alpha_t(1 - \bar\alpha_{t-1}) + \beta_t = 1 - \bar\alpha_t$$.

Hệ quả thực tế: mỗi bước train chọn $$t$$ ngẫu nhiên và tạo $$x_t$$ trong một phép tính, nên train rẻ như hồi quy. Lỗi hay gặp: dùng
$$\bar\alpha_t$$ thay vì $$\sqrt{\bar\alpha_t}$$ cho hệ số $$x_0$$ (tín hiệu mất nhanh gấp đôi theo log, model train trên một forward process khác với
sampler); lệch chỉ số $$t$$ một bước giữa mảng 0-based và công thức 1-based; ảnh ở $$[0, 1]$$ thay vì $$[-1, 1]$$.

## Vì sao DDPM dự đoán nhiễu chứ không dự đoán ảnh sạch? Liên hệ với score là gì?

Ba cách tham số hoá ($$\varepsilon$$, $$x_0$$, $$v$$) tương đương về toán (đổi qua lại bằng $$x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1 - \bar\alpha_t}\varepsilon$$), khác ở
trọng số ngầm theo $$t$$ khi dùng MSE. Ho et al. thấy dự đoán $$\varepsilon$$ với loss không trọng số ("simple") cho mẫu tốt nhất: output của mạng
luôn có thang đo cỡ 1 ở mọi $$t$$, dễ học hơn dự đoán $$x_0$$ khi nhiễu lớn. $$v$$-prediction ổn định hơn ở hai đầu schedule, hay dùng khi
chưng cất hoặc với zero terminal SNR.

Liên hệ score: theo Tweedie, $$\mathbb{E}[\varepsilon \mid x_t] = -\sqrt{1 - \bar\alpha_t}\,\nabla_{x_t}\log p_t(x_t)$$. Mạng dự đoán nhiễu là một bội của score
của phân phối dữ liệu đã làm nhiễu; sinh ảnh là đi theo score (Langevin, hoặc giải SDE/ODE ngược). Cách nhìn này giải thích vì sao
cộng hai score (guidance) có nghĩa, và vì sao DDIM là một bộ giải ODE.

## DDIM khác DDPM thế nào? Vì sao nó sinh được với 50 bước thay vì 1 000 mà không cần train lại?

Loss của DDPM chỉ phụ thuộc các marginal $$q(x_t \mid x_0)$$, không phụ thuộc cấu trúc Markov của forward process. DDIM chọn một quá trình
không Markov có cùng marginal, với bước ngược tất định ($$\eta = 0$$): đoán $$\hat x_0$$ và $$\hat\varepsilon$$ từ $$x_t$$, rồi đặt
$$x_{t'} = \sqrt{\bar\alpha_{t'}}\hat x_0 + \sqrt{1 - \bar\alpha_{t'}}\hat\varepsilon$$. Vì công thức này đúng cho mọi $$t' < t$$, có thể nhảy qua một dãy con các bước,
dùng nguyên model đã train. Thực chất nó là bước Euler của ODE xác suất (probability flow ODE).

Hệ quả: chất lượng gần DDPM 1 000 bước với 50 bước (bài Intermediate 03 đo được trên FashionMNIST), tất định nên cùng nhiễu ban đầu
cho cùng ảnh (nội suy, chỉnh sửa ảnh bằng cách đảo ngược DDIM). Xuống quá ít bước (10) thì sai số rời rạc hoá lộ rõ; khi đó dùng
sampler bậc cao (DPM-Solver, Heun) hoặc chưng cất (consistency model, progressive distillation).

## Classifier-free guidance hoạt động thế nào? Đánh đổi của guidance scale là gì?

Train một mạng vừa có điều kiện vừa không: với xác suất $$p_{uncond}$$ (0.1 tới 0.2) thay nhãn bằng nhãn rỗng. Khi sinh:
$$\tilde\varepsilon = (1 + w)\,\varepsilon(x_t, y) - w\,\varepsilon(x_t, \varnothing)$$. Theo Bayes, $$\varepsilon(x_t, y) - \varepsilon(x_t, \varnothing) \propto -\nabla\log p(y \mid x_t)$$, nên đây là
classifier guidance với một classifier ngầm lấy từ chính model, khỏi train classifier trên ảnh nhiễu.

Đánh đổi: $$w$$ tăng thì mẫu đúng class hơn, rõ hơn, nhưng **kém đa dạng** và lệch khỏi phân phối thật (sinh từ $$p(x)p(y \mid x)^{1+w}$$, không
phải $$p(x \mid y)$$). Trên bài đồ chơi hai Gauss với nhiễu chính xác, $$w = 7$$ đẩy mean từ 1.0 ra 2.1 và giảm std theo hướng phân biệt lớp
từ 0.49 xuống 0.24, trong khi hướng không liên quan class giữ nguyên. FID có dạng chữ U theo $$w$$, class accuracy tăng đều. Chi phí:
hai lần forward mỗi bước. Cảnh giác quy ước: nhiều thư viện dùng $$s = 1 + w$$.

## FID tính thế nào và những bẫy nào làm con số FID vô nghĩa?

Lấy feature 2048 chiều từ Inception-v3 cho ảnh thật và ảnh sinh, khớp hai Gauss, tính
$$\lVert\mu_r - \mu_g\rVert^2 + \mathrm{tr}(\Sigma_r + \Sigma_g - 2(\Sigma_r\Sigma_g)^{1/2})$$. Căn bậc hai ma trận tính qua phân rã trị riêng (hai ma trận đối xứng
nửa xác định dương), hoặc `scipy.linalg.sqrtm` rồi bỏ phần ảo nhỏ do sai số số học.

Bẫy: (1) **chệch theo số mẫu**: hai tập ảnh thật CIFAR-10 cho FID khác 0, và giảm khi tăng số mẫu (bảng ở mục 7 lý thuyết), nên chỉ so FID
cùng số mẫu; (2) **cài đặt**: trọng số Inception (TensorFlow hay torchvision), cách resize, định dạng ảnh đều đổi FID vài điểm; (3) **tập thật**
(train hay test, bao nhiêu ảnh); (4) FID **thưởng cho việc chép** tập train; (5) feature Inception được train trên ImageNet, có thể không
nhạy với lỗi quan trọng ở miền khác (ảnh y tế, chữ). KID có ước lượng không chệch, hợp với ít mẫu; precision/recall tách chất lượng
khỏi độ phủ.

## Case: bạn được giao làm tính năng "sinh ảnh sản phẩm theo danh mục" cho một sàn thương mại điện tử (khoảng 200 danh mục, 2 triệu ảnh). Thiết kế thế nào?

Khung trả lời:

1. **Làm rõ yêu cầu**: ảnh dùng để làm gì (minh hoạ danh mục, mockup cho người bán, tăng dữ liệu cho classifier)? Độ phân giải, độ trễ
   chấp nhận được, ngân sách GPU, yêu cầu pháp lý (bản quyền ảnh của người bán, không sinh logo thương hiệu thật).
2. **Chọn cách tiếp cận theo chi phí tăng dần**: (a) dùng model text-to-image mở có sẵn với prompt theo danh mục, đánh giá trước; (b) fine-tune
   nhẹ (LoRA, module 14) trên ảnh của sàn với nhãn danh mục thành text; (c) train một latent diffusion có điều kiện danh mục từ đầu chỉ
   khi (a), (b) không đạt và dữ liệu đủ lớn. Hầu hết dừng ở (b).
3. **Điều kiện và guidance**: danh mục như class (embedding) hoặc text; CFG với $$p_{uncond} \approx 0.1$$, quét $$w$$ trên tập validation.
4. **Dữ liệu**: lọc trùng lặp gần (giảm thuộc lòng), lọc ảnh có chữ/logo/watermark, cân bằng danh mục (danh mục hiếm cần trọng số hoặc
   oversample), tách tập test theo người bán để đo khái quát.
5. **Đánh giá**: FID/KID theo từng danh mục với số mẫu cố định, classifier danh mục chấm độ đúng điều kiện, kiểm tra thuộc lòng bằng
   nearest neighbor trong tập train, và đánh giá người (A/B với ảnh thật) trước khi ra mắt.
6. **Serving**: sampler ít bước (DPM-Solver 20 bước hoặc model chưng cất 4 bước), batch theo danh mục, cache ảnh cho các yêu cầu phổ biến,
   lọc an toàn đầu ra, đánh dấu ảnh là AI sinh.

Ứng viên tốt nói rõ con số: chi phí mỗi ảnh (số bước × thời gian forward), và hỏi "ảnh sinh thay thế cái gì": nếu chỉ để minh hoạ danh mục,
một bộ ảnh tuyển chọn tay rẻ hơn mọi model.

## Case: model diffusion của team train 3 ngày, loss giảm đẹp nhưng ảnh sinh ra toàn nhiễu xám hoặc màu bị lệch. Bạn debug thế nào?

Loss giảm đẹp nghĩa là mạng học được **một** bài toán khử nhiễu; ảnh rác nghĩa là sampler giải một bài toán **khác**. Tìm chỗ train và sinh
không khớp, từ rẻ tới đắt:

1. **Kiểm sampler bằng oracle**: dữ liệu là một ảnh duy nhất $$x^*$$, nhiễu "đoán đúng" là $$(x_t - \sqrt{\bar\alpha_t}x^*)/\sqrt{1 - \bar\alpha_t}$$; sampler đúng phải
   trả về đúng $$x^*$$. Không cần GPU, khoanh vùng ngay lỗi ở sampler (căn bậc hai thiếu, variance sai, cộng nhiễu ở bước cuối, lệch chỉ số).
2. **So schedule giữa train và sinh**: cùng $$T$$, cùng loại schedule, cùng quy ước chỉ số (0-based và 1-based), cùng giá trị $$t$$ đưa vào time
   embedding (có code chia $$t$$ cho $$T$$ một chỗ mà không chia ở chỗ kia).
3. **Thang dữ liệu**: train trên $$[-1, 1]$$ hay $$[0, 1]$$; khi lưu ảnh có đảo chuẩn hoá đúng không (màu lệch thường do đây, hoặc RGB/BGR,
   hoặc mean/std của chuẩn hoá theo kênh).
4. **Trọng số và chế độ**: sinh bằng EMA hay trọng số thô, EMA có được cập nhật thật không, model có ở `eval()` không (dropout).
5. **Đo theo $$t$$**: loss tách theo khoảng $$t$$; ảnh $$\hat x_0$$ dự đoán từ $$x_t$$ của ảnh thật ở vài mức nhiễu. Nếu $$\hat x_0$$ đẹp mà sampler ra rác thì chắc
   chắn lỗi ở sampler.

Bài Advanced 02 của module là đúng tình huống này với năm lỗi im lặng.

## Trong công việc thực tế, AI Engineer có cần tự viết DDPM không, hay chỉ dùng diffusers?

Phần lớn thời gian dùng `diffusers` (hoặc API): scheduler, pipeline, LoRA, ControlNet đã có sẵn và được tối ưu. Nhưng hiểu từ bên trong
trả lãi ở những chỗ thư viện không quyết thay bạn: chọn scheduler và số bước theo ngân sách độ trễ (hiểu DDIM là bộ giải ODE thì biết vì sao
DPM-Solver 20 bước đủ); đọc đúng "guidance scale" của từng thư viện; biết vì sao model sinh ảnh tối kém (zero terminal SNR, cách chọn dãy bước);
debug khi fine-tune ra ảnh hỏng (thang dữ liệu, chỉ số $$t$$, EMA); đánh giá đúng (FID với cùng cài đặt, kiểm thuộc lòng). Và khi cần một
model nhỏ cho miền riêng (ảnh y tế, quang phổ, dữ liệu dạng bảng), viết một DDPM 300 dòng thường nhanh hơn ép một pipeline text-to-image vào
bài toán không hợp.
