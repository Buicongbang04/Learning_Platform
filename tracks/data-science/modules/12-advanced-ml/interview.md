# Câu hỏi phỏng vấn: Advanced ML

## Bagging và boosting khác nhau thế nào? Mỗi cái giảm bias hay variance?

**Bagging** train nhiều model song song trên các mẫu bootstrap rồi lấy trung bình. Base learner là
cây sâu (bias thấp, variance cao); lấy trung bình giảm variance, bias giữ nguyên. Random forest thêm
chọn ngẫu nhiên feature ở mỗi nút để các cây bớt tương quan, vì variance của trung bình là
$$\rho\sigma^2 + (1 - \rho)\sigma^2 / B$$: thêm cây chỉ xoá được số hạng sau.

**Boosting** train tuần tự, mỗi model mới sửa lỗi của tổng các model trước. Base learner là cây nông
(bias cao); cộng dồn nhiều cây giảm bias. Learning rate nhỏ và subsampling giữ variance trong tầm
kiểm soát.

Hệ quả thực tế ứng viên senior nên nói:

- Random forest gần như không overfit khi thêm cây, tham số mặc định thường ổn: baseline nhanh.
- Boosting thường thắng trên dữ liệu bảng nhưng **có thể overfit khi thêm cây**, cần early stopping
  và tune.
- Bagging song song hoá theo cây; boosting không, nên các thư viện song song hoá **bên trong** mỗi
  cây (theo feature, theo bin của histogram).

Ví dụ thật trên Olist (bài toán review xấu, 7 feature): một cây sâu có AUC test 0.572, bagging 100
cây sâu 0.669, random forest 0.688, LightGBM 0.690.

## Giải thích gradient boosting cho người đã biết gradient descent.

Gradient descent thường cập nhật **tham số**. Gradient boosting cập nhật **hàm dự đoán**: coi giá
trị dự đoán $$F(x_i)$$ của từng điểm là "tham số", tính gradient của loss theo nó, rồi đi một bước
ngược gradient. Vì gradient chỉ biết tại các điểm train, ta fit một cây hồi quy vào negative gradient
(pseudo-residual) để tổng quát hoá cho điểm mới, và cộng cây đó (nhân learning rate) vào mô hình.

- Squared loss: negative gradient là phần dư $$y - F$$.
- Log loss với $$F$$ là logit: negative gradient là $$y - p$$, Hessian là $$p(1 - p)$$. XGBoost/LightGBM
  dùng cả hai cho bước Newton, giá trị lá $$-G / (H + \lambda)$$.
- Absolute loss: negative gradient là dấu của phần dư, giá trị lá đặt lại bằng median phần dư.

Điểm hay bị hỏi tiếp: vì sao cây? Cây bắt được tương tác và phi tuyến, không cần chuẩn hoá, xử lý
giá trị thiếu, nhanh với histogram. Vì sao cây nông? Mỗi bước nên là một cải thiện nhỏ, "weak
learner"; cây sâu ở mỗi bước làm boosting overfit rất nhanh.

## XGBoost cải tiến gì so với gradient boosting cổ điển (Friedman)?

1. **Objective có regularization**: phạt số lá ($$\gamma$$) và bình phương giá trị lá ($$\lambda$$). Giá trị lá
   tối ưu $$-G/(H + \lambda)$$, và gain của một lần tách có trừ $$\gamma$$: cây tự dừng khi tách không
   đáng.
2. **Khai triển bậc hai** (gradient + Hessian): một công thức chung cho mọi loss khả vi hai lần, hội
   tụ nhanh hơn.
3. **Sparsity-aware split**: học hướng mặc định cho giá trị thiếu ở mỗi nút.
4. **Hệ thống**: histogram / quantile sketch cho điểm cắt, cấu trúc dữ liệu theo cột, cache-aware,
   out-of-core, GPU.
5. Subsampling dòng và cột, `min_child_weight` (tổng Hessian tối thiểu của lá).

Câu trả lời tốt nhắc thêm rằng phần lớn khác biệt trong thực tế đến từ (4): XGBoost phổ biến vì nó
nhanh và chạy được trên dữ liệu lớn, không chỉ vì toán.

## LightGBM khác XGBoost ở điểm nào? `num_leaves` và `max_depth` liên quan gì?

- **Leaf-wise growth**: LightGBM tách lá có gain lớn nhất trên toàn cây, XGBoost mặc định tách theo
  tầng. Cùng số lá, leaf-wise giảm loss nhiều hơn nhưng có thể sinh nhánh rất sâu và overfit dữ liệu
  nhỏ.
- **GOSS** (giữ dòng gradient lớn, lấy mẫu dòng gradient nhỏ), **EFB** (gộp feature thưa loại trừ
  nhau): nhanh hơn trên dữ liệu lớn, nhiều cột thưa.
- **Categorical native**: tách theo thứ tự giá trị sắp bằng thống kê gradient, không cần one-hot.

`num_leaves` là tham số độ phức tạp chính của LightGBM. Cây depth-wise độ sâu d có tối đa $$2^d$$ lá;
đặt `num_leaves` gần $$2^{\text{max\_depth}}$$ thì leaf-wise gần như không còn ưu thế, đặt nhỏ hơn hẳn
(ví dụ `max_depth=8`, `num_leaves=63`) để có cây sâu một số nhánh mà vẫn ít lá. Với dữ liệu nhỏ, tăng
`min_data_in_leaf` trước khi nghĩ tới tham số khác.

## Bạn tune một model LightGBM như thế nào?

1. Baseline với tham số mặc định hợp lý, learning rate 0.1, **early stopping** trên validation theo
   thời gian để số cây không phải là tham số tune.
2. Độ phức tạp cây: `num_leaves`, `min_data_in_leaf` (và `max_depth` nếu cần). Đây là nhóm ảnh hưởng
   lớn nhất.
3. Subsampling: `feature_fraction`, `bagging_fraction` + `bagging_freq`.
4. Regularization: `lambda_l2`, `lambda_l1`, `min_gain_to_split`.
5. Hạ learning rate (0.02–0.05) và để early stopping chọn lại số cây.

Công cụ: random search hoặc Bayesian (Optuna) trên CV theo thời gian, không grid search. Điều nói
lên kinh nghiệm: biết khi nào **dừng tune**. Trên Olist, learning rate từ 0.05 xuống 0.02 làm số cây
tăng từ 117 lên 261 mà AUC test không đổi (0.707). Tune thêm thường kém hiệu quả hơn một feature tốt.

## Early stopping hoạt động thế nào và hay sai ở đâu?

Sau mỗi vòng, tính metric trên tập validation; nếu `patience` vòng liên tiếp không cải thiện thì
dừng và dùng model tại vòng tốt nhất (`best_iteration`).

Sai lầm hay gặp:

- Dùng test làm tập early stopping: số cây được chọn theo test, con số test không còn khách quan.
- Validation không cùng phân phối với production (chia ngẫu nhiên trên dữ liệu thời gian, hoặc
  validation rơi vào giai đoạn bất thường).
- Dừng theo AUC: AUC phẳng lâu, dừng muộn; log loss mượt hơn.
- Quên dùng `best_iteration` khi dự đoán sau khi lưu và nạp lại model.
- Patience quá nhỏ với learning rate nhỏ: dừng ở một đoạn phẳng tạm thời.

Sau khi chọn số cây, thường train lại trên train + validation. Trên Olist, train lại với cùng 117
cây cho AUC test 0.714 so với 0.707.

## Model boosting của bạn có AUC validation 0.82 nhưng AUC trên dữ liệu mới chỉ 0.71. Bạn chẩn đoán thế nào?

Đây đúng là chuyện xảy ra với model review xấu của Olist: validation là quý 1/2018, test là 2018-04
tới 2018-08.

1. **Kiểm leakage trước**: feature nào chỉ biết sau thời điểm dự đoán? Có cột nào được tính trên
   toàn bộ dữ liệu (target encoding không out-of-fold)?
2. **So phân phối** giữa hai giai đoạn: tỉ lệ nhãn (review xấu 18.0% ở validation, 10.4% ở test),
   phân phối feature quan trọng. Trên Olist, tháng 2–3/2018 có 16–21% đơn giao trễ, trong khi các tháng
   từ 6/2017 tới 8/2018 còn lại đều dưới 10% (trừ tháng 11/2017, 14%); khi trễ nhiều, "trễ → review xấu" dễ phân biệt nên AUC cao.
3. **Đánh giá theo nhiều cửa sổ thời gian** (rolling origin) để thấy độ dao động thật.
4. **Lát cắt**: AUC theo bang, theo danh mục, theo đơn trễ/không trễ. AUC chung giảm có thể chỉ vì
   tỉ lệ đơn "dễ" giảm (ít đơn trễ), không phải vì model kém đi.

Kết luận thường gặp: model không hỏng, validation không đại diện. Hành động: báo cáo hiệu năng bằng
khoảng trên nhiều giai đoạn, giám sát drift, và nếu cần, feature mô tả "tình trạng vận hành" hiện
tại.

## Stacking là gì? Làm sao để không rò rỉ dữ liệu? Khi nào không nên dùng?

Stacking học một meta-model trên dự đoán của các model tầng 1. Để không rò rỉ, meta-model phải học
trên dự đoán **out-of-fold**: mỗi dòng được dự đoán bởi model không thấy dòng đó. Với dữ liệu thời
gian, fold phải mở rộng theo thời gian và khối đầu không có OOF. Model tầng 1 dùng cho test được fit
lại trên toàn bộ dữ liệu dev. Meta-model mặc định là logistic regression trên logit của dự đoán.

Không nên khi các model tầng 1 tương quan cao (LightGBM và random forest trên Olist có tương quan OOF
0.98), khi lợi ích không tách khỏi nhiễu, hoặc khi chi phí vận hành quan trọng. Trên Olist, stacking
ba model hơn LightGBM đơn −0.001 AUC với CI bootstrap khoảng [−0.004, +0.002]: không đáng.

## Feature importance của gradient boosting có đáng tin không?

Có ba loại thường gặp:

- **Split count**: số lần feature được dùng để tách. Thiên về feature liên tục nhiều giá trị.
- **Gain**: tổng giảm loss nhờ feature. Tốt hơn nhưng vẫn thiên về feature nhiều giá trị và chia
  công không đều giữa các feature tương quan.
- **SHAP** (TreeSHAP) và **permutation importance** trên tập giữ lại: nhất quán hơn, cho cả hướng tác
  động (module 11).

Mọi loại đều đo **model dùng gì**, không đo **nhân quả**. Hai feature tương quan cao chia nhau
importance tuỳ ngẫu nhiên. Trên Olist, `days_vs_estimate` chiếm 37% gain: điều đó nói model dựa vào
độ trễ, không chứng minh giảm trễ sẽ giảm review xấu bao nhiêu (câu hỏi đó thuộc module 06).

## Bạn đánh giá offline một recommender system thế nào?

- **Split theo thời gian**: mỗi user, phần tương tác mới nhất làm test; hoặc một mốc thời gian chung.
  Không chia ngẫu nhiên theo dòng.
- **Metric xếp hạng @k**: precision@k, recall@k, MAP@k, NDCG@k, hit rate. Lấy trung bình trên mọi
  user của test, kể cả user hệ thống không gợi ý được.
- **Ngoài độ chính xác**: coverage, diversity, novelty, độ phổ biến trung bình của item được gợi ý.
- **Baseline**: popularity luôn phải có. Trên MovieLens, popularity đạt precision@10 0.075; item-item
  0.097. Một hệ thống không thắng popularity thì chưa sẵn sàng.
- **Giới hạn**: dữ liệu là kết quả của hệ thống cũ (user chỉ tương tác với cái họ được thấy), nên
  offline thiên về thuật toán giống hệ thống cũ. Quyết định cuối bằng A/B test.

## Item-item CF và matrix factorization khác nhau thế nào? ALS hay SGD?

**Item-item**: độ giống giữa item tính từ các user cùng tương tác (cosine, Jaccard); gợi ý item giống
lịch sử. Giải thích được, ổn định khi số user thay đổi nhanh hơn số item, tính trước hàng xóm offline.

**Matrix factorization**: học vector ẩn cho user và item, điểm là tích vô hướng (cộng bias). Nén
thông tin toàn cục, gọn, làm candidate generation bằng tìm kiếm láng giềng gần đúng (ANN).

**ALS** cố định một phía, giải ridge regression cho phía kia, song song hoá theo user/item, không cần
learning rate, hợp với implicit feedback (iALS). **SGD** linh hoạt (thêm feature, loss xếp hạng như
BPR), phải chọn learning rate.

Bẫy: MF tối ưu RMSE trên rating đã quan sát không tối ưu top-k. Trên MovieLens, MF có RMSE 0.893
(tốt hơn baseline bias 0.902) nhưng precision@10 chỉ 0.071: không thắng popularity (0.075; chênh lệch
nằm trong nhiễu với 610 user) và thua xa item-item (0.097).

## Cold start là gì và xử lý ra sao?

- **User mới**: chưa có lịch sử. Popularity theo ngữ cảnh (vùng, giờ, nguồn), onboarding hỏi sở
  thích, dùng feature nhân khẩu học/thiết bị, chuyển dần sang CF khi có vài tương tác.
- **Item mới**: chưa ai tương tác. Content-based (thể loại, mô tả, ảnh embedding), hybrid model dùng
  feature item, slot cho item mới, exploration (multi-armed bandit) có ngân sách.
- **Hệ thống mới**: chưa có dữ liệu. Luật biên tập, popularity, content-based.

Đo được độ lớn của vấn đề trước khi giải: trên MovieLens split theo thời gian, 8.3% rating test thuộc
phim chưa có trong train, mà CF không bao giờ gợi ý được.

## Isolation forest hoạt động thế nào? Khi nào nó thất bại?

Xây nhiều cây ngẫu nhiên trên mẫu nhỏ (256 điểm): mỗi nút chọn ngẫu nhiên feature và ngưỡng. Điểm
bất thường bị cô lập sau ít lần cắt; điểm bất thường là $$2^{-E[h(x)]/c(n)}$$ với $$E[h(x)]$$ là độ sâu
trung bình. Nhanh, không cần chuẩn hoá, ít tham số.

Thất bại khi:

- Bất thường nằm **lệch khỏi cấu trúc** của dữ liệu nhưng không cực đoan trên trục nào (cắt song
  song trục không cô lập được). PCA reconstruction hay autoencoder bắt tốt hơn.
- Nhiều feature nhiễu không liên quan: cắt ngẫu nhiên trên feature nhiễu làm loãng tín hiệu.
- Bất thường theo **ngữ cảnh** (chi 5 triệu bình thường với khách này, bất thường với khách kia):
  cần feature theo hành vi của từng thực thể.
- Bất thường **theo nhóm** (một đợt tấn công nhiều giao dịch giống nhau): chúng không còn "hiếm".

## Vì sao không dùng ROC-AUC để đánh giá hệ thống phát hiện gian lận?

ROC-AUC dựa trên FPR, mà mẫu số của FPR là số giao dịch bình thường, khổng lồ. Trên bộ Credit Card
Fraud, ngày thứ hai có 140 021 giao dịch, 211 gian lận: isolation forest có ROC-AUC 0.956, nhưng FPR
1% đã là khoảng 1 400 báo động sai. PR-AUC chỉ 0.130 và precision trong 100 cảnh báo đầu là 0.26.
LightGBM có ROC-AUC **thấp hơn** (0.869) nhưng PR-AUC 0.621 và 95/100 cảnh báo đầu là thật: hai metric
xếp hạng hai model ngược nhau.

Nên báo: precision và recall tại **ngân sách cảnh báo** của đội điều tra, PR-AUC để so model, và chi
phí kỳ vọng (gian lận lọt lưới so với chi phí điều tra). Chia theo thời gian và tính độ trễ của nhãn.

## Autoencoder dùng cho anomaly detection như thế nào? Rủi ro chính là gì?

Học nén rồi dựng lại dữ liệu; điểm bất thường là sai số dựng lại. PCA là trường hợp tuyến tính và
nên thử trước. Rủi ro chính là **contamination**: dữ liệu học lẫn bất thường thì mô hình học luôn cách
dựng lại chúng. Trên Credit Card Fraud, PCA 15 thành phần học trên mọi giao dịch ngày 1 cho PR-AUC
0.041; học chỉ trên giao dịch không gian lận cho 0.209. Trong thực tế "sạch" nghĩa là đã qua thời
hạn khiếu nại mà không bị báo, hoặc lọc bớt điểm có điểm bất thường cao rồi fit lại. Rủi ro khác:
autoencoder đủ mạnh dựng lại được cả bất thường (cần nút thắt đủ hẹp, regularization), và ngưỡng phải
chọn theo ngân sách cảnh báo, không theo "phân vị 99" tuỳ tiện.

## Case: Thiết kế hệ thống gợi ý sản phẩm cho Olist (marketplace). Bạn bắt đầu từ đâu?

**Hiểu bài toán trước**: Olist là marketplace, phần lớn khách chỉ mua một lần (khách quay lại hiếm),
sản phẩm bền (đồ gia dụng, nội thất). Collaborative filtering theo user gần như không có dữ liệu.

- **Mục tiêu**: GMV từ gợi ý? Tỉ lệ mua thêm (cross-sell)? Tránh gợi ý seller giao trễ (review xấu
  là chi phí thật)? Chọn một metric chính và guardrail (tỉ lệ review xấu, tỉ lệ huỷ).
- **Bề mặt**: trang sản phẩm ("thường mua cùng" là item-item trên giỏ hàng/phiên), email sau giao
  hàng (bổ sung, phụ kiện), trang chủ (popularity theo bang, theo mùa).
- **Cold start là trạng thái bình thường**: dùng item-item theo phiên và theo đơn, content-based theo
  danh mục, popularity theo vùng. Item mới của seller mới cần exploration có kiểm soát.
- **Ranking**: gradient boosting kết hợp điểm CF với feature như giá, phí ship tới bang của khách,
  thời gian giao dự kiến, điểm seller. Gợi ý sản phẩm giao trễ làm hỏng trải nghiệm dù khớp sở thích.
- **Đánh giá**: offline theo thời gian với recall@k cho candidate, NDCG cho ranking; online bằng
  A/B test theo khách, metric chính GMV/khách hoặc conversion, guardrail review xấu.

Điểm cộng: nhận ra dữ liệu Olist không hợp với CF kinh điển và đề xuất bắt đầu với "thường mua
cùng" + popularity theo bang trước khi xây MF.

## Case: Thiết kế hệ thống phát hiện gian lận cho một ví điện tử mới ra mắt, chưa có nhãn.

**Giai đoạn 0 (chưa nhãn)**: luật cứng từ chuyên gia (hạn mức, thiết bị mới + số tiền lớn, nhiều
tài khoản trên một thiết bị), cộng anomaly score (isolation forest trên feature hành vi: tần suất,
số tiền so với lịch sử của chính user, khoảng cách địa lý). Mọi cảnh báo vào hàng đợi điều tra theo
**ngân sách** (đội xem được bao nhiêu giao dịch/ngày), và quyết định của điều tra viên trở thành
nhãn.

**Giai đoạn 1 (có nhãn, chậm)**: model supervised (GBDT) trên nhãn điều tra và chargeback. Nhãn
chargeback về sau vài tuần: train trên dữ liệu đủ "chín", đánh giá theo thời gian. Anomaly score giữ
lại làm feature và để bắt kiểu tấn công mới.

**Vận hành**: ngưỡng theo chi phí (giá trị gian lận kỳ vọng so với chi phí điều tra và chi phí chặn
nhầm khách thật); ba vùng chặn / điều tra / cho qua; giám sát drift vì kẻ gian thích nghi; giữ một
phần nhỏ giao dịch không bị chặn (hoặc điều tra ngẫu nhiên) để có nhãn không thiên lệch, nếu không
model chỉ học được những gì hệ thống cũ đã bắt. Metric báo cáo: precision/recall tại ngân sách,
số tiền gian lận chặn được, tỉ lệ khách thật bị chặn nhầm.

## Case: Team muốn thay model LightGBM đang chạy bằng stacking 5 model vì offline AUC tăng 0.004. Bạn tư vấn gì?

1. **Lợi ích có thật không?** 0.004 AUC trên một tập test: bootstrap CI cho chênh lệch (trên Olist,
   chênh lệch cỡ này có CI chứa 0). Kiểm trên nhiều cửa sổ thời gian. OOF có đúng theo thời gian
   không?
2. **Lợi ích có giá trị kinh doanh không?** Quy ra quyết định: ở ngưỡng đang dùng, precision/recall
   đổi bao nhiêu, bao nhiêu đơn được xử lý đúng thêm, bao nhiêu tiền.
3. **Chi phí**: 5 model phải train, version, giám sát, retrain cùng nhịp; latency; độ phức tạp khi
   debug sự cố; thêm điểm hỏng (một feature pipeline đổi làm hỏng cả hệ).
4. **Lựa chọn rẻ hơn**: trung bình 2 model khác bản chất; đầu tư vào feature; tune lại LightGBM.
5. **Nếu vẫn muốn**: A/B test (hoặc shadow mode) với metric kinh doanh, không ship chỉ dựa trên
   offline AUC.

Câu trả lời tốt không nói "không bao giờ stacking", mà đặt lợi ích có khoảng tin cậy cạnh chi phí
vận hành và để số liệu quyết định.
