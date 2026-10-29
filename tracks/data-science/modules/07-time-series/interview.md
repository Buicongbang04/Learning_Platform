# Câu hỏi phỏng vấn: Time Series & Forecasting

## Vì sao không dùng k-fold cross-validation ngẫu nhiên cho bài toán dự báo?

K-fold ngẫu nhiên trộn quá khứ và tương lai: model được train trên dữ liệu tháng 6 rồi chấm trên
tháng 3. Với chuỗi có tự tương quan, các điểm gần nhau gần như trùng thông tin, nên điểm test có
"hàng xóm" trong tập train và sai số đo được thấp hơn thực tế. Feature lag/rolling còn làm tệ hơn:
lag của một điểm train có thể chính là giá trị của một điểm test.

Cách đúng là **rolling origin**: train tới origin, dự báo H bước, dời origin, lặp lại. Thêm `gap`
nếu dữ liệu đến trễ. Câu trả lời senior nói thêm: backtest phải mô phỏng đúng cách model chạy trong
production (tần suất retrain, độ trễ dữ liệu, horizon), và chọn cấu hình trên các origin cũ, báo cáo
trên các origin mới hơn.

Ngoại lệ: Bergmeir, Hyndman & Koo (2018) chỉ ra k-fold vẫn hợp lệ cho model **thuần tự hồi quy** khi
residual không còn tự tương quan. Trong thực tế công nghiệp, ít ai muốn dựa vào điều kiện đó.

## Stationarity là gì? Làm sao kiểm tra và xử lý?

Chuỗi dừng (weakly stationary) có trung bình, phương sai và tự tương quan không đổi theo thời gian.
ARIMA mô hình hoá chuỗi dừng; chuỗi có xu hướng hoặc mùa vụ phải sai phân trước.

Kiểm tra: nhìn đồ thị trước, rồi dùng hai kiểm định có giả thuyết ngược nhau. ADF có H0 là "có unit
root", KPSS có H0 là "dừng". Trên Olist: chuỗi gốc ADF p = 0.069, KPSS p ≤ 0.01 (không dừng); sau một
lần sai phân ADF p < 0.001, KPSS p ≥ 0.1 (dừng).

Xử lý theo nguyên nhân: xu hướng ngẫu nhiên thì sai phân; xu hướng xác định thì trừ xu hướng; phương
sai tăng theo mức thì log hoặc Box-Cox; mùa vụ thì sai phân mùa vụ. Lỗi hay gặp: sai phân quá tay
(tạo tự tương quan âm giả), và coi "không bác bỏ H0" là "chứng minh H0".

## Đọc ACF và PACF thế nào để chọn bậc ARIMA?

- AR(p): ACF tắt dần, PACF cắt sau lag p.
- MA(q): ACF cắt sau lag q, PACF tắt dần.
- Đỉnh ở lag m, 2m: mùa vụ chu kỳ m.

Trên Olist sau sai phân: ACF lag 1 = −0.24 (gợi ý MA(1), dấu hiệu quen thuộc sau sai phân), đỉnh ở
lag 7 và 14 (mùa vụ tuần), nên SARIMA(·,1,1)(0,1,1)[7] là điểm xuất phát tự nhiên.

Nói rõ trong phỏng vấn: ACF/PACF chỉ cho ứng viên. Chọn cuối cùng bằng AIC trên train, kiểm residual
(Ljung-Box), và quan trọng nhất là backtest. Với hàng nghìn chuỗi, không ai đọc ACF bằng mắt; dùng
`auto_arima`/`AutoARIMA` hoặc chuyển sang global model.

## Giải thích MAE, RMSE, MAPE, sMAPE, MASE. Bạn chọn metric nào?

- MAE: sai số trung bình cùng đơn vị, dễ giải thích; tối ưu MAE cho ra median.
- RMSE: phạt nặng sai số lớn; tối ưu RMSE cho ra mean. Vài ngày bất thường có thể chi phối.
- MAPE: phần trăm, kinh doanh thích; không xác định khi y = 0 và bất đối xứng (dự báo thấp bị chặn
  ở 100%, dự báo cao không có trần) nên khuyến khích dự báo thấp.
- sMAPE: có trần 200%, nhưng vẫn bất đối xứng theo hướng khác và khó giải thích.
- MASE: MAE chia cho MAE in-sample của seasonal naive. Không phụ thuộc quy mô, chịu được số 0; mặc
  định khi so model trên nhiều chuỗi.

Chọn theo quyết định: tồn kho lệch phải và chi phí thiếu khác chi phí thừa thì nên dùng pinball loss
ở phân vị phù hợp. Báo cáo cho kinh doanh thì WAPE (tổng |sai số| / tổng y) thay MAPE. Luôn báo kèm
metric của baseline trên cùng backtest.

## Seasonal naive là gì và vì sao luôn phải có?

Dự báo bằng giá trị cùng mùa vụ gần nhất (thứ Hai tuần sau = thứ Hai tuần này). Không cần fit, không
thể overfit, và với dữ liệu bán lẻ theo ngày thường rất khó thắng.

Trên Olist, qua 12 origin, SARIMA tốt nhất chỉ thắng seasonal naive khoảng 5% MASE (1.19 so với
1.26) và thắng ở 7/12 origin. Trên Rossmann thì ngược lại: LightGBM có MAE 665 € so với 1 501 € vì
khuyến mãi xen kẽ theo tuần làm "tuần trước" là dự báo tệ. Không có baseline thì không phân biệt
được hai tình huống này, và không thể nói model "tốt".

## ARIMA và ETS khác nhau thế nào? Khi nào dùng cái nào?

ARIMA mô hình hoá tự tương quan của chuỗi đã sai phân; ETS làm mượt theo cấp số nhân các thành phần
level, trend, season. Mọi ETS tuyến tính đều có ARIMA tương đương, nhưng nhiều ARIMA không có ETS
tương đương, và ETS nhân tính không có ARIMA tương đương.

Thực tế: ETS ổn định, nhanh, mạnh khi mùa vụ rõ và trend thay đổi dần (trend damped thường dự báo
xa tốt hơn). ARIMA linh hoạt hơn với cấu trúc tự tương quan và nhận biến ngoại sinh (SARIMAX). Cả hai
là model một chuỗi, gặp khó với nhiều mùa vụ (ngày trong tuần + ngày trong năm) và với hàng nghìn
chuỗi. Trên Olist, ETS cộng tính damped (MASE 1.22) và SARIMA(1,1,1)(0,1,1)[7] (1.19) gần như hoà:
chọn cái dễ vận hành hơn.

## Dùng gradient boosting cho dự báo: dựng feature thế nào để không leakage?

Mỗi dòng là (chuỗi, ngày), target là giá trị ngày đó. Quy tắc: dự báo cho ngày t lập ở ngày t − H
thì mọi feature từ target chỉ dùng dữ liệu tới t − H.

- Lag: `groupby(series).shift(k)` với k ≥ H. Quên `groupby` thì giá trị của chuỗi này rò sang chuỗi kia.
- Rolling: tính trên cột **đã lùi** H, trong từng chuỗi. `rolling(28).mean()` không lùi là leakage.
- Biến biết trước (lịch khuyến mãi, giá đã lên kế hoạch, ngày lễ) dùng giá trị của chính ngày t.
- Biến chỉ biết sau (số khách, số đơn huỷ) thì không dùng.

Kiểm tra bằng test: sửa dữ liệu tương lai, feature của quá khứ không được đổi. Trên Rossmann, thêm
lag 1 và lag 7 vào model dự báo 42 ngày làm MAE "đẹp" hơn 13% (575 so với 665), một con số không bao
giờ đạt được trong production.

## Recursive và direct forecasting khác nhau thế nào?

- **Recursive**: một model dự báo một bước, đưa dự báo vào làm lag để dự báo bước tiếp. Một model,
  dùng được dữ liệu mới nhất; nhưng sai số tích luỹ và phân phối feature lúc dự báo (chứa dự báo)
  khác lúc train (chứa giá trị thật).
- **Direct**: model riêng cho mỗi bước h, chỉ dùng lag ≥ h. Không tích luỹ sai số; nhiều model để
  huấn luyện và theo dõi.
- **Direct một model, lag ≥ H**: đơn giản nhất, bỏ phí thông tin gần cho các bước gần.
- Kết hợp: model theo từng tuần của horizon (lag ≥ 7, ≥ 14, …) là điểm cân bằng hay dùng.

Chọn theo horizon và số chuỗi: horizon ngắn, ít chuỗi thì recursive ổn; horizon dài, nhiều chuỗi,
nhiều biến biết trước thì direct với global model.

## Prediction interval là gì? Làm sao biết interval của bạn đúng?

Khoảng mà giá trị thật được kỳ vọng rơi vào với xác suất danh nghĩa (80%, 95%). Kiểm bằng
**coverage** trên backtest (tỉ lệ thật sự nằm trong khoảng) và **interval score** (thưởng khoảng
hẹp, phạt 2/α mỗi đơn vị nằm ngoài).

Trên Olist, khoảng 80%: khoảng lý thuyết của SARIMA phủ 94% (quá rộng, Black Friday trong train làm
phương sai phình ra); khoảng empirical từ sai số tuyệt đối phủ 67% (năm 2018 lớn hơn giai đoạn hiệu
chỉnh); khoảng empirical từ sai số log-ratio phủ 83% và có interval score tốt nhất.

Lỗi hay gặp: chỉ kiểm coverage (khoảng vô hạn luôn phủ 100%); hiệu chỉnh và đánh giá trên cùng
origin; quên rằng khoảng của tổng 14 ngày không phải tổng các khoảng từng ngày (sai số tương quan).

## Hierarchical forecasting là gì? Bottom-up, top-down, MinT khác nhau thế nào?

Dự báo nhiều cấp (cửa hàng → vùng → toàn chuỗi) sao cho các con số cộng khớp. Ma trận tổng hợp S
nối mọi node với chuỗi đáy; reconciliation tuyến tính là
$$\tilde{\mathbf y} = \mathbf S (\mathbf S^\top \mathbf W^{-1} \mathbf S)^{-1} \mathbf S^\top \mathbf W^{-1} \hat{\mathbf y}$$.

- Bottom-up: dự báo đáy rồi cộng; giữ chi tiết, chuỗi đáy nhiễu thì tổng nhiễu.
- Top-down: dự báo tổng rồi chia theo tỉ lệ; ổn định ở trên, mất mẫu hình riêng của đáy.
- OLS (W = I), WLS structural, MinT (W là hiệp phương sai sai số): dùng thông tin mọi cấp.

Trên Rossmann (20 cửa hàng, 6 tuần): khi cấp trên dùng model có mùa vụ năm còn cấp cửa hàng dùng
Holt, OLS giảm MAE cửa hàng từ 6 891 xuống 3 738 €/tuần, còn bottom-up tệ ở mọi cấp. Khi mọi node
dùng cùng một model tuyến tính, base forecast đã coherent và reconcile không đổi gì. WLS theo phương
sai residual một bước lại làm tệ đi, vì trọng số phải phản ánh sai số ở đúng horizon.

## Xử lý ngày lễ, Black Friday, khuyến mãi trong dự báo thế nào?

- Sự kiện biết trước và lặp lại: biến ngoại sinh (SARIMAX `exog`, feature cho LightGBM), hoặc
  holiday effect trong Prophet. Cần ít nhất vài lần xuất hiện trong lịch sử để học được.
- Sự kiện trong lịch sử làm méo model: STL robust, hoặc thay bằng giá trị nội suy khi fit model
  cho ngày thường, rồi cộng lại hiệu ứng sự kiện riêng.
- Sự kiện mới hoặc hiếm: điều chỉnh thủ công có quy trình (ai được override, ghi lại lý do, đo sau
  xem override có giúp không).

Olist: Black Friday 2017 có 1 176 đơn trong khi seasonal naive dự báo 197. Với một lần xuất hiện trong
lịch sử, không model nào học được độ lớn đáng tin; cần thông tin kinh doanh (ngân sách marketing,
số seller tham gia).

## Dữ liệu có nhiều ngày bằng 0 (intermittent demand) thì làm gì?

Hay gặp ở SKU bán chậm, phụ tùng. MAPE vô dụng; MASE và metric dựa trên phân vị dùng được. Model:
Croston và biến thể (SBA, TSB) tách "có bán hay không" và "bán bao nhiêu khi có"; hoặc global
LightGBM với objective Tweedie/Poisson. Dự báo điểm trung bình (0.3 đơn/ngày) ít ý nghĩa cho vận
hành; điều cần là phân phối, ví dụ "xác suất bán ít nhất 1 trong tuần". Cũng cân nhắc gộp lên cấp
tuần hoặc nhóm sản phẩm, nơi chuỗi đủ dày để dự báo, rồi phân bổ xuống.

## Model dự báo đang chạy production bị tệ dần. Bạn điều tra thế nào?

1. Dữ liệu trước: pipeline có trễ, thiếu ngày, đổi định nghĩa (đơn huỷ có được đếm không)?
2. Tách sai số theo horizon, theo chuỗi, theo thời gian: lệch có hệ thống (bias) hay chỉ nhiễu hơn?
   Bias kéo dài là dấu hiệu level shift (đổi giá, mở kênh mới, đối thủ).
3. So với baseline chạy song song: baseline cũng tệ đi thì chuỗi khó hơn (môi trường đổi), không
   chỉ model hỏng.
4. Sự kiện bên ngoài: Olist tuần 21–27/5/2018 số đơn giảm gần một nửa, trùng cuộc đình công của
   tài xế xe tải ở Brazil. Không phải lỗi model, nhưng cần quy trình override.
5. Xử lý: retrain thường xuyên hơn, sliding window thay vì expanding nếu hành vi đã đổi, thêm biến
   giải thích được thay đổi, và dashboard theo dõi sai số theo thời gian với ngưỡng cảnh báo.

## Case: Olist muốn dự báo số đơn mỗi ngày cho 14 ngày tới để xếp ca kho. Bạn làm thế nào?

Đóng khung trước: quyết định là số nhân viên mỗi ca, chốt lịch trước 2 tuần, thiếu người (đơn trễ,
review xấu: đơn giao trễ có 54.1% review xấu) đắt hơn thừa người. Vậy cần dự báo **phân vị**, không
phải trung bình, ở cấp kho × ngày.

1. Dữ liệu: số đơn theo ngày mua, đủ mọi ngày, cắt bỏ giai đoạn khởi động (trước 2017-01-09) và đuôi
   dữ liệu chưa đầy đủ (sau 2018-08-19).
2. EDA: xu hướng tăng gần 3 lần trong 18 tháng, mùa vụ tuần (thứ Bảy thấp nhất), Black Friday.
3. Baseline seasonal naive; ứng viên SARIMA, ETS, LightGBM với lag ≥ 14 và feature lịch.
4. Backtest 12+ origin. Kết quả thật: SARIMA thắng seasonal naive khoảng 5%; mức thắng nhỏ so với
   độ dao động giữa các origin.
5. Khoảng dự báo: empirical từ sai số tương đối, kiểm coverage trên origin chưa dùng. Phân vị theo
   tỉ lệ chi phí (thiếu gấp 4 lần thừa thì phân vị 0.8).
6. Vận hành: retrain hằng tuần, dashboard sai số, quy trình override cho sự kiện (Black Friday,
   chiến dịch marketing), và đo lại sau mỗi sự kiện.

Điểm cộng: nói rõ dự báo cấp tổng rồi phân bổ theo kho hay dự báo từng kho rồi reconcile.

## Case: Bạn có 1 115 cửa hàng Rossmann, cần dự báo doanh thu từng ngày 6 tuần tới. Chọn phương pháp nào?

Với hơn một nghìn chuỗi liên quan và nhiều biến biết trước (khuyến mãi, ngày lễ, nghỉ học), một
**global LightGBM** là lựa chọn mạnh: học chung từ mọi cửa hàng, dùng được feature của cửa hàng
(loại, quy mô, khoảng cách đối thủ), và chạy nhanh. Fit 1 115 SARIMA riêng lẻ chậm, không tận dụng
được biến khuyến mãi một cách tự nhiên, và cửa hàng ít lịch sử sẽ có model yếu.

Thiết kế: feature lùi ≥ 42 ngày (hoặc model theo từng tuần của horizon), target log1p, chỉ train
trên ngày mở cửa, ngày đóng cửa là NaN trong lag. Backtest nhiều origin. Trên 50 cửa hàng thật,
LightGBM có MAE 665 € so với 1 501 € của seasonal naive ở origin 2015-06-20, và kết quả giữ ở hai
origin trước đó.

Lưu ý dữ liệu: 180 cửa hàng thiếu toàn bộ nửa sau năm 2014 (đóng cửa sửa chữa hoặc lỗi dữ liệu),
cần xử lý trước khi tính lag 364. Kết thúc bằng reconcile theo vùng/loại cửa hàng nếu tài chính cần
con số tổng khớp với vận hành.

## Case: CFO hỏi "dự báo doanh thu quý tới là bao nhiêu?" và muốn đúng một con số. Bạn trả lời thế nào?

Đưa một con số **kèm khoảng**, và giải thích bằng ngôn ngữ quyết định: "Kịch bản cơ sở là X; 80%
khả năng nằm giữa L và U. Nếu lập ngân sách chi phí cố định, nên dựa trên mức thấp; nếu đặt hàng tồn
kho, dựa trên mức cao hơn mức cơ sở."

Những điều cần nói rõ:

- Khoảng đến từ backtest: dự báo quý trước đây lệch bao nhiêu, không phải từ giả định đẹp.
- Các giả định: không có thay đổi giá lớn, chiến dịch marketing như kế hoạch. Nếu giả định đổi thì
  dự báo đổi thế nào (kịch bản).
- Con số quý phải khớp với dự báo tháng và theo vùng mà các phòng ban khác đang dùng (reconcile).

Không đưa con số trơn: một con số không có khoảng sẽ bị hiểu là chắc chắn, và lần đầu lệch, niềm tin
vào cả đội dữ liệu mất theo.

## Bạn đánh giá thế nào khi một model "thắng" baseline trong backtest?

Câu hỏi đúng không phải "MASE trung bình thấp hơn không" mà là "thắng có ổn định và đủ lớn để đáng
độ phức tạp không":

- Mức thắng so với độ dao động giữa các origin (trên Olist: thắng 5%, trong khi MASE từng origin dao
  động từ 0.6 tới 2.9).
- Tỉ lệ origin thắng (7/12 không phải là áp đảo); có thể dùng Diebold-Mariano test cho chênh lệch sai
  số, nhớ rằng sai số các bước trong cùng origin tương quan.
- Thắng ở đâu: horizon gần hay xa, chuỗi lớn hay nhỏ, ngày thường hay ngày sự kiện.
- Chi phí: thời gian fit, độ khó vận hành và giải thích, rủi ro hỏng khi dữ liệu đổi.

Nhiều đội chọn baseline mạnh (seasonal naive, ETS) cộng một lớp điều chỉnh sự kiện thay vì model
phức tạp thắng 3%.
