# Câu hỏi phỏng vấn: Hypothesis Testing & A/B Testing

## Giải thích p-value cho một Product Manager không học thống kê.

"Giả sử thay đổi của anh/chị hoàn toàn không có tác dụng. Khi đó, vì chia user ngẫu nhiên, hai
nhóm vẫn luôn chênh nhau một chút. p-value là khả năng ta thấy một chênh lệch lớn cỡ này (hoặc
hơn) chỉ do may rủi như thế. p = 0.01 nghĩa là nếu thay đổi vô dụng thì chỉ khoảng 1 trên 100 thí
nghiệm cho ra chênh lệch lớn như vậy, nên ta khá tin là có tác động thật."

Những điều p-value **không** phải, và ứng viên senior nên chủ động nói:

- Không phải xác suất thay đổi có hiệu quả, hay xác suất H0 đúng.
- Không nói tác động lớn hay nhỏ: với mẫu khổng lồ, tác động không đáng kể vẫn có p rất nhỏ.
- p = 0.06 không có nghĩa "không có tác động"; có thể chỉ là thiếu mẫu.

Sau đó chuyển PM sang confidence interval: "tác động nằm khoảng +0.3% đến +1.1%" hữu ích cho quyết
định hơn một con số p.

## Power là gì? MDE là gì? Bạn chọn MDE thế nào?

Power là xác suất thí nghiệm phát hiện được tác động, nếu tác động thật có độ lớn bằng MDE.
MDE (Minimum Detectable Effect) là tác động nhỏ nhất mà thí nghiệm được thiết kế để phát hiện với
power đó (thường 80%) ở mức α đã chọn (thường 5%).

Chọn MDE là quyết định kinh doanh: tác động nhỏ nhất đáng để ship sau khi trừ chi phí xây, bảo trì
và rủi ro của tính năng. Rồi đối chiếu với thực tế: cỡ mẫu tỉ lệ nghịch với MDE², nên MDE quá nhỏ
có thể đòi hàng tháng traffic. Khi đó thương lượng: chấp nhận MDE lớn hơn, giảm variance (CUPED),
chọn metric nhạy hơn, hoặc nhắm vào tổng thể có tác động lớn hơn.

Bẫy cần tránh: chọn MDE bằng "tác động mà team kỳ vọng" (thường lạc quan), hoặc tính ngược MDE từ
traffic có sẵn rồi coi đó là mục tiêu.

## Cần bao nhiêu user để phát hiện conversion tăng từ 10% lên 11%?

Công thức xấp xỉ normal, two-sided, α = 0.05, power = 0.8:

```
n = (1.96 + 0.84)² · [0.10·0.90 + 0.11·0.89] / 0.01² ≈ 14 732 user mỗi nhóm
(14 749 nếu dùng z chính xác 1.95996 + 0.84162)
```

Nói thêm để thể hiện kinh nghiệm: tổng ~29.5 nghìn user; chia cho traffic mỗi ngày đủ điều kiện
vào thí nghiệm rồi làm tròn lên số tuần trọn; nếu metric cần thời gian "chín" (retention 7 ngày)
thì cộng thêm. Nếu muốn phát hiện 10% → 10.5% thì cần gấp khoảng 4 lần.

## Khi nào dùng z-test, t-test, chi-square, Mann-Whitney, bootstrap?

- **z-test hai tỉ lệ / chi-square 2×2**: metric 0/1 (conversion, retention). Hai cách tương đương
  với bảng 2×2 (z² = χ²).
- **Welch t-test**: trung bình của metric liên tục (doanh thu, thời gian). Với mẫu lớn, CLT xử lý
  phân phối lệch. Mặc định Welch thay vì Student vì không cần giả định variance bằng nhau.
- **Chi-square goodness-of-fit**: so số lượng quan sát với tỉ lệ kỳ vọng, chính là kiểm tra SRM.
- **Mann-Whitney U**: hỏi về thứ hạng/phân phối, **không** phải về trung bình. Không dùng để báo
  cáo "doanh thu trung bình tăng X%".
- **Bootstrap**: thống kê không có công thức SE tốt (median, percentile, metric phức tạp), hoặc
  để kiểm tra lại kết quả t-test khi dữ liệu có đuôi nặng.
- **Delta method**: metric là tỉ số của hai tổng khi đơn vị random khác đơn vị phân tích (CTR theo
  pageview, random theo user).

## SRM là gì? Bạn phát hiện SRM, giờ làm gì?

Sample Ratio Mismatch: tỉ lệ số đơn vị giữa các nhánh lệch khỏi thiết kế nhiều hơn mức ngẫu nhiên
cho phép (kiểm bằng chi-square, ngưỡng thường p < 0.001). Ví dụ thiết kế 50/50 nhưng có 50.8/49.2
trên 200 nghìn user.

SRM cho biết hai nhóm không còn so sánh được, nên **không** đọc kết quả. Các bước:

1. Kiểm tra pipeline: log sự kiện phân nhóm, join, filter (bot filter có áp khác nhau không).
2. Chia theo chiều: ngày, platform, trình duyệt, quốc gia, phiên bản app, user mới/cũ, để tìm lát
   cắt lệch. Lệch từ một ngày cụ thể → sự cố triển khai; lệch ở một trình duyệt → lỗi redirect hoặc
   crash.
3. Sửa nguyên nhân, chạy lại thí nghiệm. Không "cân lại" bằng cách bỏ bớt user ở nhánh đông hơn.

Chi tiết senior: SRM có thể do chính treatment gây ra (treatment làm app crash nên user không được
log), và khi đó SRM là một phát hiện về treatment.

## Vì sao không được nhìn kết quả mỗi ngày rồi dừng khi p < 0.05?

Dưới H0, p-value đi ngẫu nhiên lên xuống theo thời gian. Mỗi lần nhìn là một cơ hội để nó tình cờ
xuống dưới 0.05. Nhìn 10 lần và dừng ở lần đầu thấy p < 0.05 cho tỉ lệ false positive thực tế
khoảng 15–20%, không còn 5%.

Giải pháp: cố định cỡ mẫu và chỉ đọc khi đủ; hoặc group sequential design (định trước số lần nhìn,
biên O'Brien-Fleming chặt ở đầu, lỏng dần về cuối); hoặc phương pháp always-valid (mSPRT,
confidence sequence) cho phép nhìn bất cứ lúc nào. Vẫn được theo dõi guardrail an toàn hằng ngày
để dừng khi thấy hại rõ ràng; đó là quyết định về an toàn, không phải để tuyên bố thắng.

## Thí nghiệm có 20 metric, 1 metric có p = 0.03. Bạn báo cáo thế nào?

Với 20 metric ở α = 0.05, kỳ vọng khoảng 1 metric "có ý nghĩa" do may ngay cả khi không có tác
động gì. Nên:

- Nếu đó không phải OEC định trước: báo cáo như một quan sát cần kiểm chứng, không phải kết luận.
- Áp hiệu chỉnh: Holm nếu cần kiểm soát FWER (quyết định ship), Benjamini-Hochberg nếu đang sàng
  lọc để tìm hướng điều tra (kiểm soát FDR). Với 20 metric, p = 0.03 gần như chắc không qua được.
- Xem có cơ chế hợp lý không và có nhất quán với các metric liên quan không.
- Nếu đáng theo đuổi: thiết kế thí nghiệm tiếp theo với metric đó làm OEC.

Phòng từ gốc: một OEC, vài guardrail, viết ra trước.

## Chọn đơn vị random như thế nào? Khi nào random theo user là sai?

Random theo đơn vị nhỏ nhất mà treatment **không lan sang nhau** và trải nghiệm phải nhất quán.
Mặc định là user. Random theo user là sai khi:

- **Network effect / marketplace**: user ở treatment ảnh hưởng tới control. Ví dụ giảm giá cho
  khách treatment trên Grab làm họ đặt nhiều xe, tài xế bị kéo về phía họ, khách control phải chờ
  lâu hơn. Ước lượng sẽ bị thổi phồng. Dùng random theo vùng/thời gian (switchback) hoặc cluster.
- **Thay đổi phía cung**: thay đổi cho seller ảnh hưởng mọi người mua.
- **Thay đổi giá công khai**: user so sánh giá với nhau, gây phản ứng tiêu cực và rủi ro pháp lý.

Và nhớ: phân tích theo đơn vị random. Random theo user mà tính metric theo session thì phải dùng
delta method hoặc cluster-robust SE.

## OEC tăng có ý nghĩa nhưng một guardrail giảm có ý nghĩa. Ship không?

Không có câu trả lời mặc định; đây là câu hỏi để thấy cách bạn suy nghĩ. Trả lời theo khung:

1. **Kiểm tra độ tin cậy** trước: SRM, thời lượng, novelty effect, cả hai tác động có ổn định
   theo thời gian không.
2. **Hiểu cơ chế**: vì sao guardrail giảm? Có phải do cùng một hành vi (khách xem nhiều sản phẩm
   hơn nên tỉ lệ thêm vào giỏ trên mỗi lượt xem giảm, nhưng tổng đơn tăng)?
3. **Lượng hoá về cùng đơn vị**: quy cả hai về doanh thu hoặc giá trị dài hạn, kèm CI.
4. **Tìm phương án thứ ba**: sửa thiết kế để giữ lợi ích mà bỏ tác hại, thử lại.
5. **Đưa quyết định lên đúng người** với đánh đổi được trình bày rõ; guardrail "cứng" (an toàn,
   pháp lý, khiếu nại nghiêm trọng) thì không đánh đổi.

## Thí nghiệm không có ý nghĩa thống kê. PM nói "vậy là tính năng không có tác dụng". Bạn nói gì?

"Không có ý nghĩa thống kê" khác "chứng minh không có tác dụng". Nhìn CI:

- CI hẹp quanh 0 (ví dụ [−0.2%, +0.3%] trong khi tác động đáng giá là 2%): đủ bằng chứng là
  không có tác động đáng kể. Có thể kết luận gần như vậy.
- CI rộng (ví dụ [−3%, +5%]): thí nghiệm thiếu power, chưa nói được gì. Kết luận đúng là "chưa
  biết".

Nếu mục tiêu là chứng minh "không tệ hơn" (ví dụ đổi sang hạ tầng rẻ hơn), phải thiết kế
non-inferiority test từ đầu, với biên chấp nhận được và cỡ mẫu tính cho biên đó.

## Novelty effect là gì? Làm sao phát hiện?

User phản ứng mạnh với cái mới (bấm thử nút mới) rồi trở lại bình thường; tác động tuần đầu
không đại diện cho dài hạn. Ngược lại, primacy effect: user quen cái cũ nên ban đầu phản ứng tệ
rồi mới thích nghi.

Phát hiện: vẽ tác động theo ngày, hoặc tốt hơn theo "số ngày kể từ lần đầu user thấy treatment".
Xu hướng giảm dần là novelty. So user mới (chưa từng thấy bản cũ) với user cũ: user mới không có
novelty. Xử lý: chạy lâu hơn, đọc tác động ở giai đoạn ổn định, hoặc giữ một holdout dài hạn sau
khi ship.

## Bạn sẽ phân phối traffic 50/50 hay 90/10? Vì sao?

Với cùng tổng traffic, 50/50 cho variance của ước lượng chênh lệch nhỏ nhất, nên power cao nhất.
90/10 cần nhiều tổng traffic hơn để đạt cùng power (khoảng 2.8 lần), nhưng hợp lý khi:

- Treatment rủi ro (giới hạn thiệt hại khi có hại).
- Nhiều thí nghiệm dùng chung một nhóm control.
- Giai đoạn ramp-up kiểm tra kỹ thuật.

Không thay đổi tỉ lệ giữa chừng rồi gộp dữ liệu: user vào ở các giai đoạn khác nhau có thể khác
nhau (ngày trong tuần, chiến dịch marketing), gây Simpson's paradox. Phân tích riêng giai đoạn ổn
định.

## Case: Cookie Cats dời gate từ level 30 sang 40. Retention 7 ngày giảm từ 19.0% xuống 18.2% (p = 0.0016). Bạn khuyến nghị gì?

Trình bày theo thứ tự:

1. **Độ tin cậy**: kiểm SRM trước. 44 700 vs 45 489 cho p ≈ 0.0086: không vượt ngưỡng 0.001 nhưng
   vượt 0.01. Hỏi team ngưỡng đã chọn trước là gì; nếu 0.01, cần điều tra nguồn chênh lệch trước
   khi tin kết quả.
2. **Kết quả**: retention_7 giảm 0.82 điểm phần trăm, CI 95% khoảng [−1.33, −0.31]. retention_1
   giảm 0.59 điểm nhưng CI chứa 0.
3. **Cơ chế**: gate buộc người chơi dừng lại; nghỉ giữa chừng có thể giữ hứng thú lâu hơn. Gate xa
   hơn thì nhiều người chơi tới chán trước khi gặp gate.
4. **Khuyến nghị**: giữ gate ở level 30. Ghi chú các điều chưa đo: doanh thu in-app (gate là
   điểm bán hàng), retention dài hơn 7 ngày. Nếu cần, thử thêm level 20–25.

## Case: Thiết kế thí nghiệm để kiểm tra việc nhắn tin chủ động cho khách có đơn sắp giao trễ (Olist) có làm giảm review xấu không.

- **Giả thuyết**: thông báo sớm và xin lỗi làm giảm cảm giác bị bỏ rơi, nên giảm review 1–2 sao.
  Dữ liệu thật ủng hộ việc đáng làm: đơn trễ có 54% review xấu, đơn đúng hẹn 9%.
- **Đơn vị random**: đơn hàng được model dự đoán có nguy cơ trễ (hoặc khách hàng, nếu muốn trải
  nghiệm nhất quán khi khách có nhiều đơn). Random tại thời điểm dự đoán.
- **OEC**: tỉ lệ review ≤ 2 sao trên đơn đã giao. **Guardrail**: tỉ lệ huỷ đơn, tỉ lệ có review
  (tin nhắn có thể làm thay đổi ai để lại review → selection bias trên chính OEC), chi phí CSKH.
- **Power**: baseline review xấu trên tổng thể nguy cơ cao lớn hơn nhiều so với 12.8% chung, nên
  MDE đạt được nhỏ hơn. Tính cỡ mẫu từ baseline của chính tổng thể này, chia cho số đơn nguy cơ
  mỗi tuần để ra thời lượng; thêm thời gian chờ review.
- **Rủi ro**: model dự đoán thay đổi trong lúc chạy; nhắn tin cho đơn cuối cùng giao đúng hẹn có
  thể gây hại; spillover nếu khách có đơn ở cả hai nhóm.
- **Quyết định**: viết trước ngưỡng ship, kế hoạch phân tích, segment sẽ xem (vùng, category).

## Case: Thí nghiệm làm tăng conversion 2% nhưng doanh thu mỗi user giảm. Chuyện gì có thể xảy ra?

Các giả thuyết cần kiểm tra:

- **Mix shift**: treatment kéo thêm người mua đơn nhỏ (giảm giá, nút mua nhanh), nên tỉ lệ mua
  tăng nhưng giá trị giỏ trung bình giảm. Xem phân phối giá trị đơn, không chỉ trung bình.
- **Cannibalization**: khách chuyển từ sản phẩm đắt sang sản phẩm rẻ hơn.
- **Đuôi nặng**: doanh thu có vài khách cực lớn; vài "cá voi" rơi vào control là đủ làm trung bình
  lệch. Kiểm bằng winsorize hoặc bootstrap; xem CI của doanh thu có rộng không.
- **Mẫu số khác nhau**: "doanh thu mỗi user" vs "doanh thu mỗi người mua" là hai metric khác hẳn.

Khuyến nghị dựa trên metric gắn với giá trị dài hạn: tổng doanh thu (hoặc lợi nhuận) mỗi user
được random, kèm CI. Conversion là diagnostic, không phải mục tiêu cuối.

## Bộ ab_data có 3 893 dòng nhóm và trang hiển thị không khớp. Bạn xử lý thế nào?

1. **Không xoá ngay.** Tìm hiểu vì sao: user control thấy trang mới là lỗi phân nhóm, lỗi cache,
   hay lỗi log? Tỉ lệ có bằng nhau giữa hai nhánh không (1 928 vs 1 965, khá cân)?
2. **Phân tích chính: intention-to-treat**, theo nhóm được gán. Không bị selection bias vì việc gán
   là ngẫu nhiên.
3. **Phân tích phụ**: loại các dòng lệch, so kết quả. Nếu kết luận giống nhau thì yên tâm; nếu khác,
   phải tìm ra nguyên nhân trước khi kết luận.
4. Loại trùng user (giữ lần đầu), và báo cáo rõ đã loại bao nhiêu và vì sao.

Sau khi làm sạch, conversion là 12.04% (control) và 11.88% (treatment), p ≈ 0.19: không có bằng
chứng trang mới tốt hơn, và CI cho thấy nếu có lợi thì rất nhỏ.

## Bạn sẽ xây dựng văn hoá thí nghiệm trong một công ty mới bắt đầu thế nào?

Câu hỏi cho vị trí senior / lead:

- **Bắt đầu nhỏ, thắng sớm**: chọn vài thí nghiệm có giá trị kinh doanh rõ, làm thật chuẩn, trình
  bày kết quả cho lãnh đạo.
- **Hạ tầng tối thiểu**: phân nhóm bằng hash nhất quán, log sự kiện phân nhóm, pipeline metric,
  kiểm SRM tự động. Cân nhắc GrowthBook/Statsig trước khi tự xây.
- **Quy trình**: template pre-registration, experiment review hằng tuần, kho kết quả thí nghiệm có
  thể tìm kiếm.
- **Đào tạo**: PM và engineer hiểu peeking, SRM, vì sao một OEC.
- **Kỳ vọng thực tế**: đa số ý tưởng không cải thiện metric; thí nghiệm "thất bại" vẫn là tri thức.
