# Câu hỏi phỏng vấn: Causal Inference

## Tương quan khác nhân quả thế nào? Cho một ví dụ từ sản phẩm thật.

Tương quan là hai thứ cùng biến động; nhân quả là **can thiệp** vào thứ này thì thứ kia đổi. Theo
potential outcomes: tác động là $$Y(1) - Y(0)$$, và so sánh ngây thơ hai nhóm bằng tác động cộng
selection bias, tức chênh lệch giữa hai nhóm **nếu không ai được can thiệp**.

Ví dụ Olist: đơn giao trễ có review xấu 54.1%, đơn đúng hẹn 9.2%. Một phần chênh lệch có thể do
giao trễ, một phần do đơn trễ tập trung ở vùng xa, mùa cao điểm, seller kém. Một ví dụ khác hay gặp:
"user dùng tính năng X có retention cao gấp đôi". User chủ động dùng tính năng mới vốn là user gắn
bó hơn; ép mọi người dùng X chưa chắc tăng retention.

Ứng viên senior nói tiếp: cách mạnh nhất để biết là thí nghiệm; nếu không được thì cần một lập luận
về **nguồn biến thiên gần như ngẫu nhiên** (ngưỡng, thời điểm chính sách, instrument), hoặc giả định
không còn confounder chưa đo, kèm phân tích độ nhạy.

## Confounder, mediator, collider là gì? Điều chỉnh từng loại thì sao?

- **Confounder** (T ← Z → Y): nguyên nhân chung. Không điều chỉnh thì bias. Phải điều chỉnh.
- **Mediator** (T → M → Y): nằm trên đường tác động. Điều chỉnh thì mất phần tác động đi qua M, chỉ
  còn "tác động trực tiếp". Không điều chỉnh nếu muốn tác động tổng.
- **Collider** (T → C ← Y): hệ quả chung. Tự nó chặn đường; điều chỉnh (hoặc lọc dữ liệu theo nó)
  **mở** đường và tạo tương quan giả.

Ví dụ collider: chất lượng hàng và tốc độ giao độc lập, nhưng nếu chỉ phân tích seller được sàn
"đề xuất" (dựa trên tổng điểm), tương quan giữa hai thứ thành khoảng −0.68 trong mô phỏng của module.
Trong dữ liệu Olist, chỉ có đơn **có review**; nếu giao trễ ảnh hưởng tới việc khách có viết review
hay không, ta đang điều kiện trên collider mà không biết.

## Backdoor criterion là gì? Vì sao "cứ cho hết biến vào hồi quy" là sai?

Tập Z hợp lệ để điều chỉnh khi (1) không chứa hậu duệ của T và (2) chặn mọi đường từ T tới Y bắt
đầu bằng mũi tên đi vào T. Khi đó $$E[Y \mid do(T)]$$ tính được bằng điều chỉnh theo Z.

"Cho hết biến vào" sai vì ba lý do: biến sau can thiệp (mediator, collider) làm hỏng ước lượng; biến
chỉ ảnh hưởng tới T (instrument) làm tăng variance và có thể khuếch đại bias còn lại; M-bias: một
biến trước can thiệp nhưng là collider của hai nguyên nhân ẩn, điều chỉnh nó mở đường giả. Cách
chọn đúng là vẽ DAG cùng người hiểu nghiệp vụ, không phải chọn theo p-value hay feature importance.

## Propensity score là gì? Dùng thế nào và kiểm tra gì?

$$e(x) = P(T = 1 \mid X = x)$$. Dưới unconfoundedness và overlap, điều chỉnh cho e(x) là đủ. Dùng
bằng matching (ghép người có propensity gần nhau), IPW (trọng số nghịch đảo propensity),
stratification, hoặc doubly robust (AIPW, kết hợp mô hình outcome).

Kiểm tra bắt buộc: histogram propensity hai nhóm (overlap), SMD từng covariate trước và sau khi cân
(|SMD| < 0.1), effective sample size, trọng số lớn nhất. Mô hình propensity chọn để cân bằng
covariate, không phải để dự đoán giỏi: AUC 0.99 nghĩa là hai nhóm gần như không so sánh được.

Điều propensity **không** làm được: sửa confounder chưa đo, và tạo ra người so sánh được khi không
có. Nó chỉ dùng tốt hơn những gì đã có.

## Kể về thí nghiệm LaLonde. Bài học là gì?

Chương trình đào tạo nghề NSW chia ngẫu nhiên người tham gia; tác động lên thu nhập 1978 là
$1 794. LaLonde (1986) thay nhóm control ngẫu nhiên bằng người từ khảo sát dân số (PSID) và cho
thấy các phương pháp quan sát cho kết quả sai xa, kể cả sai dấu: so sánh ngây thơ cho −$15 205.

Dehejia & Wahba (1999) dùng propensity score và tìm lại được con số gần đúng; trong module, IPW với
8 covariate cho $1 759. Nhưng bài học đầy đủ khiêm tốn hơn: ESS của nhóm control chỉ khoảng 43 người
trên 2 490; đổi đặc tả hay trimming cho từ $582 tới $2 768; Smith & Todd (2005) chỉ ra kết quả phụ
thuộc mạnh vào mẫu và đặc tả. Có biến thu nhập trước chương trình (re74, re75) là điều kiện tiên
quyết. Phương pháp tốt không cứu được dữ liệu thiếu confounder quan trọng.

## Giải thích Difference-in-Differences. Giả định là gì, kiểm thế nào?

DiD lấy thay đổi trước–sau của nhóm treated trừ thay đổi của nhóm control. Hiệu thứ nhất khử khác
biệt cố định giữa nhóm; hiệu thứ hai khử xu hướng chung. Giả định: **parallel trends**, không can
thiệp thì hai nhóm thay đổi song song. Không kiểm trực tiếp được (không thấy phản thực tế), nhưng
nhìn được pre-trend: biểu đồ hai nhóm theo thời gian, event study với hệ số từng kỳ trước can thiệp.

Ví dụ Proposition 99: DiD California so với trung bình 38 bang là −27.35 bao/người/năm, nhưng
California đã giảm nhanh hơn 1.23 bao/năm trước 1989, nên DiD phóng đại. Senior nói thêm: pre-trend
"không có ý nghĩa thống kê" không chứng minh parallel trends (thiếu power, Roth 2022); với can
thiệp ở nhiều thời điểm khác nhau thì TWFE ngây thơ có thể sai (Goodman-Bacon), dùng
Callaway–Sant'Anna; và với một đơn vị treated thì cluster SE vô nghĩa.

## Synthetic control hoạt động thế nào? Khi nào dùng thay DiD?

Dựng một "bản sao" của đơn vị treated bằng tổ hợp lồi (trọng số không âm, tổng bằng 1) của các đơn
vị không bị can thiệp, chọn để bám sát đơn vị treated trước can thiệp. Sau can thiệp, khoảng cách
giữa thật và bản sao là tác động. Suy luận bằng placebo: coi từng donor là treated, xem đơn vị thật
có cực đoan không (theo tỉ số RMSPE sau/trước).

Dùng khi có một hoặc vài đơn vị treated, chuỗi trước dài, và nhóm so sánh "trung bình" không có
parallel trends. California: bản sao gồm Utah, Montana, Nevada, Connecticut…, gap năm 2000 là −26.6
bao, trung bình 1989–2000 là −19.5 (nhỏ hơn DiD); placebo xếp California thứ 3/39.

Giới hạn: đơn vị treated nằm ngoài bao lồi của donor (lớn nhất, cực đoan nhất) thì không khớp được;
pre-period ngắn thì khớp tốt do may; donor bị spillover; p-value hoán vị không thể nhỏ hơn 1/(J+1).

## Instrumental variable là gì? Cho ví dụ trong sản phẩm số.

Một biến Z ảnh hưởng tới treatment (relevance), chỉ ảnh hưởng tới outcome qua treatment (exclusion),
và không đẩy ai theo chiều ngược (monotonicity). Ước lượng bằng 2SLS; với Z nhị phân là Wald
estimator: reduced form chia first stage. Kết quả là **LATE**: tác động trên complier, người đổi
treatment vì Z.

Ví dụ sản phẩm: encouragement design, random việc gửi lời mời dùng tính năng (Z), không random việc
dùng (T). Hoặc thí nghiệm có non-compliance: ITT chia chênh lệch tỉ lệ thực sự nhận treatment. Ví dụ
kinh điển: Card dùng khoảng cách tới trường đại học, 2SLS cho lợi suất khoảng 13% mỗi năm học (0.1315 log điểm) so với 7.5%
của OLS.

Câu hỏi bẫy hay đi kèm: "instrument của bạn có thoả exclusion không?" Không kiểm được bằng dữ liệu;
phải lập luận, và kiểm tra gián tiếp bằng balance covariate theo Z.

## Instrument yếu là gì? Vì sao nguy hiểm?

First stage yếu: Z giải thích rất ít biến thiên của T. Hậu quả: 2SLS lệch về phía OLS (chính cái
bias ta muốn tránh), phân phối không còn chuẩn, CI thông thường có coverage sai. Kiểm bằng F của
first stage: quy tắc cũ là F > 10 (Staiger–Stock); Lee et al. (2022) chỉ ra muốn t-test 5% đúng size
cần F khoảng 104, hoặc dùng CI Anderson–Rubin (đúng bất kể độ mạnh). Card có F 13.26: qua ngưỡng
cũ nhưng nên báo AR.

Lỗi liên quan: tự chạy hai lần OLS rồi báo SE của lần hai. Hệ số đúng, SE sai, vì phần dư phải tính
bằng treatment thật, không phải giá trị dự đoán.

## Regression Discontinuity: giả định, cách ước lượng, cách kiểm tra?

Khi can thiệp quyết định bởi một ngưỡng trên biến liên tục, đơn vị ngay hai bên ngưỡng gần như giống
nhau; bước nhảy của E[Y | X] tại ngưỡng là tác động tại ngưỡng. Giả định: không ai kiểm soát chính
xác biến chạy quanh ngưỡng (mọi thứ khác liên tục tại ngưỡng).

Ước lượng: local linear mỗi bên, kernel tam giác, bandwidth tối ưu MSE (`rdrobust`) và CI robust
bias-corrected; tránh đa thức bậc cao toàn cục. Kiểm tra: mật độ biến chạy (McCrary, `rddensity`),
covariate trước can thiệp không nhảy, độ nhạy theo bandwidth, ngưỡng placebo. Giới hạn: tác động chỉ
cho đơn vị quanh ngưỡng. Fuzzy RDD (ngưỡng chỉ làm tăng xác suất được can thiệp) là IV với
instrument "vượt ngưỡng".

## Uplift modeling khác mô hình dự đoán thông thường thế nào? Đánh giá ra sao?

Mô hình dự đoán ước lượng $$P(Y = 1 \mid x)$$: khách nào sẽ mua. Uplift ước lượng
$$P(Y = 1 \mid x, T=1) - P(Y = 1 \mid x, T=0)$$: khách nào mua **thêm** vì được can thiệp. Nhắm theo
mô hình dự đoán là nhắm vào "sure thing", người vẫn mua dù không có voucher, tức là tốn tiền.

Cách làm: meta-learner (S, T, X, DR-learner), causal forest; cần dữ liệu thí nghiệm (hoặc
unconfoundedness). Đánh giá: không có nhãn uplift từng người, nên dùng Qini / uplift curve trên tập
test của thí nghiệm, so với xếp ngẫu nhiên và với luật đơn giản. Trên Hillstrom, T-learner logistic
đạt Qini 0.0044 so với 0.0038 của luật một cột "từng mua hàng nữ": phải thành thật rằng mô hình chỉ
hơn một chút. Lỗi hay gặp: chấm Qini trên train, chọn ngưỡng rồi báo lợi nhuận trên chính dữ liệu
dùng để chọn.

## Phân tích độ nhạy là gì? E-value nghĩa là gì?

Mọi kết luận quan sát dựa trên giả định không kiểm được; phân tích độ nhạy hỏi "giả định sai cỡ nào
thì kết luận đổi". E-value: độ mạnh tối thiểu (risk ratio) mà một confounder chưa đo phải có với cả
treatment lẫn outcome để kéo tác động về 0, $$E = RR + \sqrt{RR(RR - 1)}$$. Olist: RR 5.86 → E-value
11.2, rất vững. Một RR 1.3 cho E-value 1.92: một confounder vừa phải là đủ xoá tác động.

Các công cụ khác: omitted variable bias bounds (`sensemakr`) so với covariate mạnh nhất đã đo;
placebo outcome / treatment; chạy nhiều đặc tả và báo cả bảng. Senior luôn kèm phần này trong báo cáo.

## Case: PM nói "user dùng tính năng Wishlist có GMV cao gấp 3, hãy ép mọi user dùng Wishlist". Bạn trả lời thế nào?

1. **Gọi tên vấn đề**: self-selection. User dùng Wishlist là user mua sắm tích cực sẵn; GMV cao có
   thể là nguyên nhân chứ không phải kết quả của việc dùng Wishlist (reverse causality), và cả hai
   cùng do mức độ gắn bó (confounder).
2. **Ước lượng tốt hơn với dữ liệu có sẵn**: so sánh trước–sau khi user bắt đầu dùng (DiD theo
   thời điểm adopt, nhóm so sánh là user adopt muộn hơn), điều chỉnh GMV và tần suất truy cập
   **trước** khi dùng, kiểm overlap. Kỳ vọng con số "gấp 3" co lại rất nhiều.
3. **Cách trả lời dứt điểm**: thí nghiệm encouragement, random việc hiển thị lời nhắc dùng Wishlist.
   ITT trên GMV là thứ kinh doanh cần ("đẩy Wishlist thì GMV tăng bao nhiêu"); chia cho chênh lệch
   tỉ lệ dùng thì có tác động trên người dùng vì lời nhắc (IV).
4. **Đánh đổi**: chi phí ép dùng (UX xấu đi, user khó chịu) có thể lớn hơn tác động thật.

## Case: Olist muốn biết giảm giao trễ thì review xấu giảm bao nhiêu, để quyết định đầu tư logistics. Bạn làm gì?

1. **Estimand**: tác động của giao trễ lên xác suất review ≤ 2 sao, trên đơn đang bị trễ (ATT), vì
   đầu tư nhằm cứu chính những đơn đó.
2. **DAG**: confounder (bang khách, cùng bang với seller, mùa, giá, phí ship, số ngày hứa giao),
   mediator (liên hệ CSKH), selection (chỉ đơn có review).
3. **Ước lượng** (đơn từ 2017): ngây thơ 44.9 điểm %, hồi quy 44.4, IPW 45.0; overlap tốt, balance
   sau IPW |SMD| ≤ 0.02. Điều chỉnh gần như không đổi con số: điều đáng báo cáo.
4. **Liều**: review xấu tăng dần theo số ngày trễ (trễ 1 ngày 19.7%, 3 ngày 50.4%); không có bước
   nhảy ở đúng ngày hẹn. Khuyến nghị: ưu tiên cắt đơn trễ nặng, và cân nhắc dời ngày hẹn hợp lý hơn
   thay vì chỉ "đúng hẹn".
5. **Độ nhạy**: E-value 11.2; confounder đáng lo nhất còn lại là chất lượng seller, kiểm bằng fixed
   effect seller.
6. **Quy ra quyết định**: giảm 1 điểm % tỉ lệ trễ (khoảng 960 đơn trên 95 nghìn) giảm khoảng 430
   review xấu; cần thêm giá trị của một review xấu để so với chi phí logistics. Đề xuất thí nghiệm
   ưu tiên vận chuyển ngẫu nhiên cho một nhóm đơn để xác nhận.

## Case: Marketing chạy chiến dịch TV chỉ ở TP.HCM trong tháng 3 và báo doanh số TP.HCM tăng 20%. Bạn đánh giá thế nào?

1. "Tăng 20%" so với cái gì? Tháng 2 (có Tết?), tháng 3 năm trước? So trước–sau một mình lẫn mùa
   vụ và xu hướng chung.
2. **DiD** với các thành phố không có chiến dịch, kiểm pre-trend nhiều tháng trước. Nếu Hà Nội cũng
   tăng 15%, tác động chỉ khoảng 5 điểm.
3. **Synthetic control** vì chỉ có một thành phố treated: bản sao TP.HCM từ tổ hợp các tỉnh khác,
   khớp doanh số nhiều tháng trước; placebo trên các tỉnh khác để biết 5 điểm có nổi bật so với dao
   động bình thường không. CausalImpact là công cụ tương tự hay dùng ở doanh nghiệp.
4. **Rủi ro**: spillover (quảng cáo TV lan sang tỉnh lân cận làm nhóm so sánh cũng tăng, tác động bị
   ước lượng thấp), sự kiện khác cùng lúc (khuyến mãi của đối thủ), pre-period ngắn.
5. **Đề xuất lần sau**: geo experiment, random tỉnh nào chạy chiến dịch, đủ số tỉnh để có power.

## Khi có thể chạy A/B test, có lý do gì để vẫn dùng causal inference trên dữ liệu quan sát không?

Có, nhiều lý do:

- **Chọn thí nghiệm đáng chạy**: ước lượng quan sát rẻ, cho biết tác động cỡ nào để tính power và
  ưu tiên.
- **Tác động dài hạn**: thí nghiệm chạy vài tuần; tác động sau 1 năm phải ước lượng từ holdout hoặc
  surrogate index.
- **Non-compliance** và **CATE**: thí nghiệm cho ATE của việc *gán*; muốn tác động của việc *dùng*
  thì cần IV, muốn biết cho ai thì cần uplift (vẫn trên dữ liệu thí nghiệm).
- **Kiểm chứng phương pháp**: như LaLonde, so ước lượng quan sát với kết quả thí nghiệm để biết
  phương pháp quan sát của công ty đáng tin cỡ nào cho những lần không thể thí nghiệm.

Ngược lại, khi random được với chi phí hợp lý thì thí nghiệm gần như luôn thắng: nó xử lý cả
confounder không ai nghĩ tới.
