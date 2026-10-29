# Câu hỏi phỏng vấn: ML System Design & làm việc với business

## Bạn tiếp cận một câu hỏi ML system design mở như thế nào?

Đi theo khung và nói to từng bước, để người phỏng vấn theo được và chen vào đúng chỗ họ muốn đào:

1. **Đóng khung**: quyết định gì, ai hành động, hành động gì, lúc nào, ràng buộc gì (ngân sách, latency,
   pháp lý). Hỏi lại người phỏng vấn thay vì tự giả định.
2. **Metric**: business metric, online metric đo được trong vài tuần, offline metric để chọn model,
   guardrail. Giá trị tiền của từng loại lỗi.
3. **Dữ liệu và nhãn**: nhãn định nghĩa thế nào, có sau bao lâu, có bias chọn mẫu không.
4. **Feature**: theo thời điểm có mặt, batch hay real-time.
5. **Model**: baseline không ML, rồi model đơn giản, rồi phức tạp hơn nếu đáng.
6. **Serving**: batch / online / streaming, fallback.
7. **Monitoring**: data drift, phân phối điểm, metric khi nhãn về.
8. **Thí nghiệm**: holdout hoặc A/B để chứng minh giá trị.

Dành nhiều thời gian nhất cho bước 1–2. Ứng viên senior khác junior ở chỗ hỏi "model này phục vụ quyết
định gì" trước khi nói tên thuật toán, và chủ động nói "ở đây có lẽ không cần ML" khi đúng như vậy.

## Khi nào bạn khuyên **không** dùng ML?

- Luật đơn giản đã đủ tốt: trên Olist, luật "còn dưới 5 ngày tới ngày hẹn lúc giao vận chuyển" cho
  precision 42.7%, recall 35.2%, giá trị tiền ngang model LightGBM chọn top 10%.
- Số quyết định ít (vài chục mỗi tháng): người làm tốt hơn và rẻ hơn.
- Chưa có nhãn, hoặc nhãn không đáng tin.
- Quyết định cần giải thích từng ca theo luật (tín dụng ở một số thị trường): luật có kiểm toán.
- Giá trị kỳ vọng nhỏ hơn chi phí xây và bảo trì. Ví dụ hệ thống cảnh báo đơn trễ ở Olist, với giả định
  cơ sở, chỉ khoảng 100 R$ mỗi tuần.

Không dùng ML không có nghĩa là không làm gì: ra mắt luật, log quyết định, đo tác động. Khi có đủ dữ liệu
và luật chạm trần, model thay vào với baseline sẵn có để so.

## Làm sao chọn thời điểm dự đoán?

Thời điểm dự đoán đi theo **hành động**. Hành động phải xảy ra trước kết quả, nên mọi thông tin sau
thời điểm hành động là leak. Ở Olist:

- Model review xấu "lúc đơn vừa giao" (module 10/11) được dùng ngày giao thực tế làm feature, vì hành
  động (xin lỗi, voucher) xảy ra sau khi giao.
- Hệ thống cảnh báo đơn trễ muốn liên hệ khách **trước** khi đơn tới, nên chỉ dùng được thông tin lúc
  đặt hàng (PR-AUC test 0.120) hoặc lúc giao cho vận chuyển (0.378).

Đánh đổi: sớm hơn thì nhiều thời gian hành động hơn nhưng ít thông tin hơn. Ở đây đợi thêm khoảng 2 ngày
(trung vị thời gian seller xử lý) gấp ba PR-AUC mà vẫn còn trung vị 20.3 ngày tới ngày hẹn, nên chọn lúc
giao vận chuyển. Với chống gian lận thẻ, không có lựa chọn: phải quyết định trong vài trăm mili giây
trước khi duyệt.

## Offline metric tốt nhưng online không cải thiện. Bạn kiểm tra gì?

Theo thứ tự từ rẻ tới đắt:

1. **Hệ thống có chạy đúng không**: model đúng phiên bản, feature lúc serving có khớp lúc train
   (training-serving skew), điểm có phân phối giống offline không, cảnh báo có tới tay người hành động
   không.
2. **Offline metric có đo đúng thứ được dùng không**: đánh giá ROC-AUC trong khi dùng top k; đánh giá trên
   tập ngẫu nhiên trong khi dữ liệu thật trôi theo thời gian.
3. **Proxy có lệch mục tiêu không**: model đoán trễ, mục tiêu là review xấu; đơn trễ một ngày ít bực hơn
   đơn trễ mười ngày.
4. **Hành động có tác dụng không**: model đúng mà hành động vô hiệu thì giá trị bằng 0. Đây là lý do cần
   holdout trong nhóm được chọn, để tách "model chọn đúng" khỏi "hành động có tác dụng".
5. **Thí nghiệm đủ power chưa**: với 70 cảnh báo mỗi tuần và holdout 20%, cần khoảng 39 tuần để phát hiện
   tác động kỳ vọng ở Olist.

## Đổi precision / recall ra tiền thế nào?

Đặt giá trị cho từng ô của confusion matrix **so với không làm gì**. Với hành động tốn $$C$$, sự kiện
thiệt $$V$$, hành động giảm xác suất sự kiện $$\Delta$$ trên ca dương:

$$
\mathrm{EV} = TP\,(\Delta V - C) - FP\,C = k\,(\pi\,\Delta V - C)
$$

Có lãi khi precision $$\pi > C / (\Delta V)$$ (break-even precision). Hai điểm senior: (1) đừng coi FN
tốn trọn $$V$$ như thể hành động cứu được hết, vì giá trị bị phóng đại $$1/\Delta$$ lần; (2) nếu break-even
lớn hơn 1 thì không model nào cứu được, phải đổi hành động. Với V = 30 R$, Δ = 0.15: gọi điện 5 R$ cần
precision 111.1%, tin nhắn 0.5 R$ chỉ cần 11.1%.

## Ngân sách can thiệp cố định ảnh hưởng tới metric và chính sách thế nào?

Khi chỉ làm được k việc, metric đúng là precision@k / recall@k, không phải AUC trên toàn thứ hạng. Nhưng
k cố định có vấn đề khi số ca dương dao động: ở Olist, số đơn trễ mỗi tuần có trung vị 61, phân vị 90 là
289, tuần tệ nhất 565. Tuần yên ả, k cố định buộc phải chọn đơn điểm thấp (precision có thể dưới
break-even); tuần khủng hoảng, bỏ sót phần lớn.

Chính sách lai: ngưỡng điểm bảo đảm precision tối thiểu, trần k theo năng lực, và cảnh báo vận hành khi
chạm trần nhiều tuần liền. Trên tập test Olist, chỉ đặt trần 70 cảnh báo mỗi tuần cho precision 0.331;
ngưỡng 0.2 kèm trần 75 cho precision 0.453 với ít cảnh báo hơn.

## Feedback loop là gì? Cho ví dụ và cách phòng.

Khi đầu ra của model thay đổi dữ liệu model sẽ học. Ví dụ hệ thống cảnh báo: đơn rủi ro cao được nhắn
tin, nên ít review xấu hơn; retrain trên dữ liệu đó, model học rằng nhóm này "ít rủi ro", lần sau không
cảnh báo nữa, review xấu tăng lại. Các dạng khác: recsys chỉ gợi ý thứ đã phổ biến (degenerate loop),
cho vay chỉ thấy kết quả của khoản đã duyệt (selection), seller lách luật cảnh báo (hành vi chiến lược).

Cách phòng: holdout ngẫu nhiên trong nhóm được chọn; retrain trên đơn không bị can thiệp, đặt trọng số
`1 / holdout_share` cho đơn holdout; log điểm, quyết định và xác suất được chọn (propensity); một lượng
exploration nhỏ khi nhãn chỉ quan sát được cho lựa chọn đã làm.

## Nhãn về sau vài tuần. Bạn monitoring model thế nào?

Ba lớp. Lớp có ngay: schema, null, phân phối feature, phân phối điểm, số cảnh báo, proxy sớm (ở Olist là
số đơn đã quá hẹn mà chưa giao). Lớp nhãn: chỉ tính precision / recall trên cohort **đã chín**. Lớp kinh
doanh: so với holdout, chậm vài tuần.

Bẫy: tính metric trên các nhãn "đã có" của cohort gần đây. Nhãn trễ của Olist về khi qua ngày hẹn, nhãn
đúng hẹn về khi giao, nên nhãn âm về trước. Đơn mua tháng 02/2018 rốt cuộc trễ 16.0%, nhưng nhìn vào
2018-03-01 chỉ 47% đơn có nhãn và tỉ lệ trễ nhìn thấy là 1.4%: dashboard báo "ổn" đúng lúc khủng hoảng.

## Làm sao chứng minh hệ thống ML tạo ra giá trị?

So sánh "đơn được can thiệp" với "đơn không được can thiệp" luôn sai, vì model chọn đơn rủi ro cao. Cần
holdout: trong nhóm đủ điều kiện, giữ ngẫu nhiên một phần không can thiệp, so hai nhóm. Đây là A/B test
trên tổng thể được model chọn (module 03).

Phải tính power trước: ở Olist, nhóm được cảnh báo có review xấu nền khoảng 26.8%, tác động kỳ vọng 5.9
điểm phần trăm, cần 825 đơn mỗi nhóm. Chia 50/50 mất khoảng 24 tuần, holdout 20% mất khoảng 39 tuần. Nói
điều này **trước** khi ra mắt, cùng phương án: 50/50 giai đoạn đầu rồi giữ holdout nhỏ, đo proxy nhanh
hơn, hoặc chấp nhận chỉ chứng minh được "không có hại".

## Fairness: chọn định nghĩa nào?

Theo bản chất của quyết định. Can thiệp có lợi (hỗ trợ, ưu đãi) thì quan tâm người cần được giúp có cơ
hội như nhau: equal opportunity (recall theo nhóm). Can thiệp có hại (khoá tài khoản, từ chối khoản vay)
thì quan tâm ai bị hại nhầm: FPR theo nhóm. Khi tỉ lệ nền khác nhau, không thể cùng lúc calibrate theo
nhóm và cân bằng FPR/TPR (Kleinberg et al.; Chouldechova), nên phải chọn có chủ đích, cùng legal và
business.

Ví dụ Olist, top 5% đơn theo model lúc giao vận chuyển: recall São Paulo 43.6%, bang khác 17.9%, Bắc /
Đông Bắc 31.7% nhưng FPR 15.2% (gấp khoảng 8 lần hai vùng kia). Bỏ cột bang khỏi model không giải quyết
được, vì phí ship và số ngày hẹn mã hoá địa lý; giữ cột nhóm để đo, rồi chỉnh chính sách (ví dụ chia
ngân sách theo nhu cầu: recall bang khác lên 23.5%, Bắc / Đông Bắc xuống 20.8%, giá trị gần như không đổi).

## Batch, online hay streaming serving?

| Kiểu | Khi nào | Chi phí |
| --- | --- | --- |
| Batch | Quyết định không gấp, người hành động (CSKH, sales) | Rẻ, dễ debug, điểm cũ tới lần chạy sau |
| Online | Quyết định nằm trong luồng người dùng (gợi ý, duyệt giao dịch) | Latency, feature real-time, fallback |
| Streaming | Chậm vài phút là mất tiền (gian lận khi thanh toán) | Phức tạp nhất |

Chọn kiểu đơn giản nhất đáp ứng thời gian hành động. Cảnh báo đơn trễ cho CSKH là batch theo giờ; chọn
online "cho hiện đại" là lãng phí. Dù kiểu nào cũng cần fallback (luật nghiệp vụ) và log quyết định.

## Bạn trình bày kết quả cho một COO không làm ML thế nào?

BLUF: câu đầu là khuyến nghị và việc cần quyết. Sau đó vì sao (vấn đề bằng số thật), con số chính theo
kịch bản bi quan / cơ sở / lạc quan, rủi ro và điều chưa biết, ai cần quyết gì trước khi nào. Tối đa một
trang.

Đổi metric sang ngôn ngữ của họ: không nói "ROC-AUC 0.81" mà nói "trong 100 đơn được cảnh báo, khoảng 39
đơn thật sự trễ". Không nói "V = 30 R$" mà nói "hệ thống hoà vốn nếu một review xấu thiệt từ 8.5 R$ trở
lên; anh/chị thấy con số đó hợp lý không?". Tách rõ điều đã đo, điều ước lượng, điều giả định.

## Stakeholder muốn ra mắt ngay, bạn thấy chưa đủ bằng chứng. Bạn làm gì?

Không chặn và không chiều. Đặt rủi ro và chi phí của hai lựa chọn cạnh nhau: ra mắt ngay thì mất gì nếu
sai (tiền, khách, uy tín, khó rút lại), đợi thì mất gì (giá trị mỗi tuần chưa có). Đề xuất con đường ở
giữa có thể đảo ngược: ra mắt cho một phần traffic với holdout, guardrail cứng, tiêu chí dừng viết trước,
mốc xem lại. Ghi lại quyết định và lý do. Quyết định cuối cùng thuộc về người chịu trách nhiệm kinh
doanh; việc của DS là làm cho đánh đổi rõ ràng và có số.

## Case study: thiết kế hệ thống cảnh báo đơn có nguy cơ giao trễ cho một sàn thương mại điện tử.

**Đóng khung.** Lúc seller giao đơn cho vận chuyển, chấm điểm nguy cơ trễ; nhắn tin tự động xin lỗi và
báo ngày giao mới cho đơn điểm cao, tối đa theo năng lực; mục tiêu giảm review 1–2 sao. Baseline: luật
"còn dưới 5 ngày tới ngày hẹn".

**Metric.** Business: tỉ lệ review xấu. Online: review xấu ở nhóm cảnh báo so với holdout. Offline:
precision@k theo ngân sách, giá trị tiền ở ngưỡng chọn trên validation. Guardrail: tỉ lệ huỷ, tỉ lệ có
review (tin nhắn có thể khiến khách không review thay vì review tốt), chi phí CSKH.

**Dữ liệu.** Nhãn trễ so nguyên timestamp ngày giao và ngày hẹn; nhãn về muộn (95% trong khoảng 25 ngày).
Feature lúc giao vận chuyển: số ngày hẹn, số ngày seller xử lý, số ngày còn lại, phí ship, cùng bang,
lịch sử trễ của seller (as-of join). Không dùng ngày giao thực tế hay review.

**Model và serving.** Logistic rồi gradient boosting, so với luật trên giá trị tiền; batch theo giờ trên
sự kiện giao vận chuyển; fallback về luật; log điểm, quyết định, holdout, phiên bản.

**Monitoring và thí nghiệm.** Proxy có ngay (đơn quá hẹn chưa giao, phân phối điểm, số cảnh báo / trần),
metric chất lượng trên cohort đã chín; retrain trên đơn không can thiệp có trọng số; holdout và tính power
trước khi ra mắt; metric theo vùng.

**Kết luận trung thực.** Ở quy mô Olist 2018, giá trị khoảng 100 R$ mỗi tuần dưới giả định cơ sở: ra mắt
luật với holdout để đo V và Δ trước khi đầu tư model.

## Case study: PM nói "model churn của chúng ta có AUC 0.85, hãy gửi voucher cho top 10% khách". Bạn phản hồi gì?

Năm câu hỏi trước khi đồng ý:

1. **Voucher có tác dụng với ai?** Model churn dự đoán ai sẽ rời đi, không phải ai **đổi ý** nhờ voucher.
   Khách chắc chắn rời đi và khách chắc chắn ở lại đều không đáng gửi. Cần uplift model hoặc ít nhất thí
   nghiệm để biết tác động (module 06).
2. **Giá trị tiền**: chi phí voucher (kể cả khách đằng nào cũng ở lại dùng voucher) so với giá trị giữ chân
   một khách. Tính break-even precision theo cách ở trên với Δ là tác động của voucher.
3. **AUC 0.85 trên tập nào?** Chia ngẫu nhiên hay theo thời gian; có leak không (feature "đã gọi huỷ dịch
   vụ").
4. **Top 10% có phải ngân sách đúng không?** Precision@10% là bao nhiêu, không phải AUC.
5. **Đo thế nào?** Holdout trong top 10%.

Đề xuất: chạy thí nghiệm gửi voucher ngẫu nhiên trong vài decile điểm churn, đo tác động theo decile, rồi
chọn nhóm có uplift lớn nhất, không phải nhóm có điểm churn cao nhất.

## Case study: sau ba tháng, hệ thống cảnh báo đơn trễ báo tỉ lệ trễ giảm từ 8% xuống 3% trong tháng gần nhất. Team muốn ăn mừng. Bạn kiểm tra gì?

1. **Label delay**: tháng gần nhất chưa chín. Nhãn đúng hẹn về trước nhãn trễ, nên tỉ lệ trễ nhìn thấy của
   cohort chưa chín luôn thấp. Ở Olist, cohort 02/2018 trông như trễ 1.4% vào ngày 2018-03-01 nhưng thật ra
   16.0%. Tính lại trên cohort đã đủ 30 ngày.
2. **Hệ thống không làm giảm trễ**: tin nhắn không làm xe chạy nhanh hơn. Nếu tỉ lệ trễ thật giảm, nguyên
   nhân nằm ở vận hành, mùa vụ hay định nghĩa ngày hẹn (sàn có nới ngày hẹn dài hơn không?).
3. **Metric đúng của hệ thống** là review xấu ở nhóm được cảnh báo so với holdout, không phải tỉ lệ trễ.
4. **Định nghĩa và pipeline**: lọc đơn có đổi không (bỏ đơn huỷ, đơn chưa giao), join có mất dòng không.

Báo cáo lại với team bằng con số đúng, và đề xuất dashboard ghi rõ "số liệu tới cohort ngày X".
