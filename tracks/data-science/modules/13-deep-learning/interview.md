# Câu hỏi phỏng vấn: Deep Learning với PyTorch

## Khi nào bạn dùng deep learning, khi nào dùng gradient boosting?

Dữ liệu **bảng** (đơn hàng, khách hàng, giao dịch) với vài chục tới vài trăm feature: gradient
boosting (LightGBM, XGBoost) thường thắng hoặc ngang, train nhanh, ít tune, giải thích được bằng SHAP.
Dữ liệu **không có cấu trúc** (ảnh, văn bản, âm thanh, chuỗi sự kiện dài): deep learning, gần như
luôn bắt đầu từ model pretrain.

Ứng viên senior nói thêm về trường hợp lai: feature bảng cộng văn bản review thì thường lấy
embedding / điểm từ model văn bản làm feature cho model boosting. Và luôn so với baseline: trên
review Olist, TF-IDF + logistic regression (test AUC 0.950) thắng cả túi embedding (0.942) lẫn
Transformer 2 tầng train từ đầu (0.944–0.947).

## Giải thích backpropagation cho người biết đạo hàm nhưng chưa học deep learning.

Mạng nơ-ron là một hàm hợp nhiều tầng; loss phụ thuộc vào mỗi trọng số qua một chuỗi phép toán.
Backprop là chain rule áp **từ cuối về đầu**: tính đạo hàm của loss theo output của tầng cuối, rồi
nhân với đạo hàm cục bộ của từng tầng để đi ngược dần, tái sử dụng kết quả trung gian. Nhờ vậy, chi
phí tính gradient theo **mọi** tham số chỉ cỡ vài lần chi phí một lần forward, dù có hàng triệu tham
số. PyTorch ghi lại graph khi forward (mỗi tensor có `grad_fn`) và `loss.backward()` duyệt ngược
graph theo thứ tự topo, cộng dồn gradient vào `.grad`.

Chi tiết thể hiện kinh nghiệm: gradient **cộng dồn** nên phải `zero_grad()`; graph bị giải phóng
sau `backward()`; activation của forward được giữ lại đến lúc backward nên bộ nhớ train lớn hơn
nhiều so với suy luận.

## Viết vòng train chuẩn. Những bug "im lặng" nào hay gặp?

`for batch: optimizer.zero_grad(); loss = loss_fn(model(x), y); loss.backward(); optimizer.step()`,
`model.train()` trước khi train, `model.eval()` + `torch.no_grad()` khi đánh giá, early stopping theo
val loss và nạp lại trọng số tốt nhất.

Bug không báo lỗi nhưng làm model tệ:

- Quên `zero_grad()`: gradient cộng dồn qua các batch.
- Quên `model.eval()`: dropout vẫn bật, BatchNorm cập nhật thống kê bằng dữ liệu đánh giá.
- `evaluate` gọi `eval()` nhưng không ai gọi lại `train()`: từ epoch 2 dropout tắt khi train.
- Thêm `softmax` trước `CrossEntropyLoss` (vốn nhận logits): vẫn học được nhưng chậm, gradient yếu.
- Lưu `model.state_dict()` không `deepcopy`: "bản tốt nhất" bị cập nhật theo.
- Cộng `total += loss` (tensor): giữ graph của mọi batch, rò bộ nhớ.

Cách phát hiện: overfit một batch nhỏ trước (loss phải về gần 0), và viết test cho vòng train như
bài Basic 02.

## Dropout hoạt động thế nào? Vì sao khi train phải nhân 1/(1−p)?

Khi train, mỗi nơ-ron bị đặt về 0 với xác suất p, ngẫu nhiên mỗi batch. Model không thể dựa vào
một nơ-ron cụ thể, nên học biểu diễn dư thừa và bền hơn, gần giống trung bình một tập hợp rất nhiều
mạng con. Nhân phần còn lại với $$1/(1-p)$$ (inverted dropout) để kỳ vọng output của tầng không đổi;
nhờ vậy khi `eval()` chỉ việc tắt dropout, không phải chỉnh lại trọng số.

Trong thí nghiệm của module (MLP 512-512 trên 1 000 ảnh FashionMNIST), dropout 0.5 không đổi accuracy
nhiều (0.817 → 0.819 ở epoch 100) nhưng giảm val loss epoch 100 từ 1.193 xuống 0.835: model bớt tự tin
sai. Nói được điều đó cho thấy bạn nhìn loss chứ không chỉ accuracy.

## Weight decay khác L2 regularization thế nào? Vì sao có AdamW?

Với SGD thường, thêm $$\frac{\lambda}{2}\lVert w\rVert^2$$ vào loss và weight decay (nhân w với $$1 - \eta\lambda$$ mỗi bước) là
một. Với Adam thì không: phạt L2 đi vào gradient, rồi bị chia cho căn của moment bậc hai, nên tham số
có gradient lớn bị phạt ít hơn. **AdamW** tách phần decay ra khỏi gradient, áp trực tiếp lên trọng
số, nên regularization đúng như ý định và thường tổng quát hoá tốt hơn. Mặc định hiện đại cho
Transformer là AdamW. Thường không decay bias và tham số của LayerNorm.

## Vì sao CNN hợp với ảnh hơn MLP?

Hai lý do: **weight sharing** (cùng kernel dùng ở mọi vị trí, số tham số không phụ thuộc kích thước
ảnh: tầng conv đầu trong module có 320 tham số, tầng Linear làm cùng phép biến đổi kích thước cần
gần 20 triệu) và **translation equivariance** (nhận ra cùng một mẫu ở mọi vị trí). Cộng thêm pooling
và nhiều tầng, CNN học đặc trưng từ cạnh tới hoạ tiết tới bộ phận.

Số thật trên FashionMNIST (5 epoch, CPU): MLP 87.7%, CNN 90.5% test accuracy; CNN chậm hơn khoảng 13
lần trên CPU. Bẫy đáng nói: phần lớn tham số của CNN đơn giản nằm ở tầng Linear sau `Flatten` (401 536
trên 421 642), nên kiến trúc hiện đại dùng global average pooling.

## Vanishing gradient là gì? LSTM giải quyết nó ra sao?

Trong RNN, gradient về bước đầu phải đi qua tích của nhiều Jacobian; với `tanh` và trọng số thông
thường, tích này co nhanh về 0, nên model không học được phụ thuộc xa. LSTM thêm cell state cập nhật
kiểu **cộng** ($$c_t = f_t \odot c_{t-1} + i_t \odot \tilde c_t$$); khi forget gate gần 1, gradient đi qua
gần như nguyên vẹn. Exploding gradient (ngược lại) thì chữa bằng gradient clipping.

Ví dụ từ module: nhớ token đầu tiên qua 10–20 bước, LSTM và GRU học được ở 10/10 seed, RNN thường chỉ
2/10. Ở mạng sâu (không phải chuỗi), residual connection và normalization đóng vai trò tương tự.

## Giải thích attention. Vì sao chia cho căn bậc hai của d_k?

Mỗi vị trí tạo query, key, value. Trọng số giữa vị trí i và j là softmax của $$q_i \cdot k_j$$ theo j;
output ở i là trung bình có trọng số của các value. Mỗi token "hỏi" mọi token khác, nên phụ thuộc xa
chỉ cách nhau một bước, và tính được song song.

Chia $$\sqrt{d_k}$$: nếu các thành phần của q, k độc lập phương sai 1 thì tích vô hướng có độ lệch chuẩn
$$\sqrt{d_k}$$ (trong module đo được 3.97, 7.97, 16.17 với d = 16, 64, 256). Điểm số lớn làm softmax gần
one-hot và gradient gần 0. Chia đưa độ lệch chuẩn về khoảng 1.

## Transformer có positional encoding để làm gì? Không có thì sao?

Self-attention là phép toán trên **tập hợp**: hoán vị input thì output hoán vị theo y hệt (test của
bài Advanced 02 kiểm đúng tính chất này). Không có thông tin vị trí, "não gostei, recomendo" và
"gostei, não recomendo" giống nhau. Positional encoding (sinusoid cố định, hoặc vector vị trí học
được, hoặc dạng tương đối như RoPE) cộng / trộn vị trí vào biểu diễn. Sinusoid có lợi thế là không
có tham số và tổng quát hoá tới độ dài chưa thấy ở mức nào đó; vị trí học được thì giới hạn ở
`max_len` lúc train.

## So sánh RNN/LSTM và Transformer. Chi phí của attention là gì?

Transformer: đường đi giữa hai token bất kỳ là 1 bước, train song song theo độ dài, mạnh nhất khi
pretrain trên dữ liệu lớn. Cái giá là attention tốn $$O(L^2)$$ bộ nhớ và tính toán theo độ dài chuỗi;
chuỗi rất dài cần FlashAttention, attention thưa hoặc chia đoạn. LSTM: $$O(L)$$, chạy streaming từng
bước với trạng thái cố định, ít dữ liệu vẫn học được; nhưng tuần tự nên train chậm và khó nhớ xa.
Chọn theo dữ liệu, độ dài, ràng buộc độ trễ và việc có model pretrain hay không.

## Embedding là gì? Embedding học từ một model phân loại có "nghĩa" không?

Embedding là bảng tra id → vector dày đặc học được, thay one-hot thưa. Dùng cho từ, sản phẩm, khách,
seller, mọi biến phân loại nhiều giá trị.

Embedding chỉ mang cấu trúc mà mục tiêu train đòi hỏi. Model phân loại review xấu trên Olist chỉ cần
một hướng tốt/xấu; hàng xóm gần nhất của "pessimo" trong embedding đó là các từ vô nghĩa. Skip-gram
(word2vec) train trên cùng văn bản cho "otimo" gần "maravilhoso, excelente, perfeito" và "entregue" gần
các lỗi chính tả của nó. Muốn embedding dùng chung cho nhiều tác vụ thì cần mục tiêu tự giám sát hoặc
model pretrain; và nếu dùng làm feature thì chỉ train trên dữ liệu thuộc giai đoạn train.

## Transfer learning: linear probe hay fine-tune? Khi nào transfer không giúp?

Ít dữ liệu nhãn và miền gần nguồn: linear probe (đóng băng backbone, train head), rẻ và khó overfit.
Dữ liệu vừa: fine-tune toàn bộ với learning rate backbone nhỏ hơn head (khoảng 10 lần) hoặc mở dần
từng tầng. Nhiều dữ liệu và miền rất xa: train từ đầu có thể ngang bằng.

Transfer không giúp khi nguồn **hẹp hoặc xa** đích. Thí nghiệm trong module: pretrain trên 5 lớp áo
quần FashionMNIST rồi chuyển sang giày/túi; linear probe thua train từ đầu 7.4–8.4 điểm ở mọi mức dữ
liệu, fine-tune chỉ ngang bằng. Câu trả lời senior: luôn có đối chứng train từ đầu và nhiều seed,
chú ý dùng đúng transform của weights pretrain, và để BatchNorm ở `eval()` khi đóng băng.

## Model 85 triệu tham số có train được trên GPU 4 GB không? Bạn ước lượng thế nào?

Trạng thái train fp32 + Adam: khoảng 16 byte mỗi tham số (trọng số 4, gradient 4, hai moment 8), tức
85.1 triệu × 16 byte ≈ 1.27 GiB, **chưa tính activation**, thứ thường lớn hơn và tăng theo batch size,
độ dài chuỗi. Vậy là được nhưng sát: dùng mixed precision (bf16 trên Ampere), batch nhỏ + gradient
accumulation, giới hạn độ dài chuỗi, gradient checkpointing nếu cần; đo bằng
`torch.cuda.max_memory_allocated()` thay vì đoán. Model vài tỉ tham số thì không: cần GPU lớn hơn, hoặc
fine-tune một phần nhỏ tham số (LoRA) kèm lượng tử hoá.

## Training loss không giảm. Bạn gỡ lỗi theo thứ tự nào?

1. Kiểm dữ liệu: nhãn có khớp input không (xem vài mẫu), có chuẩn hoá chưa, có NaN không.
2. Overfit **một batch** (8–32 mẫu): loss không về gần 0 thì là bug pipeline, không phải thiếu dữ liệu.
3. Kiểm vòng train: `zero_grad`, `train()`, loss nhận logits hay xác suất, đúng chiều `argmax`.
4. Learning rate: quá lớn thì loss nổ hoặc đứng yên ở mức đoán mò (bài Intermediate 02: LSTM kẹt ở 50%
   với lr 1e-2, học được với 3e-3); thử quét lr theo log.
5. Gradient: log chuẩn gradient; bằng 0 (ReLU chết, vanishing) hay khổng lồ (cần clipping).
6. Rồi mới tới kiến trúc, regularization.

## Case: Olist muốn tự động gắn cờ review cần CSKH xử lý. Bạn xây model thế nào?

Làm rõ bài toán trước: gắn cờ review **đã viết** (phân loại nội dung), không phải dự báo trước khi
khách review. Định nghĩa nhãn cùng đội CSKH (review xấu, hoặc tốt hơn: "cần hành động" như không nhận
được hàng, hàng lỗi), vì `review_score <= 2` chỉ là proxy.

Dữ liệu: khoảng 41% đơn có lời bình; tỉ lệ xấu trong nhóm có lời bình là 23.8% (so với 12.8% mọi
review). Chia theo thời gian (validation quý 1/2018 có tỉ lệ xấu 32%, khác hẳn train). Baseline:
TF-IDF unigram + bigram + logistic regression (test AUC 0.955, PR-AUC 0.817), train vài giây, giải
thích bằng trọng số từ. Chỉ nâng lên model pretrain tiếng Bồ Đào Nha nếu lợi ích đo được trên tập
khó (review có phủ định "nao", nơi mọi model đều kém hơn hẳn) đáng chi phí GPU và độ trễ.

Vận hành: chọn ngưỡng theo năng lực CSKH (top k review mỗi ngày) và chi phí bỏ sót; theo dõi drift
từ vựng (sản phẩm mới, mùa vụ); có vòng phản hồi để CSKH sửa nhãn.

## Case: Team muốn phân loại ảnh sản phẩm của seller vào danh mục. Có 2 000 ảnh có nhãn. Kế hoạch của bạn?

2 000 ảnh là quá ít để train CNN từ đầu cho ảnh thật. Kế hoạch:

1. Baseline nhanh: embedding từ model pretrain ImageNet (ResNet / EfficientNet, đúng transform chuẩn
   hoá của weights) + logistic regression (linear probe). Rẻ, chạy cả trên CPU.
2. Fine-tune toàn bộ với lr backbone nhỏ, augmentation (lật, cắt, đổi sáng; không dùng phép làm đổi
   nhãn), early stopping theo validation, trên GPU (RTX 3050 4GB đủ cho ResNet18/50 với batch vừa và
   mixed precision).
3. Đánh giá theo từng danh mục (confusion matrix): như FashionMNIST, lỗi thường dồn vào vài cặp danh
   mục giống nhau; cân nhắc gộp danh mục hoặc cho người duyệt các trường hợp không chắc.
4. Kết hợp với tín hiệu rẻ hơn (tiêu đề, mô tả sản phẩm) trước khi đầu tư thêm vào ảnh.

Rủi ro: ảnh seller khác phân phối ảnh train (nền, góc chụp), nhãn danh mục nhiễu, mất cân bằng lớp.

## Case: PM hỏi "dùng Transformer cho mọi thứ được không, nghe nói nó tốt nhất?". Bạn trả lời thế nào?

Đưa số, không đưa niềm tin. Trên review Olist trong module: Transformer 2 tầng train từ đầu đạt test
AUC 0.944–0.947 sau khoảng 1 phút train mỗi lần, TF-IDF + logistic regression đạt 0.950 (bigram 0.955)
trong vài giây; cả trên tập review có phủ định, nơi "Transformer hiểu thứ tự từ" lẽ ra có lợi,
baseline vẫn hơn. Transformer mạnh khi được **pretrain** trên lượng dữ liệu khổng lồ, và khi tác vụ
cần hiểu ngữ cảnh dài. Với dữ liệu bảng, gradient boosting thường thắng.

Đề xuất quy trình: mỗi bài toán bắt đầu bằng baseline đơn giản, đo trên cùng tập test chia theo thời
gian, nâng cấp model chỉ khi lợi ích lớn hơn chi phí (GPU, độ trễ, khả năng giải thích, công vận hành).
