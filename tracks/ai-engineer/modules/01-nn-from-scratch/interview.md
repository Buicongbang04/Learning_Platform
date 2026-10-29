# Câu hỏi phỏng vấn: Neural network từ số 0

## Vì sao mạng nơ-ron cần activation phi tuyến? Hai layer Linear liền nhau không activation có tác dụng gì không?

Không có phi tuyến thì $$W_2(W_1x + b_1) + b_2 = (W_2W_1)x + (W_2b_1 + b_2)$$: chồng bao nhiêu tầng vẫn là một
phép biến đổi tuyến tính, ranh giới quyết định vẫn là một siêu phẳng. Trên XOR, logistic regression và
MLP 8 neuron ẩn **không** activation đều đạt 0.52, cùng MLP đó với tanh đạt 0.9875. Cách nhìn đúng: tầng
ẩn phi tuyến học feature, tầng cuối là model tuyến tính trên các feature đó.

Ứng viên senior nói thêm vế sau: hai Linear liền nhau không thêm khả năng biểu diễn, nhưng nếu tầng giữa
hẹp thì nó là **phân rã hạng thấp** $$W \approx W_2W_1$$, ít tham số hơn. LoRA dùng đúng ý này để fine-tune LLM
(cập nhật $$\Delta W = BA$$ với hạng $$r$$ nhỏ). Và nhắc lỗi thực tế: quên activation giữa hai tầng không báo
lỗi, model chỉ âm thầm tệ như logistic regression.

## Tự suy gradient của softmax + cross-entropy theo logits.

Với một mẫu, $$y$$ one-hot, $$p = \mathrm{softmax}(z)$$, $$L = -\sum_k y_k \log p_k$$. Viết
$$\log p_k = z_k - \log\sum_j e^{z_j}$$; đạo hàm của log-sum-exp theo $$z_i$$ là $$p_i$$, nên
$$\frac{\partial \log p_k}{\partial z_i} = \delta_{ki} - p_i$$. Suy ra

$$
\frac{\partial L}{\partial z_i} = -\sum_k y_k(\delta_{ki} - p_i) = -y_i + p_i\sum_k y_k = p_i - y_i
$$

Với loss trung bình trên batch $$N$$ mẫu thì chia thêm $$N$$. Điểm cộng khi nói được hệ quả:

- Gradient bị chặn trong $$[-1, 1]$$, tỉ lệ với mức sai, không bão hoà. So với MSE trên sigmoid có thêm thừa
  số $$p(1-p)$$, bằng gần 0 đúng lúc model sai tự tin nhất.
- Mỗi dòng gradient có tổng 0 (softmax chỉ quan tâm chênh lệch logit).
- Không bao giờ phải dựng Jacobian $$C \times C$$ của softmax, $$\mathrm{diag}(p) - pp^\top$$: ghép với CE nó rút gọn
  thành $$p - y$$. Đó là lý do framework gộp hai thứ thành một hàm (`CrossEntropyLoss` nhận logits).

Kiểm bằng code: bản numpy khớp `torch.nn.functional.cross_entropy` tới `atol=1e-12`.

## Vì sao CrossEntropyLoss nhận logits chứ không nhận xác suất? Softmax "ổn định số" nghĩa là gì?

Hai lý do. Thứ nhất, **ổn định số**: softmax ngây thơ của `[1000, 1001, 1002]` ra `nan` vì $$e^{1000}$$ tràn
thành `inf`. Softmax bất biến khi cộng hằng, nên trừ $$\max_j z_j$$ trước khi lấy mũ là đủ. Nhưng lấy log
của softmax vẫn hỏng: với `[0, 800]`, xác suất lớp đầu underflow về 0 và `log` ra `-inf`, trong khi
**log-sum-exp** cho đúng `-800`:

$$
\log p_i = z_i - m - \log\sum_j e^{z_j - m}, \qquad m = \max_j z_j
$$

Thứ hai, **gradient**: tính gộp cho thẳng $$p - y$$, không đi qua Jacobian của softmax và phép chia cho
$$p$$ (vốn có thể bằng 0).

Lỗi thường gặp: thêm softmax trước `CrossEntropyLoss` (softmax hai lần: vẫn chạy, học chậm vì gradient bị
nén), dùng `sigmoid` + `BCELoss` thay vì `BCEWithLogitsLoss`, tự viết `np.log(softmax(z))` trong code numpy.

## Viết backward cho layer Linear Z = XW + b. Làm sao nhớ không nhầm?

Với gradient đến `dZ` shape `(N, out)`:

- `dX = dZ @ W.T`, shape `(N, in)`, đưa tiếp về tầng trước;
- `dW = X.T @ dZ`, shape `(in, out)`;
- `db = dZ.sum(axis=0)`, shape `(out,)`.

Mẹo: **gradient có cùng shape với tham số**, và chỉ có một cách ghép `X (N, in)` với `dZ (N, out)` ra
`(in, out)`. Bias được broadcast cho N dòng nên backward cộng theo trục batch. Tổng quát hơn: tensor
dùng ở nhiều nơi (broadcast, fan-out, residual) thì gradient là tổng gradient từ mọi nơi, nên code tự viết
dùng `+=`.

Hệ quả thực tế người phỏng vấn hay hỏi tiếp: backward cần `X` của forward, nên mọi framework giữ
activation tới lúc backward. Bộ nhớ train lớn hơn suy luận nhiều và tăng theo batch size; gradient
checkpointing đánh đổi bằng cách tính lại. Backward mỗi Linear là hai phép nhân ma trận, forward là một:
một bước train cỡ 3 lần forward, nguồn gốc của ước lượng "6 × tham số × token" FLOPs khi train LLM.

## Bạn kiểm tra gradient tự viết thế nào? Những bẫy nào làm gradient check "báo sai"?

So với sai phân trung tâm $$\frac{f(w + \varepsilon e_i) - f(w - \varepsilon e_i)}{2\varepsilon}$$ (sai số $$O(\varepsilon^2)$$), đo sai số
**tương đối**. Float64, $$\varepsilon$$ khoảng 1e-6: dưới 1e-7 là đúng, trên 1e-4 gần như chắc có bug. MLP 2 tầng
trong module cho sai số 4e-11 tới 3e-10 ở mọi tham số, và khớp `torch.autograd` với cùng trọng số.

Bẫy:

- Check bằng **float32**: sai số làm tròn chia cho $$\varepsilon$$ thành rác.
- **ReLU sát 0**: sai phân nhảy qua chỗ gãy, sai số lớn mà code đúng. Đổi seed, batch nhỏ.
- **Ngẫu nhiên** trong forward (dropout) chưa cố định; BatchNorm phải dùng cùng batch.
- Quên trả tham số về giá trị cũ sau khi cộng $$\varepsilon$$.
- Check ở $$w = 0$$: nhiều số hạng bằng 0, che bug.

Điều quan trọng nhất: gradient check bắt được bug mà **loss không cho thấy**. Quên chia batch size làm
gradient lớn gấp $$N$$ (rel $$= \frac{N-1}{N+1}$$, 0.78 với $$N = 8$$), nhưng loss vẫn giảm như thể lr lớn hơn.

## ReLU "chết" là gì, vì sao xảy ra, phát hiện và xử lý thế nào?

Neuron ReLU chết khi pre-activation âm với **mọi** input: output luôn 0, gradient luôn 0, trọng số của nó
không bao giờ được cập nhật nữa. Nguyên nhân hay gặp nhất là một bước cập nhật quá lớn đẩy bias hoặc
trọng số vào vùng âm. Số đo thật trên MLP 784-128-10 MNIST, SGD 1 epoch:

| lr | ReLU chết | Test acc |
| --- | --- | --- |
| 0.5 | 0% | 0.9664 |
| 1.0 | 27% | 0.9552 |
| 2.0 | 98% | 0.2052 |
| 5.0 | 100% | 0.0982 |

Chỗ nguy hiểm là lr 1.0: accuracy còn 95.5% nên không ai để ý, nhưng một phần tư công suất model đã mất.

Phát hiện: đếm tỉ lệ neuron có `h.max(axis=0) == 0` trên một tập validation, log mỗi epoch. Xử lý: giảm
lr hoặc thêm warmup; khởi tạo đúng (He); thêm normalization trước activation; đổi sang Leaky ReLU, GELU,
SiLU (gradient khác 0 ở phía âm); gradient clipping nếu nguyên nhân là vài bước gradient khổng lồ.
Đừng khởi tạo bias âm.

## He init và Xavier init khác nhau thế nào? Suy ra được không?

Với $$z = \sum_{i=1}^{n_{in}} w_i x_i$$, các biến độc lập, trung bình 0: $$\mathrm{Var}(z) = n_{in}\mathrm{Var}(w)\mathbb{E}[x^2]$$. Giữ thang đo
qua forward cần $$\mathrm{Var}(w) = 1/n_{in}$$, qua backward cần $$1/n_{out}$$.

- **Xavier**: thoả hiệp $$\frac{2}{n_{in} + n_{out}}$$, suy ra cho activation gần tuyến tính quanh 0 (tanh).
- **He**: ReLU xoá nửa phân phối nên $$\mathbb{E}[\mathrm{ReLU}(z)^2] = \frac12\mathrm{Var}(z)$$; bù hệ số 2 thành $$\frac{2}{n_{in}}$$.

Thí nghiệm 10 tầng 512 neuron: ReLU + He giữ std activation 0.83 → 0.73 từ tầng 1 tới tầng 10; ReLU +
Xavier co từ 0.59 xuống 0.023 (mất √2 mỗi tầng); tanh với std 0.01 còn 3e-7; tanh với std 1 có std "đẹp"
0.98 nhưng 90.5% activation bão hoà và gradient về input nổ tới 2.7e+05.

Câu trả lời senior thêm hai điều: mặc định của `nn.Linear` là Kaiming uniform với `a=√5`, phương sai
$$\frac{1}{3n_{in}}$$, nhỏ hơn He 6 lần, nên với MLP sâu dùng ReLU không có normalization nên tự khởi tạo He. Và
khi mạng có BatchNorm/LayerNorm và residual thì khởi tạo bớt quan trọng nhiều; với Transformer, việc thu
nhỏ khởi tạo của nhánh residual (GPT-2 chia cho $$\sqrt{2L}$$) quan trọng hơn chọn Xavier hay He.

## Vanishing và exploding gradient: nguyên nhân và các lớp giải pháp?

Gradient về tầng đầu là tích các Jacobian của mọi tầng phía sau. Mỗi tầng nhân độ lớn một hệ số $$k$$ thì
sau $$L$$ tầng là $$k^L$$: sigmoid có đạo hàm tối đa 0.25, 10 tầng còn $$9.5 \times 10^{-7}$$. Nguyên nhân: khởi tạo
sai thang đo, activation bão hoà, chuỗi rất dài (RNN, cùng một ma trận nhân lặp lại), trọng số phình vì
lr lớn.

| Lớp giải pháp | Ví dụ | Chữa |
| --- | --- | --- |
| Khởi tạo | He, Xavier | cả hai |
| Activation | ReLU-family thay sigmoid ở tầng ẩn | vanishing |
| Normalization | BatchNorm, LayerNorm, RMSNorm | cả hai |
| Kiến trúc | residual connection, LSTM/GRU gating | vanishing |
| Tối ưu | gradient clipping theo norm, lr nhỏ hơn, warmup | exploding |

Cách phát hiện: log norm gradient **từng tầng**, không chỉ norm tổng. Tầng đầu nhỏ hơn tầng cuối vài bậc
là vanishing; norm tổng có những gai lớn đột ngột là exploding.

## Adam hay SGD + momentum: bạn chọn khi nào?

Mặc định là **AdamW**: ít nhạy với thang đo từng tham số, hội tụ nhanh, gần như chuẩn ngành cho
Transformer và fine-tune LLM (kèm warmup + cosine). Trên MNIST với MLP 784-128-10 sau 3 epoch, Adam lr
1e-3 đạt 0.9747, SGD lr 0.1 đạt 0.9636, SGD lr 0.01 đạt 0.9160.

Chọn **SGD + momentum** khi: train CNN cho ảnh và có thời gian tune lịch lr (thường tổng quát hoá ngang
hoặc hơn Adam); bộ nhớ chật, vì Adam giữ hai state mỗi tham số (tham số + gradient + 2 state = 4 lần bộ
nhớ tham số ở fp32, với model 7B là khác biệt hàng chục GB).

Ba điều cho thấy hiểu thật:

- Momentum kiểu PyTorch có lr hiệu dụng $$\eta/(1-\mu)$$: SGD momentum 0.9 lr 0.01 cho đường cong gần trùng
  SGD lr 0.1 (0.379/0.192/0.146 so với 0.362/0.190/0.144). So hai optimizer phải tune lr cho từng cái.
- "Adam không cần tune lr" là sai: Adam lr 1e-1 chỉ đạt 0.7288.
- Adam + `weight_decay` (L2 đi vào gradient rồi bị chia cho $$\sqrt{\hat v}$$) khác **AdamW** (decay tách riêng,
  mọi tham số bị kéo về 0 cùng tỉ lệ). Muốn regularize thì dùng AdamW.

## Vì sao Adam cần bias correction, và vì sao Transformer cần warmup?

$$m$$ và $$v$$ khởi tạo bằng 0, nên ở bước 1 $$m = (1-\beta_1)g = 0.1g$$ và $$v = 0.001g^2$$: cả hai bị kéo về 0. Chia cho
$$1 - \beta^t$$ khử đúng độ lệch đó; không có nó thì những bước đầu có độ lớn sai, nhất là với
$$\beta_2 = 0.999$$ (cần cỡ nghìn bước mới "quên" giá trị 0 ban đầu).

Warmup giải quyết chuyện khác: lúc đầu trọng số ngẫu nhiên cho gradient lớn và hỗn loạn, và $$\hat v$$ ước
lượng từ rất ít mẫu nên bước $$\hat m / \sqrt{\hat v}$$ thất thường; với Transformer (LayerNorm, attention,
nhiều tầng) một vài bước lớn đầu tiên có thể đẩy model vào vùng không phục hồi được (loss nổ hoặc
attention sụp về vài token). Tăng lr tuyến tính từ gần 0 trong vài trăm tới vài nghìn bước, rồi
cosine decay. MLP nhỏ trên MNIST thì không cần.

## BatchNorm hoạt động khác nhau thế nào giữa train và eval? Bug nào hay gặp?

Khi train, BatchNorm chuẩn hoá mỗi feature bằng mean và variance của **batch hiện tại**, đồng thời cập
nhật running stats bằng trung bình trượt (momentum 0.1 trong PyTorch). Khi eval, nó dùng running stats,
nên output một mẫu không phụ thuộc mẫu khác. Chi tiết dễ sai khi tự viết: PyTorch chuẩn hoá bằng phương sai
lệch (chia $$N$$) nhưng lưu running var **không lệch** (chia $$N-1$$); bản numpy dùng `ddof=0` cho running var
sẽ không khớp torch.

Bug hay gặp:

- Quên `model.eval()` khi đánh giá hoặc deploy: kết quả phụ thuộc thành phần batch, batch size 1 cho
  output rác, và running stats bị "nhiễm" dữ liệu đánh giá.
- Batch size nhỏ (1 tới 8): thống kê batch nhiễu, train không ổn định. Dùng LayerNorm/GroupNorm, hoặc
  SyncBatchNorm khi chia batch qua nhiều GPU.
- Fine-tune với batch nhỏ mà vẫn cập nhật running stats của model pretrain: nên đóng băng BN (để eval
  mode cho các tầng BN).
- Dropout đặt trước BN làm running var học từ dữ liệu có dropout, lệch với lúc eval.

LayerNorm chuẩn hoá theo feature của từng mẫu, không có running stats, train và eval giống hệt: lý do
Transformer dùng nó (chuỗi dài thay đổi, batch nhỏ, sinh từng token).

## Dropout: vì sao "inverted", và vì sao pretrain LLM thường để dropout bằng 0?

Inverted dropout đặt 0 với xác suất $$p$$ và nhân phần còn lại với $$1/(1-p)$$ khi train, để kỳ vọng không đổi
(đo trên một triệu phần tử với $$p = 0.5$$: mean 0.9996). Nhờ vậy eval chỉ cần bỏ dropout, không phải chỉnh
trọng số. Khi tự viết: mask sinh mới mỗi forward và lưu lại cho backward; sinh mask mới trong backward là
bug im lặng.

Dropout là regularization, đổi lấy học chậm hơn. Pretrain LLM có hàng nghìn tỉ token và thường chỉ đi qua
dữ liệu khoảng một lần, nên overfit không phải vấn đề, dropout chỉ làm chậm. Fine-tune trên tập nhỏ thì
dropout (và LoRA dropout) lại có ích.

## Case: loss ra NaN ở epoch 3. Bạn debug thế nào?

NaN muộn (không phải bước đầu) thường là thứ gì đó **tăng dần** tới khi tràn số. Thứ tự:

1. **Tái hiện và khoanh vùng**: lưu checkpoint mỗi vài trăm bước; chạy lại từ checkpoint gần nhất với
   `np.seterr(all="raise")` (numpy) hoặc `torch.autograd.set_detect_anomaly(True)` để dừng ở phép toán
   đầu tiên ra `nan`/`inf`. Ghi lại batch gây lỗi.
2. **Xem dữ liệu của batch đó**: có NaN, inf, giá trị cực lớn, cột hằng (chia std = 0) không. Một bản
   ghi lỗi chỉ xuất hiện ở epoch 3 vì thứ tự xáo.
3. **Xem số đo đã log**: norm gradient và max abs của logits theo thời gian. Tăng dần rồi nổ là lr quá
   lớn cho giai đoạn đó, hoặc weight phình (thiếu weight decay).
4. **Tìm phép toán không ổn định**: `log(softmax)` thay vì `log_softmax`, `log(p)` không kẹp, softmax không
   trừ max, BatchNorm thiếu $$\epsilon$$, chia cho một std tính trên batch.
5. **Sửa theo nguyên nhân**: hàm ổn định số; gradient clipping theo norm; giảm lr hoặc thêm warmup/decay;
   với mixed precision thì dùng loss scaling hoặc bf16 (module 02).

Câu trả lời yếu là "giảm lr thử xem": có thể che bệnh (ví dụ một bản ghi NaN trong dữ liệu) mà không chữa.

## Case: model không học, loss đứng yên ở khoảng 2.30 (ln 10) trên MNIST. Bạn nghĩ tới những gì?

$$\ln 10 \approx 2.303$$ là cross-entropy của dự đoán **đều** trên 10 lớp: model đang không dùng gì từ input. Các
giả thuyết, từ rẻ tới đắt để kiểm:

- **Output không phụ thuộc input**: ReLU chết hết. Trong thí nghiệm của module, SGD lr 5.0 giết 100% neuron
  ẩn, loss đứng ở 2.324, accuracy 0.0982 (đúng tỉ lệ một lớp, model đoán một lớp cho mọi ảnh). Kiểm: tỉ lệ
  neuron không bật, độ lệch chuẩn của logits giữa các mẫu.
- **Nhãn không khớp input**: `X` và `y` xáo bằng hai hoán vị khác nhau, hoặc nhãn bị lệch một dòng. Kiểm:
  hiện vài ảnh kèm nhãn **sau** khi xáo.
- **Tham số không được cập nhật**: quên gọi step, gradient bị ghi đè bằng 0, tham số là bản copy chứ không
  phải mảng đang được dùng. Kiểm: so trọng số trước và sau một bước.
- **lr quá nhỏ hoặc init quá nhỏ**: loss giảm rất chậm chứ không hẳn đứng yên. Kiểm: quét lr theo log, std
  activation từng tầng.
- **Input chưa chuẩn hoá** (pixel 0 tới 255): pre-activation khổng lồ, ReLU chết hoặc tanh bão hoà ngay
  bước đầu.

Bước quyết định: **overfit một batch 32 mẫu**. Không về được loss gần 0 thì là bug pipeline, không phải
vấn đề dữ liệu hay kiến trúc. Ứng viên tốt cũng nói loss ở bước 0 **phải** gần 2.30; nếu bước 0 đã là
2.30 và không bao giờ giảm thì nghi gradient/update, còn nếu giảm rồi quay về 2.30 thì nghi lr làm chết
neuron giữa chừng.

## Case: model đạt 98% trên validation trong notebook nhưng khi đóng gói thành service thì chỉ còn khoảng 60%. Bạn tìm nguyên nhân thế nào?

Đây là lỗi hệ thống chứ không phải lỗi model. Khoanh vùng bằng cách đưa **cùng một input** qua hai đường
(notebook và service) và so từng bước:

1. **Tiền xử lý**: notebook chia 255 và trừ mean/std của tập train, service quên chia hoặc tính mean/std
   trên request. Ảnh từ người dùng có thể nền trắng chữ đen (MNIST ngược lại), khác kích thước, khác
   dtype (uint8 cộng tràn).
2. **Chế độ model**: service không gọi `eval()`; BatchNorm dùng thống kê của batch 1 ảnh, dropout vẫn bật.
   Triệu chứng: gửi cùng một ảnh hai lần ra hai kết quả, hoặc kết quả đổi theo batch.
3. **Trọng số**: nạp nhầm checkpoint (bản cuối thay vì bản tốt nhất), thiếu running stats của BN khi chỉ
   lưu tham số học.
4. **Thứ tự lớp**: mapping chỉ số lớp sang nhãn khác nhau giữa train và service.
5. Rồi mới tới **distribution shift** thật: dữ liệu production khác dữ liệu train. Lúc đó cần thu dữ liệu
   thật, đánh giá trên đó, và theo dõi phân phối input (module 20).

Thiết kế để không lặp lại: một hàm tiền xử lý dùng chung cho train và serve, lưu đủ trạng thái (tham số,
running stats, mean/std, mapping lớp) trong một artifact, và một test so output của service với notebook
trên vài mẫu cố định.

## Trong thực tế, khi nào một AI Engineer phải tự viết backward thay vì để autograd lo?

Hầu hết thời gian không cần: autograd đúng và đủ nhanh. Những trường hợp phải tự viết hoặc ít nhất phải
hiểu backward:

- **Phép toán tự định nghĩa** (`torch.autograd.Function`): một hàm có công thức gradient gọn hơn hoặc ổn
  định hơn autograd tự suy ra (ví dụ log-sum-exp, các loss có cực trị), hoặc một phép không khả vi cần
  gradient thay thế (straight-through estimator cho quantization, module 10).
- **Kernel tối ưu**: FlashAttention, fused softmax + cross-entropy cho vocabulary lớn viết bằng Triton/CUDA
  có forward và backward riêng; không ai sinh tự động được.
- **Tiết kiệm bộ nhớ**: gradient checkpointing, tính lại activation trong backward thay vì lưu.
- **Debug**: khi loss NaN hoặc model không học, đọc được norm gradient từng tầng và biết nó *nên* bằng bao
  nhiêu là kỹ năng phân biệt người dùng thư viện với người sửa được thư viện.

Cách làm an toàn: viết backward, gradient check bằng float64 trên input nhỏ (`torch.autograd.gradcheck`),
so với cài đặt autograd thuần, rồi mới đo tốc độ.
