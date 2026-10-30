# Câu hỏi phỏng vấn: Thống kê & Experimentation cho quyết định

## Giải thích p-value cho một PM không học thống kê.

"Giả sử tính năng mới **không** có tác dụng gì. Khi đó, chênh lệch giữa hai nhóm vẫn dao động do ngẫu nhiên. p-value
là xác suất thấy chênh lệch lớn cỡ này (hoặc lớn hơn) chỉ do dao động đó. p = 0.03 nghĩa là nếu tính năng vô dụng
thì chỉ khoảng 3% thí nghiệm cho chênh lệch cỡ này."

Ba điều p-value **không** nói, và ứng viên senior nói luôn:

- Không phải xác suất "B tốt hơn A" (đó là câu hỏi Bayesian).
- Không đo độ lớn: 731 ngày Bike Sharing cho p = 0.0065 với độ ẩm, nhưng độ ẩm chỉ giải thích 1% biến động lượt
  thuê.
- p > 0.05 không có nghĩa "không có hiệu ứng": có thể thí nghiệm thiếu power.

Vì vậy readout tốt báo **chênh lệch kèm khoảng tin cậy** theo đơn vị business, p-value chỉ là dòng phụ.

## "Có ý nghĩa thống kê" và "có ý nghĩa thực tế" khác nhau thế nào? Cho ví dụ.

Có ý nghĩa thống kê: dữ liệu đủ để nói hiệu ứng khác 0. Có ý nghĩa thực tế: hiệu ứng đủ lớn để đáng làm (bù chi
phí, đổi quyết định). Cỡ mẫu lớn làm hiệu ứng rất nhỏ cũng "có ý nghĩa"; cỡ mẫu nhỏ làm hiệu ứng lớn vẫn "không có
ý nghĩa".

Ví dụ trên Bike Sharing: r(độ ẩm, lượt thuê) = −0.10, p = 0.0065, r² = 1%. Có ý nghĩa thống kê, không đủ để điều xe.
Ví dụ ngược: tổng lượt thuê ngày lễ thấp hơn ngày làm việc 850 lượt, p = 0.08, "không có ý nghĩa"; nhưng tách ra
thì thành viên giảm khoảng 1 300 lượt (p < 0.001) và khách vãng lai tăng khoảng 460 (p = 0.02): hai hiệu ứng thật
ngược chiều nhau.

Cách nói chuẩn trong thí nghiệm: đặt **MDE** trước theo mức đáng làm; "có ý nghĩa nhưng cả khoảng tin cậy dưới
MDE" thì vẫn là không ship.

## Bạn chọn kiểm định thống kê thế nào?

Theo ba câu hỏi: metric là gì, đơn vị lấy mẫu thế nào, stakeholder hỏi về cái gì.

| Tình huống | Kiểm định |
| --- | --- |
| Tỉ lệ 0/1, hai nhóm độc lập | z-test hai tỉ lệ (= chi-square 2×2) |
| Trung bình (doanh thu/khách), n lớn | Welch t-test, thường cắt đuôi ở ngưỡng đặt trước |
| Nhiều nhóm | Chi-square/ANOVA tổng, rồi so cặp có hiệu chỉnh nhiều kiểm định |
| Cùng đơn vị đo hai lần | Paired t-test trên chênh lệch |
| Tỉ lệ chia nhóm có đúng thiết kế? | Chi-square goodness of fit (SRM) |
| Quan hệ hai biến liên tục | Pearson r có khoảng tin cậy (Spearman nếu đơn điệu không tuyến tính) |
| "Phần lớn khách" chứ không phải trung bình | Mann-Whitney U |

Lỗi hay gặp không nằm ở công thức mà ở chọn kiểm định trả lời câu hỏi khác: CFO hỏi tổng doanh thu (trung bình ×
số người) mà dùng Mann-Whitney (so thứ hạng) là trả lời sai câu hỏi. Mặc định dùng Welch thay vì t-test phương
sai gộp vì hai nhóm thường không cùng phương sai.

## Một experiment brief tốt gồm những gì?

1. **Quyết định** cần ra và người quyết; giả thuyết có cơ chế ("nếu ... thì ... vì ...").
2. **Đối tượng**: định nghĩa đủ điều kiện, cố định tại ngày bắt đầu; **đơn vị chia nhóm** (người, phiên, cửa hàng,
   vùng) trùng hoặc thô hơn đơn vị phân tích; tỉ lệ chia; cách chia (hash + salt).
3. **Metric chính** (một), metric phụ, **guardrail có ngưỡng**.
4. **Baseline và lưu lượng từ dữ liệu thật**, sample size, MDE, thời lượng cộng cửa sổ đo, ngày đọc kết quả.
5. **Kiểm tra trước khi đọc**: SRM, log đủ, không peeking.
6. **Quy tắc quyết định** viết trước theo khoảng tin cậy và MDE.
7. **Rủi ro**: mùa vụ, novelty, lây nhiễm giữa nhóm, kéo cầu sớm.

Brief tốt trả lời được "nếu kết quả ra X thì làm gì" trước khi có X. Nó cũng là nơi DA nói "không khả thi" trước khi
công ty tốn ba tháng.

## Metric chính và guardrail khác nhau thế nào? Cho ví dụ cho một thí nghiệm voucher.

Metric chính là thứ thí nghiệm muốn cải thiện và dựa vào đó để ship. Guardrail là thứ **không được xấu đi** quá
một ngưỡng đặt trước; vượt ngưỡng thì không ship dù metric chính tốt.

Voucher 10% cho khách đang hoạt động:

- Metric chính: doanh thu **sau voucher** trên mỗi khách được chia nhóm (kể cả người không mua) trong 30 ngày, cắt
  đuôi ở p99 giai đoạn trước. Không chọn "tỉ lệ mua": voucher có thể làm nhiều người mua hơn ở giá thấp hơn mà
  lỗ.
- Metric phụ: tỉ lệ mua, số đơn, doanh thu 90 ngày (kéo cầu sớm?).
- Guardrail: tỉ lệ doanh thu bị huỷ (baseline 2.9% trên Online Retail II, ngưỡng +1 điểm), biên lợi nhuận, giá trị
  đơn trung bình.

## Sample size, MDE và thời lượng tính thế nào? Giảm MDE một nửa thì sao?

Cần baseline của metric (tỉ lệ p0 hoặc độ lệch chuẩn σ), MDE, alpha, power. Với metric trung bình:
n mỗi nhóm = 2 × (z₁₋α/₂ + z₁₋β)² × σ² / MDE². Cỡ mẫu tỉ lệ với 1/MDE²: giảm MDE một nửa thì cần gấp khoảng
**bốn** lần số người. Thời lượng = số người cần / lưu lượng đủ điều kiện mỗi tuần, làm tròn lên số tuần trọn (tối
thiểu hai tuần), **cộng cửa sổ đo** của metric.

Hai điểm DA hay quên: baseline phải tính trên đúng đối tượng sẽ vào thí nghiệm, chỉ với người đã đủ cửa sổ quan
sát; và phương sai của metric doanh thu có thể giảm rất mạnh bằng cắt đuôi (Online Retail II: độ lệch chuẩn doanh
thu 30 ngày từ 2 332 xuống 551 GBP khi cắt ở p99, cỡ mẫu giảm khoảng 18 lần).

## Case: trưởng nhóm CRM nói "A/B email chào mừng cho khách mới, chạy 4 tuần là biết". Bạn trả lời thế nào?

Tôi không trả lời bằng cảm giác mà lấy ba con số từ dữ liệu (Online Retail II):

- Baseline: 35.2% khách mới mua lần hai trong 60 ngày (chỉ tính khách đã đủ 60 ngày quan sát, cohort từ 2010).
- Lưu lượng: năm 2011 trung bình 31.7 khách mới mỗi tuần.
- Sample size: muốn thấy +5 điểm % (35% → 40%) cần 1 474 khách mỗi nhóm, tức **94 tuần** gom khách, chưa kể 60 ngày
  đo. Chạy 4 tuần chỉ phát hiện được hiệu ứng khoảng +25 điểm, không thực tế cho một email.

Câu trả lời: "4 tuần thì không biết được. Ta có thể: (1) thử trên mọi khách đang hoạt động (khoảng 1 900 người một
lần) với metric 30 ngày; (2) gửi cho mọi khách mới nhưng giữ holdout 10-20% và đọc dần trong 6-12 tháng; (3) chấp
nhận chỉ thấy hiệu ứng lớn." Đồng thời cảnh báo: dừng sớm khi p-value đẹp là peeking, không phải lối tắt.

## SRM là gì? Phát hiện thế nào, nguyên nhân thường là gì?

Sample Ratio Mismatch: tỉ lệ người dùng giữa các nhóm lệch khỏi tỉ lệ thiết kế nhiều hơn mức ngẫu nhiên cho phép.
Kiểm bằng chi-square goodness of fit với tỉ lệ **thiết kế** (lấy từ cấu hình, không từ dữ liệu), ngưỡng thường p <
0.001. Ví dụ thiết kế 50/50, quan sát 50 600 / 49 400: chi2 = 14.4, p ≈ 0.00015, dù lệch chỉ 1.2%.

Nguyên nhân hay gặp: redirect hoặc trang chậm làm người dùng một nhóm rời đi trước khi được log; lọc bot khác nhau;
lỗi hash/cấu hình; tính năng làm crash app ở một nhóm; phân tích chỉ trên người "đã thấy" tính năng mà việc thấy phụ
thuộc nhóm. Vì nguyên nhân thường liên quan tới hành vi, hiệu ứng đo được không tin được: dừng đọc kết quả, điều
tra.

Hai biến thể DA senior nhắc thêm: cỡ mẫu lớn làm SRM **nhạy hơn** (trên `marketing-ab` 588 nghìn người, nếu brief
ghi 95/5 thay vì 96/4 thì p ≈ 3e-271); và tổng thể đúng tỉ lệ vẫn có thể lệch trong phân khúc đo sau khi chia nhóm
(tỉ lệ `psa` theo ngày từ 3.50% tới 4.71%), dấu hiệu hai nhóm được phục vụ khác nhau.

## Peeking là gì? Nếu business thật sự cần dừng sớm thì sao?

Peeking: xem p-value nhiều lần trong lúc chạy và dừng ngay khi p < 0.05. Mỗi lần nhìn là một cơ hội thêm cho nhiễu
vượt ngưỡng: mô phỏng 28 lần nhìn (mỗi ngày trong 4 tuần) khi A và B như nhau cho khoảng 27% thí nghiệm "có ý
nghĩa" ở một thời điểm nào đó, thay vì 5%.

Nếu cần dừng sớm (tính năng gây hại, hoặc cơ hội lớn): thiết kế từ đầu **sequential testing** (group sequential với
ngưỡng alpha spending, hoặc always-valid inference mà các nền tảng experimentation hỗ trợ), và guardrail có ngưỡng
dừng khẩn cấp. Dashboard theo dõi trong lúc chạy chỉ để kiểm SRM và lỗi, không để đọc hiệu ứng.

## Case: readout cho CMO của chiến dịch quảng cáo với nhóm đối chứng PSA. Bạn trình bày gì?

Theo thứ tự của readout:

1. **Độ tin cậy**: 564 577 người nhóm `ad`, 23 524 nhóm `psa`; SRM so với thiết kế 96/4 p = 0.9998. Lưu ý tỉ lệ
   `psa` lệch theo ngày (3.5-4.7%), đã hỏi đội kỹ thuật.
2. **Hiệu ứng**: tỉ lệ mua 2.55% so với 1.79%, **+0.77 điểm %** (khoảng tin cậy 0.60-0.94), tương đối +43%.
3. **Quy ra business**: khoảng **4 300 đơn tăng thêm** trong 14 423 đơn của nhóm thấy quảng cáo; 10 nghìn đơn còn
   lại sẽ có kể cả không có quảng cáo.
4. **Quyết định**: tiếp tục nếu chi phí trên mỗi **đơn tăng thêm** thấp hơn biên lợi nhuận mỗi đơn. Tính chi phí
   trên mọi đơn của nhóm `ad` sẽ đánh giá thấp chi phí thật khoảng 3 lần.
5. **Điều chưa trả lời được**: tần suất quảng cáo tối ưu. Chuyển đổi tăng theo số quảng cáo đã thấy ở **cả** nhóm
   PSA, nên đó là correlation; muốn biết phải chia ngẫu nhiên tần suất.

## Case: agency báo "sau chiến dịch ở Đức, số khách mua mỗi tuần tăng 68%". Bạn kiểm tra thế nào?

So trước/sau trộn chiến dịch với mọi thứ khác thay đổi cùng lúc. Các bước:

1. Tái tạo con số: Online Retail II, khách Đức mỗi tuần từ 6.4 (tháng 3-8/2011) lên 10.8 (tháng 9-11): +68% là
   đúng về số học.
2. Nhóm đối chứng không bị nhắm, cùng mùa vụ: các nước châu Âu khác tăng **57%** cùng giai đoạn. Năm 2010, không
   có chiến dịch, Đức cũng tăng 46% từ tháng 3-8 sang 9-11. Phần lớn là mùa Giáng sinh.
3. DiD trên thang log: khoảng **+7%** (2×2) tới +10.5% (hồi quy theo tuần), khoảng tin cậy khoảng −6% tới +30%.
4. Độ tin cậy: xu hướng trước song song (khoảng cách log đi ngang); placebo với mốc giả và năm 2010 cho "hiệu ứng"
   −10% và −14%: nhiễu của phương pháp cỡ ±15%.
5. Kết luận đúng mực: "Không có bằng chứng chiến dịch tạo thêm khách; dữ liệu cũng không loại trừ một hiệu ứng
   dưới khoảng 30%, vì Đức chỉ có 6-11 khách mỗi tuần." Khuyến nghị: không tăng gấp đôi ngân sách; lần sau chạy geo
   experiment (chọn ngẫu nhiên vùng) để đo được.

(Chiến dịch là tình huống giả định trên dữ liệu thật của bài Advanced 02.)

## Correlation không phải causation: cho một ví dụ bạn gặp trong dữ liệu thí nghiệm.

Trong `marketing-ab`, người thấy hơn 100 quảng cáo chuyển đổi 17.1%, người thấy 1-5 quảng cáo chỉ 0.25%. Dễ kết luận
"tăng tần suất hiển thị". Nhưng nhóm PSA, không thấy quảng cáo nào, cũng tăng từ 0.28% lên 11.9% theo số lần
thấy PSA. Biến gây nhiễu là **mức độ dùng**: người dùng nhiều vừa thấy nhiều vị trí hiển thị vừa mua nhiều. Chỉ
biến được chia ngẫu nhiên (`ad` hay `psa`) cho so sánh nhân quả.

Ba lời giải thích phải loại trừ trước khi nói "X gây ra Y": biến gây nhiễu, nhân quả ngược (mở trạm xe ở nơi nhu
cầu đã cao), chọn mẫu (chỉ nhìn khách còn hoạt động).

## Difference-in-differences là gì? Giả định quan trọng nhất và cách kiểm?

DiD ước lượng tác động của một thay đổi áp cho một nhóm bằng: thay đổi của nhóm đó trừ thay đổi cùng giai đoạn của
nhóm đối chứng không bị áp. Phép trừ thứ hai loại bỏ phần thay đổi chung (mùa vụ, xu hướng công ty).

Giả định quan trọng nhất: **xu hướng song song**, nếu không có thay đổi thì hai nhóm đã đi song song. Không kiểm được
trực tiếp ở giai đoạn sau, nên kiểm gián tiếp: vẽ hai nhóm (chỉ số hoá) giai đoạn trước; độ dốc khoảng cách trước
gần 0; placebo với mốc giả hoặc năm trước. Thêm: không có sự kiện khác chỉ xảy ra ở một nhóm, không tràn sang nhóm
đối chứng, và chọn thang đo (tuyệt đối hay log) theo cơ chế: hai nhóm khác quy mô và chịu cùng mùa vụ thì thang log
hợp lý hơn.

## Regression để giải thích khác regression để dự báo thế nào? Đọc hệ số ra sao?

Giải thích hỏi "giữ các yếu tố khác như nhau, X đáng giá bao nhiêu Y". Chọn biến theo nghiệp vụ (biến gây nhiễu phải
có, biến trung gian không đưa vào), đọc hệ số kèm CI theo đơn vị business, R² không phải mục tiêu. Dự báo hỏi "giá
trị tiếp theo là bao nhiêu", chọn biến theo sai số trên dữ liệu chưa thấy; biến trễ, biến trung gian đều được.

Trên Bike Sharing: hệ số nhiệt độ là 162 lượt/°C khi chỉ có nhiệt độ, còn 130 khi thêm mùa, 125 khi thêm thời tiết.
Model một biến gán cho nhiệt độ cả phần của mùa (omitted variable bias). Cách nói cho trưởng vận hành: "giữ mùa và
thời tiết như nhau, ấm hơn 5°C thêm khoảng 620 lượt/ngày (540-710), tới khoảng 28°C thì không thêm nữa; mưa nhỏ
mất khoảng 1 900 lượt". Sai số chuẩn: dùng HC3, và HAC khi dữ liệu theo thời gian tự tương quan (Durbin-Watson 1.09
ở đây làm sai số chuẩn nhiệt độ tăng từ 8.6 lên 14.8).

## Metric doanh thu lệch phải rất mạnh. Bạn thiết kế và phân tích thế nào?

- **Định nghĩa**: doanh thu trên **mọi** người được chia nhóm (người không mua là 0), không phải trên người mua.
- **Giảm phương sai**: cắt đuôi (winsorize) ở ngưỡng đặt trước, ví dụ p99 của giai đoạn trước; CUPED (dùng doanh
  thu giai đoạn trước làm biến điều chỉnh) nếu nền tảng hỗ trợ.
- **Kiểm định**: Welch t-test trên trung bình (CLT với n lớn); bootstrap khi n nhỏ. Mann-Whitney chỉ khi câu hỏi là
  "phần lớn khách", vì nó không so trung bình.
- **Chạy thử A/A**: trên Online Retail II tháng 9/2011, chia ngẫu nhiên 1 923 khách (không ai được tác động), doanh
  thu không cắt cho chênh lệch −186 GBP/khách, p = 0.08, chỉ vì một khách 75 nghìn GBP rơi vào một nhóm; cắt ở p99
  còn −5.8. Đó là lý do ngưỡng cắt phải viết trong brief.

## Thí nghiệm có kết quả "không có ý nghĩa". Bạn báo cáo và đề xuất gì?

Đọc khoảng tin cậy, không đọc chữ "không có ý nghĩa":

- CI hẹp quanh 0 và cận trên dưới MDE: **có bằng chứng hiệu ứng nhỏ hơn mức đáng làm**. Không ship, ghi lại để
  không ai thử lại cùng ý tưởng.
- CI rộng, chứa cả 0 và MDE: **thiếu power**, chưa kết luận. Đề xuất: thêm thời gian/đối tượng nếu thiết kế cho
  phép, metric nhạy hơn, hoặc chấp nhận và chuyển sang ý tưởng khác.

Không làm: tách phân khúc tới khi có một cái "có ý nghĩa" rồi ship cho phân khúc đó. Với 10 phân khúc, xác suất có ít
nhất một p < 0.05 do may là 40%; phân khúc tìm ra sau khi xem dữ liệu là giả thuyết cho thí nghiệm sau.

## Khi nào không nên (hoặc không thể) chạy A/B test?

- Lưu lượng quá nhỏ cho MDE đáng làm (khách mới của Online Retail II: 94 tuần cho +5 điểm).
- Không chia ngẫu nhiên được hoặc không nên: thay đổi giá công khai, chính sách pháp lý, thay đổi ảnh hưởng toàn hệ
  thống (marketplace hai phía, network effect) mà chia theo người sẽ lây nhiễm.
- Quyết định rõ ràng hoặc bắt buộc (sửa lỗi bảo mật), hoặc chi phí sai rất nhỏ và dễ quay lại.
- Hiệu ứng chỉ thấy sau rất lâu (thương hiệu, retention năm).

Thay thế: holdout dài hạn, geo experiment (chia theo vùng), DiD hoặc synthetic control trên dữ liệu quan sát, hoặc
rollout từng bước có theo dõi guardrail. Nói rõ với stakeholder: các cách này dựa trên giả định, kết luận yếu hơn
thí nghiệm ngẫu nhiên.

## Vì sao bạn chọn Python (scipy, statsmodels) thay vì Excel hay một nền tảng experimentation?

Tuỳ tần suất và người dùng:

- **Python** cho phân tích thật: đủ mọi kiểm định, robust SE, DiD, mô phỏng A/A; notebook + git tái lập được, review
  được. Một readout có SRM, CI, cắt đuôi, phân khúc là vài chục dòng có test.
- **Excel/Sheets** khi người nhận cần tự đổi giả định (calculator sample size cho trưởng nhóm CRM), sau khi đã đối
  chiếu con số với code. Excel thiếu z-test tỉ lệ, robust SE, và khó tái lập.
- **Nền tảng experimentation** (Optimizely, Statsig, Eppo, GrowthBook) khi công ty chạy hàng chục thí nghiệm mỗi
  tháng: chia nhóm ổn định, log exposure, SRM tự động, scorecard có guardrail, sequential test. DA vẫn dùng Python
  để phân tích sâu và kiểm lại con số của nền tảng.
- **R** nếu team có truyền thống econometrics (`fixest`, `sandwich`); kết quả tương đương.

Ở công ty nhỏ chạy vài thí nghiệm mỗi quý, Python + một template readout là đủ và rẻ nhất; khi số thí nghiệm tăng,
chi phí sai sót do mỗi người tính một kiểu lớn hơn chi phí nền tảng.
