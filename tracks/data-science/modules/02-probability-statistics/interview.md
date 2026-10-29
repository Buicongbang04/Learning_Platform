# Câu hỏi phỏng vấn: Xác suất & Thống kê suy luận

## Giải thích Central Limit Theorem cho một người không học thống kê. Vì sao Data Scientist cần nó?

"Từng đơn hàng có giá trị rất khác nhau: phần lớn nhỏ, thỉnh thoảng có đơn cực lớn. Nhưng nếu lấy
trung bình của nhiều đơn, rồi lặp lại việc đó nhiều lần, các con số trung bình sẽ xếp thành hình
chuông quanh giá trị thật, và càng lấy nhiều đơn thì chuông càng hẹp."

Vì sao cần: gần như mọi khoảng tin cậy và kiểm định cho trung bình (t-test trong A/B test, CI cho
doanh thu trung bình) dựa vào CLT để dùng phân phối chuẩn, dù dữ liệu gốc không chuẩn. Độ rộng của
chuông là standard error $$\sigma/\sqrt{n}$$.

Ứng viên senior nói thêm điều kiện: quan sát độc lập, variance hữu hạn, và **n đủ lớn so với độ lệch
của dữ liệu**. Với dữ liệu đuôi nặng (doanh thu theo khách), "đủ lớn" có thể là hàng nghìn. Với
variance vô hạn (một số phân phối Pareto), CLT không áp dụng.

## "Cứ n ≥ 30 là dùng được phân phối chuẩn." Bạn đồng ý không?

Không, quy tắc đó chỉ đúng cho dữ liệu gần đối xứng. Skewness của trung bình mẫu giảm theo
$$\mathrm{skew}(X)/\sqrt{n}$$. Giá trị đơn Olist có skewness 9.37; mô phỏng lấy mẫu từ 96 470 đơn giao
xong cho thấy khoảng t "95%" với n = 30 chỉ chứa trung bình thật khoảng 84–85% số lần, n = 500 khoảng
93%. Khoảng còn hụt về một phía: mẫu nhỏ hay thiếu đơn lớn nên đánh giá thấp trung bình.

Cách làm đúng: với metric của chính mình, mô phỏng độ phủ (lấy mẫu từ dữ liệu lịch sử, đếm số lần CI
chứa giá trị thật). Mười dòng code, và nó trả lời câu hỏi "n bao nhiêu là đủ" chính xác hơn mọi quy tắc
ngón tay cái. Với mẫu nhỏ: bootstrap, median, hoặc phân tích trên log.

## Bias và variance của một estimator là gì? Khi nào bạn chấp nhận một estimator có bias?

- **Bias**: trung bình của estimator qua nhiều mẫu lệch khỏi giá trị thật bao nhiêu.
- **Variance**: estimator dao động bao nhiêu giữa các mẫu.
- $$\mathrm{MSE} = \mathrm{bias}^2 + \mathrm{variance}$$.

Chấp nhận bias khi đổi lại giảm được nhiều variance, đặc biệt khi dữ liệu ít. Ví dụ: tỉ lệ review xấu
của một category chỉ có 2 đơn (1 xấu) là 50%, không lệch nhưng cực nhiễu. Ước lượng Bayesian kéo về
trung bình chung (12.8%) có bias nhưng MSE nhỏ hơn nhiều. Ridge/Lasso trong ML là cùng ý tưởng. Ví dụ
ngược lại: variance mẫu với `ddof=0` lệch xuống, sửa bằng `ddof=1` gần như không tốn gì, nên dùng
`ddof=1`.

## Maximum Likelihood Estimation là gì? Nó liên quan gì tới loss function trong machine learning?

MLE chọn tham số làm dữ liệu quan sát được có xác suất (likelihood) cao nhất. Thực tế ta cực đại
log-likelihood (tổng thay vì tích, tránh tràn số), hay tương đương cực tiểu negative log-likelihood.

Liên hệ với ML:

| Mô hình / loss | Là MLE với giả định |
| --- | --- |
| Linear regression với MSE | Nhiễu Normal, variance không đổi |
| Logistic regression với log loss (cross-entropy) | Nhãn Bernoulli |
| Poisson regression | Số đếm Poisson |
| Thêm L2 regularization | MAP với prior Normal trên hệ số |

Tính chất tốt của MLE: consistent, hiệu quả tiệm cận. Giới hạn: mẫu nhỏ có thể cho kết quả cực đoan
(0/7 → 0%), perfect separation trong logistic regression làm hệ số tiến ra vô cùng, và khi mô hình
sai thì MLE cho "tham số gần nhất trong họ đã chọn", không phải sự thật.

## Diễn giải một khoảng tin cậy 95%. Nó khác credible interval thế nào?

CI 95% là kết quả của một **thủ tục**: nếu lặp lại việc lấy mẫu và dựng khoảng theo cùng cách nhiều
lần, khoảng 95% các khoảng sẽ chứa tham số thật. Với một khoảng cụ thể đã tính, tham số hoặc nằm trong
hoặc không; nói "95% xác suất tham số nằm trong [a, b]" là sai theo nghĩa tần suất.

Credible interval Bayesian thì được nói đúng câu đó, **với điều kiện tin vào prior và mô hình**. Với dữ
liệu lớn và prior không quá mạnh, hai khoảng gần như trùng nhau.

Sai lầm thường gặp khác: "CI hai nhóm chồng nhau nên không khác nhau có ý nghĩa". Hai CI 95% có thể
chồng nhau một ít mà chênh lệch vẫn có ý nghĩa; muốn biết thì dựng CI cho chính chênh lệch (module 03).

## Category có 0 review xấu trên 7 đơn. Khoảng tin cậy cho tỉ lệ review xấu là bao nhiêu?

CI Wald cho [0, 0]: vô nghĩa, vì SE ước lượng từ $$\hat p = 0$$ bằng 0. Wald hỏng khi p nhỏ hoặc n nhỏ;
mô phỏng với p = 2%, n = 50, độ phủ thật chỉ khoảng 63%.

Dùng Wilson: [0, 0.354]. Ba đơn vị dữ liệu như vậy không nói được gì nhiều, và Wilson nói thật điều đó.
Nếu cần một con số để xếp hạng: dùng cận dưới của Wilson (cách Reddit xếp bình luận), hoặc posterior
mean Beta-Binomial với prior lấy từ mọi category (khoảng 12% trên Olist). Nếu cần đảm bảo độ phủ ít nhất
95% (bối cảnh pháp lý, y tế): Clopper-Pearson.

## Bootstrap hoạt động thế nào? Khi nào bạn không tin bootstrap?

Coi mẫu là tổng thể thu nhỏ: lấy lại n quan sát có hoàn lại, tính thống kê, lặp vài nghìn lần; phân
phối các thống kê đó xấp xỉ phân phối lấy mẫu. CI percentile là percentile 2.5 và 97.5. Ưu điểm: dùng
cho mọi thống kê (median, percentile 90, tỉ số) không cần công thức.

Không tin khi:

- Thống kê phụ thuộc cực trị (max, p99 với mẫu nhỏ): mẫu bootstrap không vượt được max của mẫu gốc,
  CI cho max có độ phủ gần 0.
- Quan sát không độc lập (nhiều đơn của cùng khách, chuỗi thời gian): phải resample theo cụm / block.
- Mẫu rất nhỏ: mẫu không đại diện được tổng thể.
- Mẫu lệch: bootstrap đo nhiễu, không đo bias.

Với median còn có CI chính xác từ thống kê thứ tự (dựa trên Binomial(n, 0.5)), không cần mô phỏng.

## Số đơn mỗi giờ có theo Poisson không? Kiểm tra thế nào, và nếu không thì sao?

Poisson buộc variance bằng mean. Kiểm tra nhanh: dispersion index = variance / mean. Trên Olist (đơn
giao xong, theo giờ, tháng 3/2018): mean 9.41, variance 51.08, dispersion khoảng 5.4. Poisson với một
λ chung dự đoán 0.18% số giờ có từ 20 đơn trở lên; thực tế 7.4%.

Nguyên nhân: λ thay đổi theo giờ trong ngày, ngày trong tuần, khuyến mãi; hỗn hợp nhiều Poisson luôn có
variance lớn hơn mean. Xử lý: Poisson regression với λ phụ thuộc giờ / ngày, hoặc Negative Binomial
(thêm tham số dispersion). Hậu quả nếu bỏ qua: hệ thống cảnh báo bất thường dựa trên Poisson sẽ báo
động liên tục, và mọi CI dựa trên variance Poisson đều quá hẹp.

## Doanh thu theo khách có đuôi rất nặng. Bạn báo cáo và phân tích nó thế nào?

Trên Olist, 1% đơn lớn nhất chiếm 10.4% doanh thu; mean giá trị đơn 159.83 BRL, median 105.28. Một vài
khách lớn có thể đổi trung bình của cả tuần.

- **Báo cáo** cả median (khách điển hình) và mean (gắn với tổng doanh thu), thêm percentile 90/99.
- **Phân tích trung bình** khi cần (tổng doanh thu là thứ kinh doanh quan tâm): đủ mẫu để CLT hoạt
  động (kiểm tra bằng mô phỏng), so với bootstrap, winsorize ở p99.9 và ghi rõ đã làm.
- **Tách metric**: doanh thu mỗi khách = tỉ lệ mua × giá trị khi mua; mỗi thành phần ít đuôi hơn.
- **Không** dùng Mann-Whitney rồi báo cáo như thể kiểm định trung bình (module 03).
- **Mô hình hoá đuôi** khi cần dự báo khách lớn: log-transform, mô hình riêng cho phần đuôi.

## Một xét nghiệm / mô hình có độ chính xác cao, nhưng phần lớn cảnh báo lại sai. Vì sao?

Base rate. Khi sự kiện hiếm, kể cả tỉ lệ dương tính giả nhỏ áp lên số đông âm tính cũng tạo ra nhiều
cảnh báo sai hơn số cảnh báo đúng. Định lý Bayes:

$$
P(A \mid B) = \frac{P(B \mid A)\,P(A)}{P(B)}
$$

Ví dụ thật trên Olist (đơn giao xong có review): P(xấu | trễ) = 54.1%, nhưng P(trễ | xấu) chỉ khoảng
34%, vì chỉ 8.0% đơn bị trễ. Kết luận cho đội CSKH: giảm giao trễ giải quyết được khoảng một phần ba
review xấu, không phải phần lớn. Nhầm $$P(A \mid B)$$ với $$P(B \mid A)$$ là lỗi rất phổ biến khi đọc
metric, và cũng là lý do precision của mô hình fraud thấp dù recall cao.

## Frequentist và Bayesian khác nhau thế nào? Bạn dùng Bayesian khi nào?

Frequentist coi tham số cố định, chưa biết; xác suất là tần suất khi lặp lại. Bayesian coi tham số là
biến ngẫu nhiên, kết hợp prior với likelihood thành posterior.

Dùng Bayesian khi:

- Nhiều nhóm nhỏ có liên quan (category, seller, cửa hàng): partial pooling / shrinkage cho ước lượng
  tốt hơn hẳn từng nhóm riêng.
- Cần câu trả lời dạng xác suất cho quyết định: "P(category A tệ hơn B) = 0.9".
- Có kiến thức trước đáng tin (thí nghiệm cũ, dữ liệu ngành) và dữ liệu mới ít.

Giữ frequentist khi quy trình chuẩn của ngành là frequentist (nhiều experimentation platform, y tế),
dữ liệu lớn (hai cách cho cùng kết quả), hoặc người đọc không chấp nhận prior. Rủi ro của Bayesian:
prior chọn sau khi thấy dữ liệu, hoặc không báo cáo prior đã dùng.

## Kể các loại sampling bias bạn từng gặp trong dữ liệu sản phẩm.

- **Self-selection / non-response**: trên Olist, 40.6% review có bình luận; tỉ lệ review xấu trong
  nhóm có bình luận là 23.7%, không bình luận 5.3%. Phân tích cảm xúc chỉ từ bình luận sẽ thấy khách
  tệ gấp đôi thực tế.
- **Survivorship**: thời gian giao chỉ có ở đơn đã giao; đơn bị huỷ vì chờ lâu biến mất khỏi dữ liệu.
  Tương tự: phân tích khách "trung thành" chỉ trên khách còn hoạt động.
- **Coverage theo thời gian**: Olist tháng 10/2016 có 324 đơn, tháng 11/2017 có 7 544. Trung bình
  cả giai đoạn không đại diện hiện tại.
- **Selection do chính sản phẩm**: mô hình gợi ý chỉ thấy phản hồi cho món đã được gợi ý (feedback loop).

Senior nói thêm: bias **không giảm theo n**; sửa được bằng trọng số khi selection phụ thuộc biến quan
sát được (post-stratification, IPW), không sửa được hoàn toàn khi phụ thuộc chính đại lượng cần đo; khi
đó phải sửa ở khâu thu thập.

## Vì sao công thức SE = σ/√n có thể cho standard error quá nhỏ?

Công thức giả định n quan sát **độc lập**. Dữ liệu sản phẩm thường có cụm: nhiều đơn của cùng khách,
nhiều đơn của cùng seller, nhiều sự kiện trong cùng session, các ngày liền nhau trong chuỗi thời gian.
Quan sát trong cụm tương quan dương, nên "số thông tin độc lập" ít hơn n, và SE thật lớn hơn công thức.
Hệ quả: CI quá hẹp, kiểm định báo "có ý nghĩa" nhầm.

Xử lý: phân tích ở đúng đơn vị độc lập (gộp theo khách), cluster-robust SE, bootstrap theo cụm, hoặc
mô hình phân cấp. Đây cũng là lý do trong A/B test, đơn vị phân tích phải khớp đơn vị random (module 03).

## Case: Xếp hạng category (hoặc seller) theo tỉ lệ review xấu để đội vận hành ưu tiên xử lý. Bạn làm thế nào?

Vấn đề của tỉ lệ thô: trên Olist, category đứng đầu theo tỉ lệ thô là `security_and_services` với 1
review xấu trên 2 đơn (50%). Category nhỏ luôn chiếm các vị trí đầu và cuối bảng chỉ vì nhiễu.

Cách làm:

1. Đếm đúng: dùng định nghĩa chung (đơn giao xong, review mới nhất, xấu là ≤ 2 sao), gán category theo
   quy tắc rõ ràng.
2. Beta-Binomial với prior ước lượng từ mọi category (empirical Bayes). Trên Olist: prior mean 12.75%,
   nặng như khoảng 240 đơn.
3. Xếp theo posterior mean, hoặc theo xác suất vượt ngưỡng "P(tỉ lệ > 15%)" nếu đội vận hành có ngưỡng.
4. Kèm credible interval và số đơn để người đọc thấy độ chắc chắn.

Kết quả: `office_furniture` (270/1 236, posterior 20.4%) đứng đầu; `security_and_services` co về 13.1%;
`fashion_male_clothing` (22.9% thô) chỉ còn 15.8%, gần như ngang `bed_bath_table`. Đội vận hành nên bắt
đầu với nội thất văn phòng.

Câu hỏi tiếp theo nên hỏi lại: tỉ lệ review xấu có phải metric đúng không (hay review xấu đến từ giao
trễ, tức vấn đề logistics chứ không phải category)? Xếp hạng có cần điều chỉnh theo bang, theo trễ không?

## Case: PM báo "giá trị đơn trung bình tuần này tăng 8% so với tuần trước, chiến dịch mới hiệu quả". Bạn phản hồi thế nào?

Trước hết: 8% có lớn hơn dao động bình thường không? Trên Olist giai đoạn 2017-06 tới 2018-07, độ lệch
chuẩn của thay đổi tuần-so-với-tuần của giá trị đơn trung bình là khoảng 9.5%, và 27% số tuần thay đổi
ít nhất 8% (lên hoặc xuống) mà không cần chiến dịch nào. Với độ lệch chuẩn giá trị đơn khoảng 219 BRL và
hơn một nghìn đơn mỗi tuần, standard error của chênh lệch hai tuần đã cỡ 5% trung bình.

Các bước:

1. Nhìn median và phân phối: tăng đều hay do vài đơn rất lớn? Median của Olist dao động ít hơn
   (khoảng 6.4% tuần-so-với-tuần).
2. Đặt vào chuỗi dài: có phải mùa vụ, ngày lễ, mix category thay đổi?
3. So sánh trước–sau không phải nhân quả: chiến dịch trùng thời điểm với mọi thứ khác. Nếu muốn biết
   tác động, cần nhóm đối chứng (A/B test, module 03) hoặc phương pháp quasi-experiment (module 06).

Câu trả lời cho PM: "Mức tăng này nằm trong dao động thường thấy; chưa đủ để kết luận. Đề xuất chạy
chiến dịch có nhóm đối chứng ở lần sau, hoặc mình xem kỹ phần đóng góp của các đơn lớn."

## Case: Khảo sát qua điện thoại cho thấy 30% khách không hài lòng. Trưởng CSKH muốn tăng gấp đôi ngân sách. Bạn kiểm tra gì?

Câu hỏi đầu tiên: **ai** trả lời khảo sát? Nếu khách có đơn trễ nghe máy nhiều hơn (đang chờ hàng, muốn
phàn nàn), mẫu bị lệch về phía không hài lòng.

Mô phỏng trên Olist thật: tổng thể có 12.8% review xấu, 8.0% đơn trễ. Nếu khảo sát chọn đơn trễ với xác
suất 0.5 và đơn đúng hẹn với 0.05, mẫu có 46.7% đơn trễ và tỉ lệ không hài lòng thô 30.0%, gấp hơn hai
lần sự thật. Post-stratification theo trạng thái trễ (tính tỉ lệ trong từng tầng, gộp theo tỉ trọng
tổng thể) cho 12.9%, CI 95% [12.1%, 13.7%].

Các bước trong thực tế: so tỉ trọng các nhóm (trễ, vùng, category, giá trị đơn) giữa mẫu và tổng thể;
hiệu chỉnh trọng số theo các biến lệch; nói rõ giới hạn (nếu người không hài lòng nghe máy nhiều hơn ngay
cả khi cùng nhóm thì hiệu chỉnh không sửa hết); và đề xuất thiết kế khảo sát lần sau (stratified
sampling, gọi lại người không nghe máy). Ngân sách nên quyết định trên con số đã hiệu chỉnh và trên dữ
liệu hành vi (review, mua lại), không chỉ trên khảo sát.

## Case: Olist nên hẹn khách ngày giao hàng thế nào? Bạn tiếp cận bằng thống kê ra sao?

Hiện trạng trên Olist thật: median thời gian giao 10.22 ngày, p95 29.27 ngày; median ngày hẹn 23.23 ngày
sau khi mua, vậy mà vẫn 8.1% đơn trễ, và đơn trễ có 54.1% review xấu. Ngày hẹn vừa quá dài cho phần lớn
đơn vừa quá ngắn cho một nhóm.

Tiếp cận:

1. Coi ngày hẹn là một **percentile** của phân phối thời gian giao có điều kiện theo tuyến (bang, khoảng
   cách, seller). Hẹn ở p95 của tuyến nghĩa là chấp nhận khoảng 5% trễ.
2. Ước lượng percentile: thực nghiệm khi nhóm nhiều đơn (kèm bootstrap CI); mô hình hoặc gộp nhóm khi ít
   đơn. Kiểm tra mô hình ở **đuôi**: Lognormal có AIC tốt nhất trên thời gian giao Olist nhưng q95 của nó
   (30.7) lệch khỏi q95 thực nghiệm (29.3).
3. Kiểm tra ngoài thời gian: ước lượng trên 2017, đánh giá trên 2018.
4. Chọn percentile là quyết định kinh doanh: hẹn ngắn tăng conversion, hẹn dài giảm trễ. Đo tác động lên
   conversion bằng thí nghiệm.

Hẹn theo p95 của từng bang (trong mẫu) giữ median ngày hẹn gần như cũ (24.7 ngày) mà tỉ lệ trễ giảm còn
khoảng 5%. Đây là bài Advanced 01.
