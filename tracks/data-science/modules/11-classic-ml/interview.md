# Câu hỏi phỏng vấn: Classic Machine Learning

## Giải thích bias-variance tradeoff. Làm sao biết model của bạn đang bị cái nào?

Sai số kỳ vọng trên dữ liệu mới tách được thành ba phần: bias² (model quá đơn giản, sai một cách hệ thống),
variance (model nhạy với tập train cụ thể, đổi tập train là đổi dự đoán) và noise (không model nào loại được):

$$
\mathbb{E}\big[(y - \hat f(x))^2\big] = \text{bias}^2 + \text{variance} + \sigma^2
$$

Tăng độ linh hoạt (cây sâu hơn, k nhỏ hơn trong kNN, regularization yếu hơn) giảm bias và tăng variance.

Chẩn đoán trong thực tế:

- Train tốt, validation kém hơn nhiều: variance cao. Regularize, giảm độ sâu, thêm dữ liệu, bagging.
- Train và validation đều kém, gần nhau: bias cao. Feature tốt hơn, model linh hoạt hơn, bớt regularization.
- Learning curve: nếu đường validation đã phẳng khi tăng cỡ train thì thêm dữ liệu cùng loại không giúp.

Chi tiết senior: khoảng cách train/validation lớn không tự nó là lỗi. Random forest trên Olist có train
ROC-AUC 0.918, validation 0.806, nhưng vẫn là model có validation tốt nhất. Chọn theo điểm validation, không
theo khoảng cách.

## Logistic regression khác linear regression thế nào? Vì sao không dùng linear regression cho nhãn 0/1?

Logistic mô hình hoá log-odds là hàm tuyến tính, $$\log\frac{p}{1-p} = w^\top x + b$$, và học bằng cực đại
likelihood Bernoulli (tức cực tiểu log loss). Linear regression trên nhãn 0/1 (linear probability model) cho
dự đoán ngoài [0, 1], phương sai sai số phụ thuộc x, và bị kéo bởi các điểm xa ngưỡng.

Linear probability model không phải lúc nào cũng sai: trong kinh tế lượng người ta vẫn dùng nó để ước lượng
tác động trung bình vì hệ số dễ đọc (module 05). Nhưng để dự đoán xác suất thì dùng logistic.

Hệ số logistic: tăng x một đơn vị thì odds nhân với $$e^{w}$$. Không đọc hệ số như nhân quả, và khi feature
tương quan mạnh thì hệ số không ổn định (dùng L2).

## L1 và L2 regularization khác nhau thế nào? Khi nào dùng cái nào?

- **L2 (ridge)**: phạt tổng bình phương hệ số. Co mọi hệ số về gần 0 nhưng hiếm khi bằng 0. Ổn định khi feature
  tương quan (chia trọng số cho cả nhóm). Mặc định tốt.
- **L1 (lasso)**: phạt tổng trị tuyệt đối. Đẩy nhiều hệ số về đúng 0, tự chọn feature. Khi feature tương quan,
  chọn gần như ngẫu nhiên một cái trong nhóm, và lựa chọn đó không ổn định giữa các lần train.
- **Elastic net**: kết hợp, giữ được tính thưa của L1 mà ổn định hơn với nhóm tương quan.

Lỗi hay gặp: không scale feature trước khi regularize (feature đơn vị nhỏ bị phạt oan); quên rằng `C` trong
sklearn là nghịch đảo độ mạnh; dùng L1 để "tìm feature quan trọng" rồi diễn giải như nhân quả.

## Random forest giảm variance thế nào? Vì sao nó cần chọn ngẫu nhiên tập con feature?

Trung bình B model có cùng variance $$\sigma^2$$ và tương quan đôi một $$\rho$$ có variance:

$$
\rho\,\sigma^2 + \frac{1 - \rho}{B}\,\sigma^2
$$

Tăng số cây chỉ triệt được phần thứ hai. Phần đầu chỉ giảm khi các cây **ít tương quan**. Bootstrap mỗi cây
một mẫu khác làm giảm tương quan một ít; chọn ngẫu nhiên tập con feature ở mỗi lần chia (`max_features`) làm
giảm nhiều hơn, vì không cho mọi cây cùng dùng feature mạnh nhất ở gốc.

Đánh đổi: `max_features` nhỏ thì cây yếu hơn từng cây (bias tăng) nhưng ít tương quan hơn. Random forest ít
khi overfit khi tăng số cây, nhưng vẫn overfit nếu từng cây quá sâu trên dữ liệu nhiễu (giới hạn bằng
`min_samples_leaf`). Nó không ngoại suy được ngoài khoảng giá trị đã thấy ở train.

## So sánh kNN, SVM, decision tree, random forest, logistic regression. Bạn chọn gì cho dữ liệu bảng 50 nghìn dòng, 30 feature?

Bắt đầu bằng logistic regression làm baseline (nhanh, giải thích được, xác suất ổn định), rồi gradient
boosting hoặc random forest làm ứng viên chính. kNN kém ở nhiều chiều và chậm khi dự đoán; SVM kernel RBF tốn
thời gian bậc hai theo số dòng và không cho xác suất trực tiếp. Một cây đơn lẻ chỉ khi cần luật dễ đọc cho
người vận hành.

Điều quan trọng hơn thuật toán: feature, cách chia dữ liệu theo đúng cách model được dùng, và metric đúng.
Trên Olist, bốn model hợp lý cách nhau chưa tới 0.015 ROC-AUC; thêm một feature tốt (lịch sử seller) thường
đáng hơn đổi thuật toán.

## ROC-AUC và PR-AUC khác nhau thế nào? Khi nào dùng cái nào?

- **ROC-AUC**: xác suất một ca dương ngẫu nhiên có điểm cao hơn một ca âm ngẫu nhiên. Đoán bừa cho 0.5 bất kể
  tỉ lệ dương. Không nhạy với tỉ lệ dương, nên so sánh được giữa các tập.
- **PR-AUC (average precision)**: tóm tắt precision trên mọi mức recall. Đoán bừa cho PR-AUC bằng tỉ lệ dương.
  Nhạy với chất lượng ở top danh sách.

Khi dữ liệu rất mất cân bằng (fraud 0.17%), ROC-AUC 0.95 vẫn có thể nghĩa là top 1 000 cảnh báo chủ yếu là
báo nhầm, vì FPR nhỏ nhân với số ca âm khổng lồ vẫn là nhiều FP. PR-AUC phơi bày điều đó. Dùng PR-AUC (hoặc
precision@N) khi hành động là "xem top N"; dùng ROC-AUC khi cần một metric thứ hạng ổn định qua các tập có tỉ
lệ dương khác nhau.

Lưu ý: PR-AUC thay đổi khi tỉ lệ dương thay đổi. Trên Olist, validation có 18.0% review xấu, test có 10.4%;
PR-AUC của cùng một model rơi từ 0.611 xuống 0.337, một phần chỉ vì tỉ lệ nền.

## Log loss và Brier score đo gì? Vì sao một model có ROC-AUC tốt lại có log loss tệ?

Cả hai đo chất lượng **xác suất**, không chỉ thứ hạng. Log loss phạt cực nặng dự đoán tự tin mà sai (p = 0.001
cho ca dương tốn gần 7 đơn vị); Brier là bình phương sai số, bị chặn trong [0, 1].

ROC-AUC chỉ phụ thuộc thứ hạng, nên mọi phép biến đổi đơn điệu (bình phương xác suất) giữ nguyên ROC-AUC
nhưng đổi log loss. Cây quyết định mọc hết cho xác suất 0 hoặc 1: trên Olist, log loss validation của nó là
7.2 so với khoảng 0.34 của random forest. Khi xác suất được dùng trực tiếp (ngưỡng theo chi phí, dự báo số
lượng), phải nhìn log loss hoặc Brier và reliability curve.

## Làm sao chọn ngưỡng phân loại? Vì sao không dùng 0.5?

0.5 chỉ tối ưu khi FP và FN tốn như nhau và xác suất calibrated. Với chi phí $$C_{FP}$$, $$C_{FN}$$ (TP, TN
tốn 0), dự đoán dương khi chi phí kỳ vọng của hành động nhỏ hơn không hành động:

$$
(1 - p)\,C_{FP} \le p\,C_{FN} \iff p \ge \frac{C_{FP}}{C_{FP} + C_{FN}}
$$

Trên Olist với liên hệ 5 R$, bỏ lỡ 30 R$: ngưỡng lý thuyết 0.143; chi phí mỗi đơn trên test 2.28 R$ so với
2.63 R$ ở ngưỡng 0.5 và 3.11 R$ khi không liên hệ ai.

Trong thực tế:

1. Nếu xác suất chưa calibrated, quét ngưỡng trên validation theo chi phí, chấm trên test.
2. Ràng buộc năng lực (chỉ gọi được N đơn) biến bài toán thành top-N.
3. Chi phí là giả định: luôn kèm phân tích độ nhạy.
4. Không chọn ngưỡng trên test.

## Dữ liệu chỉ có 1% ca dương. Bạn xử lý thế nào?

Trước hết hỏi vấn đề thật là gì:

- **Metric**: bỏ accuracy (99% bằng cách đoán toàn âm). Dùng PR-AUC, recall tại precision cố định, hoặc chi phí.
- **Ngưỡng**: thường là việc duy nhất cần làm. Model calibrated + ngưỡng theo chi phí.
- **Số ca dương tuyệt đối**: 1% của 10 triệu là 100 nghìn ca, đủ học. 1% của 5 nghìn là 50 ca: vấn đề là dữ
  liệu, không resampling nào tạo ra thông tin mới. Thu thêm nhãn, dùng luật chuyên gia, hoặc anomaly detection
  (module 12).

Nếu vẫn dùng class_weight hay resampling: chỉ resample **trong** từng fold train (làm trước khi chia là
leakage, và test không còn phản ánh tỉ lệ thật), và nhớ xác suất bị lệch, phải prior-correct hoặc
recalibrate nếu dùng xác suất. Undersample có ích thật khi dữ liệu quá lớn để train nhanh.

Câu trả lời yếu: "dùng SMOTE" như phản xạ, không nói vì sao và không kiểm tra calibration.

## Model calibrated là gì? Khi nào cần, và làm sao sửa?

Calibrated: trong các ca được dự đoán 30%, khoảng 30% thật sự dương. Đo bằng reliability curve, Brier, ECE.

Cần khi dùng xác suất trực tiếp: ngưỡng theo chi phí bằng công thức, dự báo tổng ("quý này mất bao nhiêu
khách" bằng tổng xác suất), định giá rủi ro, kết hợp nhiều model. Không cần nếu chỉ xếp hạng top N.

Model hay lệch: cây đơn lẻ, SVM, Naive Bayes, boosting train quá lâu, mọi model dùng class_weight hay
resampling. Logistic regression và random forest có `min_samples_leaf` hợp lý thường gần calibrated (trên
Telco, ECE khoảng 0.02).

Sửa bằng một hàm đơn điệu học trên tập calibration riêng: Platt (sigmoid, ít tham số) khi dữ liệu ít; isotonic
khi có vài nghìn ca trở lên. Calibration hỏng theo thời gian khi tỉ lệ nền đổi, nên phải theo dõi và
calibrate lại trên dữ liệu gần đây.

## Bạn tuning siêu tham số thế nào? Làm sao tránh overfit tập validation?

Random search là mặc định cho 3+ tham số (cùng ngân sách, tốt hơn grid vì thường chỉ vài tham số quan trọng);
Bayesian optimization (Optuna) khi mỗi lần fit đắt. Mọi preprocessing nằm trong `Pipeline` để CV không leak.
Cách chia CV giống cách model được dùng (theo thời gian, theo nhóm).

Tránh overfit validation:

- Giới hạn ngân sách tuning trước khi bắt đầu.
- Test chỉ chấm một lần ở cuối.
- Nested CV khi cần ước lượng không chệch của cả quy trình (vòng trong tuning, vòng ngoài đánh giá).
- So với baseline: trên Telco, random forest tuning 12 cấu hình đạt test ROC-AUC 0.847, bằng đúng logistic
  regression không tuning. Biết dừng là kỹ năng senior.

## Bạn có model churn với SHAP cho thấy "hợp đồng tháng" là yếu tố quan trọng nhất. Giám đốc muốn tặng ưu đãi để chuyển khách sang hợp đồng năm. Bạn tư vấn gì?

(Product sense / case study.) SHAP giải thích **model**, không giải thích **tác động của việc thay đổi
feature**. Khách chọn hợp đồng năm vốn khác khách hợp đồng tháng (gắn bó hơn, ổn định tài chính hơn). Tỉ lệ
churn 42.7% so với 11.3% ở hợp đồng 1 năm là tương quan, có confounding.

Tư vấn:

1. Ưu đãi có thể vẫn đúng, nhưng tác động thật chưa biết. Nếu ép khách sắp rời đi ký hợp đồng năm, họ có thể
   rời đi khi hết hợp đồng, hoặc ưu đãi chỉ đến tay khách vốn không định rời (tốn tiền vô ích).
2. Chạy thí nghiệm: random khách hợp đồng tháng có nguy cơ cao vào nhóm nhận ưu đãi và nhóm không; đo churn
   sau 6–12 tháng và doanh thu ròng sau khi trừ ưu đãi (module 03).
3. Nhắm theo **uplift** (ai thay đổi hành vi nhờ ưu đãi) chứ không chỉ theo rủi ro churn: người chắc chắn
   rời đi và người chắc chắn ở lại đều không đáng tặng.
4. Trong lúc chờ, dùng causal inference trên dữ liệu quan sát (khách đã từng đổi hợp đồng) để có ước lượng
   sơ bộ, kèm cảnh báo về confounding (module 06).

## Đội CSKH muốn model dự đoán đơn sẽ bị review xấu để gọi điện trước. Bạn thiết kế thế nào từ đầu tới cuối?

(Case study.) Các quyết định theo thứ tự:

1. **Thời điểm dự đoán và hành động**: lúc đơn vừa giao (biết thời gian giao, trễ bao nhiêu; mọi cột review là leakage) hay lúc mua / lúc giao cho hãng vận chuyển (bài toán khác, phải bỏ mọi kết quả giao hàng; can
   thiệp sớm hơn nhưng ít thông tin)? Feature chỉ lấy những gì biết tại thời điểm đó. Trễ là tín hiệu mạnh
   nhất: 54% đơn trễ bị review xấu so với khoảng 9% đơn đúng hẹn.
2. **Nhãn**: review mới nhất ≤ 2 sao. Đơn không có review? Nếu loại, model chỉ áp dụng cho người sẽ review.
3. **Chia theo thời gian**, không ngẫu nhiên. Trên Olist, validation (Q1/2018) có tỉ lệ trễ 14.4%, test
   5.9%: điểm số và xác suất đổi theo.
4. **Model**: baseline logistic, rồi random forest / boosting. Metric: PR-AUC và chi phí tại ngưỡng.
5. **Ngưỡng theo chi phí và năng lực**: chi phí gọi, thiệt hại một review xấu, tỉ lệ cuộc gọi thật sự cứu
   được; nếu CSKH chỉ gọi được 100 đơn mỗi tuần thì chọn top 100 theo điểm, không phải ngưỡng cố định (ngưỡng
   cố định cho số đơn mỗi tuần dao động theo mùa).
6. **Đo tác động thật** bằng thí nghiệm: random trong nhóm có điểm cao, nhóm được gọi và nhóm không.
   Model tốt chưa chắc can thiệp có tác dụng.
7. **Theo dõi**: drift tỉ lệ trễ, calibration theo tháng; và **feedback loop**: khi đơn được gọi không còn bị
   review xấu, nhãn tương lai bị can thiệp làm thay đổi, train lại ngây thơ sẽ học sai.

## Model của bạn đạt ROC-AUC 0.81 trên validation nhưng chỉ 0.69 trên test. Bạn điều tra thế nào?

(Case study, chính là chuyện xảy ra trên Olist.) Thứ tự kiểm tra:

1. **Leakage ở validation?** Feature nào dùng thông tin tương lai? Validation có bị dùng để chọn quá nhiều thứ
   (overfit validation)?
2. **Phân phối thay đổi?** So tỉ lệ dương và phân phối feature giữa các tập. Olist: validation có 14.4% đơn
   trễ (đơn trễ dễ đoán: 63% bị review xấu), test chỉ 5.9% và đơn trễ ở test chỉ 39% bị review xấu. Tập test
   "khó" hơn, không phải model hỏng.
3. **Chấm theo lát cắt**: ROC-AUC trong nhóm đơn đúng hẹn, trong nhóm đơn trễ. Nếu từng lát cắt ổn định thì
   khác biệt đến từ cơ cấu (mix shift).
4. **Hành động**: báo cáo con số test (trung thực về hiệu năng tương lai), calibrate lại trên dữ liệu gần nhất,
   train lại với dữ liệu tới gần thời điểm triển khai, theo dõi drift. Nếu feature mạnh nhất mất tác dụng theo
   thời gian, tìm feature bền hơn.

## Khi nào bạn dùng k-means, khi nào DBSCAN? Chọn k thế nào?

k-means: cụm gần cầu, cỡ tương đương, dữ liệu lớn; cần chọn k; nhạy với scale và outlier. DBSCAN: cụm hình dạng
bất kỳ, tự tách nhiễu, không cần k nhưng cần `eps` và `min_samples`; kém khi mật độ các cụm khác nhau và khi
nhiều chiều (HDBSCAN tốt hơn).

Chọn k: elbow, silhouette, độ ổn định khi chạy lại với seed hoặc mẫu khác, và quan trọng nhất là **dùng được
không**. Trên RFM Olist, silhouette cao nhất ở k = 2, nhưng hai cụm đó chỉ là "mua một lần" và "mua nhiều
lần", điều một dòng `frequency > 1` làm được. k = 4 cho các nhóm có hành động CRM riêng.

Lỗi hay gặp: không scale (k-means trên RFM thô chia gần như chỉ theo tiền), không log-transform dữ liệu lệch,
diễn giải cụm như "loại khách có thật" thay vì một cách chia tiện dụng.

## Đội marketing muốn "phân khúc khách hàng bằng AI". Bạn làm gì?

(Product sense.) Hỏi trước: phân khúc để **làm gì**? Mỗi phân khúc sẽ nhận hành động khác nhau nào? Nếu không
có hành động khác nhau thì phân khúc vô ích.

- Nếu mục tiêu là "ai sẽ quay lại mua" hay "ai sắp rời đi": đó là bài supervised, có nhãn, đo được. Dùng model
  dự đoán, không dùng phân cụm.
- Nếu mục tiêu là hiểu và giao tiếp (persona cho đội nội dung): RFM theo luật (ngũ phân vị) thường đủ, dễ giải
  thích, ổn định theo thời gian. k-means khi có nhiều feature hành vi và muốn khám phá.
- Với Olist, 97% khách chỉ mua một lần: phân khúc theo hành vi mua lặp gần như vô nghĩa. Phân khúc theo danh
  mục sản phẩm, vùng, hoặc trải nghiệm giao hàng có thể hữu ích hơn.
- Đánh giá phân khúc bằng kết quả kinh doanh: chiến dịch nhắm theo phân khúc có hơn chiến dịch đại trà không
  (thí nghiệm).

## Permutation importance và SHAP khác nhau thế nào? Cạm bẫy của chúng?

- **Permutation importance**: global, đo metric giảm bao nhiêu khi hoán vị một feature trên tập held-out. Áp
  dụng cho mọi model, đo đúng đóng góp vào hiệu năng dự đoán.
- **SHAP**: phân bổ dự đoán của **từng dòng** cho các feature (Shapley value), cộng lại bằng dự đoán. Có cả
  local (giải thích một khách) lẫn global (trung bình |SHAP|).
- **MDI** (`feature_importances_`): tính trên train, thiên vị feature liên tục / nhiều giá trị. Chỉ xem nhanh.

Cạm bẫy chung: feature tương quan chia nhau importance (trên Telco, `MonthlyCharges` có permutation importance
gần 0 vì `TotalCharges ≈ tenure × MonthlyCharges` bù lại); hoán vị tạo dòng phi thực tế; giải thích một model
tệ; và lớn nhất: đọc importance như nhân quả. "Feature X quan trọng với model" khác "thay đổi X sẽ đổi kết quả".

## PCA dùng khi nào? Có nên luôn chạy PCA trước khi train model không?

PCA tìm hướng trực giao có phương sai lớn nhất. Dùng để vẽ dữ liệu nhiều chiều, nén nhóm feature tương quan
cao (cho model tuyến tính, hoặc khi chi phí lưu trữ/tính toán lớn), khử nhiễu.

Không nên chạy theo phản xạ: hướng có phương sai lớn không nhất thiết liên quan tới nhãn (PCA không nhìn nhãn);
thành phần chính khó giải thích; model cây không hưởng lợi gì; phải chuẩn hoá trước vì PCA nhạy với scale.
Trên RFM Olist đã chuẩn hoá, ba thành phần giải thích 38.9%, 33.3%, 27.8% phương sai: các feature gần như độc
lập, PCA không nén được gì.
