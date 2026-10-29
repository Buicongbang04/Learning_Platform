# Câu hỏi phỏng vấn: Toán cho Machine Learning

## Giải thích linear regression dưới góc nhìn hình học. Vì sao residual vuông góc với mọi feature?

Mọi dự đoán $$\hat y = Xw$$ là tổ hợp tuyến tính các cột của $$X$$, nên nằm trong **không gian cột** của
$$X$$. Least squares tìm điểm trong không gian đó gần $$y$$ nhất theo khoảng cách Euclid, và điểm gần nhất
là **hình chiếu vuông góc**. "Vuông góc" nghĩa là residual $$y - Xw$$ vuông góc với mọi cột:

$$
X^\top(y - Xw) = 0 \;\Longleftrightarrow\; X^\top X\,w = X^\top y
$$

Đó chính là normal equation. Hệ quả hay được hỏi tiếp:

- Có cột intercept thì residual có tổng bằng 0 (vuông góc với cột toàn 1).
- Residual không tương quan với bất kỳ feature nào **trên tập train**; nếu thấy residual tương quan
  với một feature đã có trong model thì có bug. Tương quan với feature *chưa có* (quãng đường giao hàng)
  là gợi ý thêm feature.
- Ma trận chiếu $$P = X(X^\top X)^{-1}X^\top$$ có trace bằng số tham số, lý do variance của residual chia
  cho $$n - d$$; đường chéo của nó là leverage.

## Vì sao không dùng `inv(X.T @ X) @ X.T @ y`? Khi nào normal equation vẫn là lựa chọn tốt?

Ba lý do: (1) tính nghịch đảo tốn hơn giải hệ (`solve` làm một phân rã LU rồi thế ngược); (2) kém chính
xác hơn; (3) quan trọng nhất, tạo $$X^\top X$$ bình phương condition number: $$\kappa(X^\top X) = \kappa(X)^2$$, nên
mất gấp đôi số chữ số đúng. Trên ma trận Vandermonde bậc 12 (κ ≈ 7 · 10⁸), normal equation cho nghiệm sai
hoàn toàn còn `lstsq` vẫn đúng tới khoảng 9 chữ số.

Normal equation vẫn tốt khi feature đã chuẩn hoá, không trùng lặp, d nhỏ tới vừa: nó nhanh nhất (trên
51 216 dòng, d = 100, khoảng 63 ms so với 695 ms của QR), và $$X^\top X$$, $$X^\top y$$ cộng dồn được theo chunk
hay trong SQL/Spark nên chạy được trên dữ liệu phân tán. Mặc định an toàn khi không chắc là
`np.linalg.lstsq` (SVD) hoặc QR.

## Eigenvector là gì? SVD khác eigen decomposition thế nào và liên hệ với PCA ra sao?

Eigenvector của ma trận vuông $$A$$ là hướng $$v$$ mà $$A$$ chỉ kéo giãn: $$Av = \lambda v$$. Ma trận đối xứng
(covariance, Hessian) có trị riêng thực và eigenvector trực chuẩn: $$A = V\Lambda V^\top$$.

SVD áp dụng cho **mọi** ma trận n×d: $$X = U\Sigma V^\top$$. Liên hệ: $$X^\top X = V\Sigma^2V^\top$$, nên $$V$$ là
eigenvector của $$X^\top X$$ và $$\sigma_i^2$$ là trị riêng.

PCA: trừ trung bình được $$X_c$$, covariance $$C = X_c^\top X_c/(n-1)$$. Thành phần chính là eigenvector của
$$C$$, cũng là cột của $$V$$ trong SVD của $$X_c$$; variance giải thích là $$\sigma_i^2/(n-1)$$. Thư viện làm SVD
trên $$X_c$$ thay vì eigen trên $$C$$ để không bình phương condition number. Ứng viên tốt nhắc thêm: SVD
cắt k thành phần cho xấp xỉ hạng k tốt nhất (Eckart–Young), nền của matrix factorization trong
recommender và của LSA trong NLP.

## Trình bày PCA từ đầu tới cuối. Chọn số thành phần thế nào? Khi nào PCA là ý tồi?

1. Chọn feature số; xử lý lệch phải (log) nếu cần.
2. Chuẩn hoá khi feature khác đơn vị (nếu không, PCA chạy theo cột có variance lớn nhất). **Fit
   scaler và PCA trên train**.
3. SVD rút gọn; lấy thành phần, variance, score.
4. Chọn k: theo tỉ lệ variance cộng dồn (80–95%), theo "khuỷu" của scree plot, hoặc tốt nhất là theo
   metric của bài toán cuối trên validation.

Ví dụ thật: 7 cột số của 32 340 sản phẩm Olist, sau log và chuẩn hoá: PC1 35.9% (kích thước), PC2 17.6%
(độ chăm chút listing), cần 5 / 7 thành phần cho 90%. Nén kém vì ba cột văn bản/ảnh gần như độc lập.

PCA là ý tồi khi: cần giải thích bằng feature gốc; quan hệ phi tuyến; feature quan trọng với target
có variance nhỏ (PCA không nhìn target, có thể vứt đúng tín hiệu cần); dùng trước model cây trên dữ liệu
bảng (thường làm mất khả năng tách theo từng feature mà không lợi gì).

## Condition number là gì? Bạn chẩn đoán multicollinearity thế nào trong thực tế?

$$\kappa(X) = \sigma_{\max}/\sigma_{\min}$$: hệ số khuếch đại sai số tương đối từ dữ liệu sang nghiệm. Quy tắc nhẩm:
mất khoảng $$\log_{10}\kappa$$ chữ số đúng. Với tối ưu, κ của Hessian quyết định gradient descent chậm cỡ nào.

Điểm senior: κ lớn có hai nguồn. **Thang đo** (`[1, gram, cm³]` có κ ≈ 36 431, `[1, kg, lít]` chỉ 36.4,
cùng thông tin) thì chữa bằng chuẩn hoá, và solver tốt gần như không bị ảnh hưởng. **Cột gần phụ thuộc
tuyến tính** thì κ vẫn lớn sau khi chia mỗi cột cho chuẩn của nó; đây mới là multicollinearity thật.

Công cụ: condition number sau khi cân bằng cột; singular value nhỏ nhất và vector $$v$$ tương ứng (chỉ
ra **tổ hợp** cột nào gần bằng 0); VIF $$= 1/(1 - R_j^2)$$ khi hồi quy feature j theo các feature còn lại
(VIF > 10 là cảnh báo). Hệ quả: dự đoán vẫn tốt, nhưng hệ số không ổn định, đổi dấu, standard error phình
to. Chữa: bỏ cột trùng, gộp feature, ridge, PCA.

## Đạo hàm logistic loss theo trọng số. Vì sao sigmoid đi với cross-entropy?

Với $$z = w^\top x$$, $$p = \sigma(z)$$, $$\ell = -[y\log p + (1-y)\log(1-p)]$$. Chain rule:

$$
\frac{\partial \ell}{\partial w} = \frac{\partial \ell}{\partial p}\cdot\frac{\partial p}{\partial z}\cdot\frac{\partial z}{\partial w}
= \frac{p - y}{p(1-p)}\cdot p(1-p)\cdot x = (p - y)\,x
$$

$$p(1-p)$$ triệt tiêu, nên gradient tỉ lệ với sai số $$p - y$$ và không "tắt" khi model sai nặng. Nếu dùng
MSE trên sigmoid, gradient có thừa số $$p(1-p) \to 0$$ khi $$p$$ gần 0 hoặc 1: model sai hoàn toàn mà học rất
chậm. Đây cũng là lý do softmax đi với categorical cross-entropy.

Về cài đặt: viết loss theo logit, $$\log(1 + e^z) - yz$$, dùng `logaddexp` / `BCEWithLogitsLoss`. Tính
`log(sigmoid(z))` trực tiếp ra `-inf` khi z rất âm.

## Bạn tự viết một loss hoặc layer mới. Làm sao biết gradient đúng?

**Gradient check**: so gradient giải tích với sai phân trung tâm
$$\frac{f(w + \varepsilon e_i) - f(w - \varepsilon e_i)}{2\varepsilon}$$ (sai số $$O(\varepsilon^2)$$, tốt hơn sai phân tiến $$O(\varepsilon)$$),
$$\varepsilon$$ khoảng 1e-5 tới 1e-6. Đo sai số tương đối $$\lVert g_a - g_n\rVert/(\lVert g_a\rVert + \lVert g_n\rVert)$$:
dưới 1e-7 tốt, trên 1e-4 gần như chắc có bug.

Bẫy: kiểm ở w = 0 (nhiều số hạng bằng 0 che bug); float32 (sai số làm tròn vượt ngưỡng); hàm có điểm
gãy (ReLU, `abs`, `max`) gần điểm kiểm; dropout hay batch norm làm loss ngẫu nhiên giữa hai lần gọi. Với
model lớn, kiểm trên vài toạ độ ngẫu nhiên và một batch nhỏ. Thực tế ngày nay autograd làm hộ, nhưng
gradient check vẫn cần khi viết custom autograd function, kernel CUDA, hoặc loss có công thức tự rút gọn.

## Convex và non-convex khác nhau thế nào? Cho ví dụ và hệ quả thực tế.

Convex: đoạn thẳng nối hai điểm trên đồ thị nằm trên đồ thị; tương đương Hessian nửa xác định dương. Mọi
cực tiểu địa phương là toàn cục. Ví dụ: linear/ridge/lasso, logistic, SVM, GLM. Non-convex: mạng nơ-ron,
matrix factorization, k-means, Gaussian mixture.

Hệ quả:

- Convex: kết quả không phụ thuộc khởi tạo; hai thư viện phải ra cùng hệ số (khác là có vấn đề hội tụ
  hoặc regularization); dùng được solver bậc hai và tiêu chuẩn dừng chặt.
- Non-convex: kết quả phụ thuộc seed. Một mạng 8 nút ẩn trên dữ liệu review Olist, 10 seed, cho loss train
  0.3202–0.3281 và trọng số khác hẳn nhau. Phải cố định seed, báo cáo độ dao động qua nhiều seed, không
  diễn giải từng trọng số, và chọn model bằng validation chứ không bằng loss train.
- Trong nhiều chiều, điểm yên ngựa và vùng phẳng là trở ngại chính hơn cực tiểu địa phương tồi.

## Learning rate quá lớn hoặc quá nhỏ thì sao? Có cơ sở nào để chọn không?

Với loss bậc hai có Hessian $$H$$, sai số theo hướng trị riêng $$\lambda$$ nhân với $$1 - \eta\lambda$$ mỗi bước. Nên:
$$\eta > 2/\lambda_{\max}$$ thì phân kỳ (loss nổ theo hàm mũ); $$\eta$$ quá nhỏ thì hướng cong ít tiến cực chậm. Với
$$\eta = 1/\lambda_{\max}$$, số bước tỉ lệ $$\kappa = \lambda_{\max}/\lambda_{\min}$$.

Thực tế: thử theo thang log (1e-5 … 1); "LR range test" tăng lr dần trong một epoch và chọn trước điểm loss
bắt đầu nổ; dùng warmup cho mạng lớn; giảm lr theo schedule. Dấu hiệu chẩn đoán: loss nổ / NaN → lr lớn;
loss giảm đều nhưng rất chậm → lr nhỏ hoặc bài toán xấu điều kiện; loss dao động quanh một mức → lr cố
định với SGD, cần decay.

## Vì sao chuẩn hoá feature làm gradient descent nhanh hơn? Model cây có cần chuẩn hoá không?

Chuẩn hoá giảm condition number của Hessian. Ví dụ thật: hồi quy phí ship Olist theo kg và lít, κ(H) ≈ 1 329,
gradient descent với lr = 1/L cần 9 231 bước để loss cách tối ưu 1e-6; chuẩn hoá đưa κ về 8.6 và chỉ cần 30
bước, cùng nghiệm. Hình ảnh: đường đồng mức từ elip dẹt thành gần tròn, gradient chỉ thẳng vào tâm.

Chuẩn hoá cũng cần cho regularization (L1/L2 phạt mọi hệ số như nhau, nên thang đo quyết định feature nào
bị phạt nặng), cho kNN, k-means, PCA, SVM. Model cây (random forest, gradient boosting) **không** cần: tách
theo ngưỡng không đổi khi biến đổi đơn điệu feature. Lỗi hay gặp: fit scaler trên toàn bộ dữ liệu trước khi
chia train/test.

## So sánh batch gradient descent, SGD và minibatch SGD. Batch size ảnh hưởng gì?

| | Batch GD | SGD (B = 1) | Minibatch (B = 32–512) |
| --- | --- | --- | --- |
| Chi phí mỗi bước | $$O(nd)$$ | $$O(d)$$ | $$O(Bd)$$ |
| Gradient | Chính xác | Rất nhiễu | Nhiễu vừa |
| Tận dụng phần cứng | Tốt nhưng ít bước | Kém | Tốt nhất |
| Hội tụ với lr cố định | Có (convex, lr < 2/L) | Dao động quanh nghiệm | Dao động, nhỏ hơn |

Với lr cố định, nhiễu của SGD không tắt: trên một hồi quy mô phỏng (20 epoch, batch 16, 10 seed), lr cố
định dừng cách nghiệm 0.39–1.69, lr giảm theo $$\eta_0/(1 + kt)$$ còn 0.008–0.028. Batch lớn hơn cho gradient ít
nhiễu hơn nên thường dùng được lr lớn hơn (quy tắc tăng lr tuyến tính theo batch, có giới hạn); batch nhỏ
có nhiễu giúp thoát điểm yên ngựa và đôi khi tổng quát hoá tốt hơn.

## Momentum và Adam hoạt động thế nào? Khi nào chọn SGD + momentum thay vì Adam?

Momentum: $$v \leftarrow \beta v - \eta\nabla L$$, $$w \leftarrow w + v$$. Gradient cùng dấu cộng dồn (tăng tốc theo hướng
thoải), gradient đổi dấu triệt tiêu (giảm dao động theo hướng dốc). Với tham số tối ưu trên hàm bậc hai, số
bước tỉ lệ $$\sqrt\kappa$$ thay vì $$\kappa$$: với κ = 100, khoảng 90 bước so với khoảng 1 300.

Adam: momentum trên gradient (moment bậc một) cộng chia từng toạ độ cho căn của trung bình gradient bình
phương (moment bậc hai), có hiệu chỉnh bias lúc đầu. Phần chia là tiền điều kiện chéo: ít nhạy với thang
đo, ít phải chỉnh lr. Mặc định cho transformer và hầu hết mạng mới.

SGD + momentum vẫn được chọn cho một số bài toán thị giác (CNN) vì đôi khi tổng quát hoá tốt hơn và ít
tham số trạng thái hơn (Adam lưu thêm hai vector cỡ bằng số tham số, đáng kể với model hàng tỉ tham số).
Với Adam và weight decay, dùng AdamW (tách weight decay khỏi bước thích nghi).

## Newton khác gradient descent thế nào? Vì sao deep learning không dùng Newton?

Newton dùng cả độ cong: $$w \leftarrow w - H^{-1}\nabla L$$ (giải hệ, không nghịch đảo). Gần nghiệm hội tụ **bậc
hai** (số chữ số đúng gấp đôi mỗi bước) và **không phụ thuộc thang đo** (affine invariant). Trên logistic
regression review Olist, Newton hội tụ trong 5 bước; gradient descent cần 63 bước với feature chuẩn hoá và
sau 20 000 bước vẫn chưa tới khi để đơn vị gốc.

Nhưng mỗi bước tốn $$O(nd^2)$$ để tạo Hessian và $$O(d^3)$$ để giải: với d = 10⁸ tham số thì không thể. Mạng
nơ-ron còn non-convex, Hessian có trị riêng âm nên bước Newton có thể đi lên. Giải pháp trung gian:
L-BFGS (xấp xỉ $$H^{-1}$$ từ vài chục gradient gần nhất, mặc định của `LogisticRegression` trong sklearn),
quasi-Newton, Hessian-free / natural gradient trong nghiên cứu.

## Ridge làm gì về mặt toán? Liên hệ với condition number và với Bayes.

$$w = (X^\top X + \lambda I)^{-1}X^\top y$$: cộng $$\lambda$$ vào mọi trị riêng của $$X^\top X$$, nên condition number thành
$$(\sigma_{\max}^2 + \lambda)/(\sigma_{\min}^2 + \lambda)$$, hữu hạn kể cả khi thiếu hạng. Theo hướng singular value $$\sigma_i$$,
hệ số bị co theo $$\sigma_i^2/(\sigma_i^2 + \lambda)$$: co mạnh theo hướng dữ liệu ít thông tin. Đổi bias lấy variance.

Bayes: ridge là MAP với prior Gaussian $$w \sim \mathcal N(0, \tau^2 I)$$, $$\lambda = \sigma^2/\tau^2$$; lasso là prior
Laplace. Hình học: ràng buộc L2 là hình cầu (hệ số nhỏ đều), L1 là hình thoi có góc trên các trục nên nghiệm
hay rơi vào góc (hệ số bằng 0, chọn feature). Thực hành: chuẩn hoá trước, không phạt intercept, chọn λ bằng
validation (theo thời gian nếu dữ liệu có thời gian).

## Case study: model phí ship của Olist cho hệ số "thêm một lít thì phí ship giảm 1.19 BRL". PM hỏi có nên giảm giá ship cho hàng cồng kềnh không. Bạn làm gì?

Đầu tiên **không** trả lời câu hỏi kinh doanh dựa trên hệ số đó. Hệ số âm cho thể tích trái trực giác vận
tải, nên nghi vấn kỹ thuật trước:

1. Xem danh sách feature: có cột nào trùng thông tin với thể tích không? Trong ví dụ này có: "peso cubado"
   (dài × rộng × cao / 6000) là thể tích chia 6. Hai cột tỉ lệ nhau, $$X^\top X$$ suy biến, κ ≈ 2.9 · 10¹⁶.
2. Kiểm chứng: condition number sau khi cân bằng cột, singular value nhỏ nhất và vector tương ứng (chỉ
   đúng vào cặp cột này), VIF.
3. Hiểu hậu quả: mọi solver cho cùng dự đoán (MSE train 111.864), nhưng hệ số tuỳ solver: normal equation
   −1.19 và 8.23, QR không pivot cỡ 10¹³, SVD min-norm 0.174 và 0.029. Tổng hiệu ứng thể tích vẫn khoảng
   +0.179 BRL mỗi lít.
4. Sửa: bỏ một trong hai cột (hoặc dùng ridge), fit lại, kiểm hệ số ổn định qua bootstrap và qua các
   giai đoạn thời gian.

Trả lời PM: "Hệ số âm là lỗi kỹ thuật do hai cột trùng nhau, không phải sự thật về chi phí. Sau khi sửa,
mỗi lít thêm khoảng 0.18 BRL. Model này cũng chưa có quãng đường, yếu tố lớn nhất của phí ship, và là
tương quan chứ chưa phải chi phí thật của hãng vận chuyển. Muốn quyết định giá thì cần dữ liệu cước của
đối tác vận chuyển." Thêm kiểm tra condition number vào pipeline để lỗi này không lặp lại.

## Case study: team muốn dùng PCA nén 300 feature xuống 20 trước khi đưa vào LightGBM dự đoán churn "cho nhanh và đỡ overfit". Bạn tư vấn thế nào?

Hỏi trước: vấn đề thật là gì (training chậm? overfit đo được trên validation? latency khi serve?) và 300
feature gồm những gì.

Lập luận:

- Model cây không cần khử tương quan hay chuẩn hoá; PCA trộn feature thành tổ hợp tuyến tính, làm mất
  khả năng tách theo ngưỡng của từng feature, thường **giảm** chất lượng.
- PCA không nhìn target: thành phần variance nhỏ có thể chứa tín hiệu churn mạnh (vd. "số lần gọi tổng
  đài tuần trước" có variance nhỏ).
- Mất khả năng giải thích: SHAP trên "PC7" vô dụng với team CSKH.
- Thêm một bước phải fit trên train và lưu cùng model; dễ rò rỉ nếu fit trên toàn bộ dữ liệu.

Đề xuất: đo trước (LightGBM trên 300 feature có thật sự chậm hay overfit không); nếu overfit, dùng
regularization của chính LightGBM, feature selection theo importance / permutation trên validation, gộp
feature trùng lặp có chủ đích. PCA hợp lý cho một **nhóm** feature tương quan mạnh và thuần kỹ thuật
(embedding 300 chiều của văn bản), kiểm bằng validation theo thời gian. Quyết định bằng thí nghiệm, không
bằng niềm tin.

## Case study: một model chạy tốt trên CPU, chuyển sang GPU với mixed precision thì sau vài trăm bước loss thành NaN. Bạn debug thế nào?

Khoanh vùng theo thứ tự rẻ tới đắt:

1. **Tái lập và cô lập**: cố định seed, ghi lại bước đầu tiên có `inf`/`NaN` ở loss, gradient hay activation
   (`torch.autograd.detect_anomaly`, hook kiểm `isfinite` mỗi layer).
2. **Ổn định số trong loss**: có tự viết `log(softmax(x))` hay `log(sigmoid(x))` không? float16 chỉ tới khoảng
   65 504 và mất chính xác rất sớm; đổi sang `log_softmax`, `BCEWithLogitsLoss`, `logsumexp`.
3. **Gradient scaling**: mixed precision cần loss scaling (gradient nhỏ bị làm tròn thành 0, hoặc lớn bị
   tràn); dùng `GradScaler`, hoặc bfloat16 (dải số mũ như float32).
4. **Learning rate**: loss nổ dần trước khi NaN là dấu hiệu lr vượt ngưỡng ổn định; thử lr nhỏ hơn, warmup,
   gradient clipping.
5. **Dữ liệu**: batch có giá trị cực trị hoặc NaN đầu vào; chia cho độ lệch chuẩn bằng 0 khi chuẩn hoá.
6. **Phép chia / log / sqrt** tự viết: thêm epsilon đúng chỗ (`sqrt(x + eps)`, không phải `sqrt(x) + eps` khi
   cần gradient tại 0).

Nói rõ với team bước nào đã loại trừ, và thêm test (gradient check, kiểm `isfinite`) cho phần đã sửa.

## Case study: bạn và đồng nghiệp fit logistic regression trên cùng dữ liệu bằng hai thư viện, ra hệ số khác nhau ở chữ số thứ hai. PM hỏi cái nào đúng.

Logistic regression là bài toán convex: nếu cùng hàm mục tiêu và cả hai hội tụ thì **phải** ra cùng nghiệm.
Khác nhau nghĩa là một trong ba điều:

1. **Hàm mục tiêu khác**: sklearn mặc định có L2 với `C = 1.0`, statsmodels thì không; một bên có
   intercept, bên kia không; class weight; chuẩn hoá feature khác nhau. Ở bài Advanced 02, Newton tự viết khớp
   `LogisticRegression(C=np.inf)` tới 1e-5 và khớp bản có L2 khi đặt $$\lambda = 1/(Cn)$$.
2. **Chưa hội tụ**: `max_iter` mặc định quá ít (sklearn cảnh báo `ConvergenceWarning`), tolerance lỏng, feature
   chưa chuẩn hoá làm solver bậc một chậm. Kiểm chuẩn gradient tại nghiệm.
3. **Bài toán gần suy biến**: feature trùng lặp (nhiều nghiệm cho cùng loss) hoặc dữ liệu gần tách được (MLE
   không hữu hạn): hệ số phụ thuộc solver và điểm dừng.

Trả lời PM: "Không cái nào 'sai'; hai bên đang giải hai bài toán hơi khác nhau. Tôi sẽ thống nhất cấu hình
(regularization, intercept, chuẩn hoá), kiểm hội tụ, rồi hai bên sẽ khớp. Nếu vẫn lệch thì dữ liệu có
vấn đề và hệ số không nên dùng để ra quyết định." Ghi cấu hình vào tài liệu model để lần sau không lặp lại.
