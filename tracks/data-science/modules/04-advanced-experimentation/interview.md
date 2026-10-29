# Câu hỏi phỏng vấn: Experimentation nâng cao

## CUPED là gì? Vì sao nó không làm lệch ước lượng tác động?

CUPED điều chỉnh metric bằng dữ liệu trước thí nghiệm của cùng đơn vị:

$$
Y_{\text{cuped}} = Y - \theta\,(X - \bar X), \qquad \theta = \frac{\mathrm{cov}(Y, X)}{\mathrm{var}(X)}
$$

Hiệu giữa hai nhánh sau điều chỉnh là $$(\bar Y_T - \bar Y_C) - \theta(\bar X_T - \bar X_C)$$. Vì
$$X$$ đo **trước** khi random, $$\bar X_T - \bar X_C$$ có kỳ vọng 0: số hạng thứ hai chỉ trừ bớt phần
"xui rủi" khi một nhánh tình cờ nhận nhiều user mạnh hơn, không trừ tác động. Variance giảm theo hệ
số $$1 - \rho^2$$.

Ứng viên senior nói thêm: CUPED một covariate tương đương hồi quy `Y ~ treat + X`, và điều kiện sống
còn là covariate không bị treatment ảnh hưởng. Covariate đo sau khi bật thí nghiệm (dù chỉ chồng một
ngày) chứa tác động, và CUPED sẽ trừ mất nó.

## CUPED giảm được bao nhiêu variance? Bạn ước lượng trước khi chạy thế nào?

Đúng bằng $$\rho^2$$, bình phương tương quan giữa metric và covariate. Trước khi hứa hẹn, lấy dữ liệu
lịch sử của đúng tổng thể sẽ vào thí nghiệm, chia hai kỳ liên tiếp dài bằng thí nghiệm dự kiến, tính
$$\rho$$ giữa hai kỳ. Cỡ mẫu cần nhân với $$1 - \rho^2$$.

Con số thật dao động cực lớn: doanh số tháng trước và tháng này của cửa hàng Rossmann tương quan
0.99, CUPED giảm 98% variance; chi tiêu 12 tháng trước và "có ghé website trong 2 tuần" của
Hillstrom tương quan 0.065, CUPED giảm 0.4%. Khác biệt nằm ở chỗ covariate có phải **chính metric
đó, của chính đơn vị đó, ở kỳ trước** không.

## User mới không có dữ liệu trước thí nghiệm. CUPED xử lý thế nào?

Không được bỏ họ: bỏ user mới làm đổi tổng thể, và nếu treatment ảnh hưởng tới việc ai là user mới
(ví dụ thay đổi trang đăng ký) thì còn gây lệch. Các cách:

- Điền covariate bằng một hằng số (0 hoặc trung bình) **và** thêm biến chỉ báo "không có lịch sử"
  vào hồi quy. Tương đương điều chỉnh riêng nhóm có lịch sử, nhóm mới giữ nguyên.
- Dùng covariate thay thế có sẵn cho mọi user (nguồn traffic, thiết bị, quốc gia), thường yếu hơn
  nhiều.

Tỉ lệ user mới càng cao thì lợi ích càng giảm. Netflix báo cáo variance reduction kém hẳn ở user mới
vì không tìm được covariate tương quan mạnh.

## CUPAC khác CUPED thế nào? Rủi ro lớn nhất là gì?

CUPAC dùng **dự đoán của model ML** làm covariate, gom nhiều đặc trưng trước thí nghiệm và quan hệ
phi tuyến vào một con số. Variance giảm bằng $$R^2$$ của model trên dữ liệu thí nghiệm.

Rủi ro lớn nhất là rò rỉ:

- Model dùng đặc trưng bị treatment ảnh hưởng (số lần mở app khi treatment là push notification).
- Model huấn luyện trên chính outcome của đơn vị nó dự đoán, kể cả gián tiếp (fit trên toàn bộ dữ
  liệu thí nghiệm rồi predict lại). Phải huấn luyện trên kỳ trước, hoặc cross-fitting.

Rủi ro thứ hai là kỳ vọng sai. Trên Olist, model LightGBM dự đoán giao trễ từ thông tin lúc đặt
hàng chỉ có $$\rho$$ khoảng 0.15 với outcome, giảm 2.3% variance. Model huấn luyện trên 2017 còn bị
lệch khi áp lên 2018 (hệ số θ khoảng 0.46 thay vì gần 1). CUPAC vẫn không lệch, nhưng không cứu được
thí nghiệm thiếu power.

## Stratified sampling hay post-stratification? Khi nào chọn cái nào?

Cả hai loại bỏ variance giữa các tầng. Với mẫu lớn, lý thuyết cho thấy chúng giảm variance như nhau;
Netflix kiểm trên dữ liệu thật và khuyên dùng kỹ thuật **sau khi gán** (post-stratification, CUPED)
vì stratified sampling theo thời gian thực cần hệ thống hàng đợi phức tạp và thực tế cho kết quả kém
hơn.

Stratified sampling đáng công khi **ít đơn vị**: vài chục thành phố, một nghìn cửa hàng. Random đơn
giản có thể tình cờ gửi phần lớn cửa hàng lớn vào một nhánh; gán theo tầng chặn điều đó từ đầu, bảng
so sánh hai nhánh trông cân bằng, và lãnh đạo tin kết quả hơn. Phân tích vẫn phải tính theo tầng
(hoặc CUPED), nếu không SE sẽ quá lớn.

Chọn tầng: tầng phải **dự đoán được metric**. Trên Rossmann, chia theo loại cửa hàng giải thích 4.0%
variance doanh số, chia theo decile doanh số tháng trước giải thích 85.9%.

## Ratio metric là gì? Vì sao không dùng t-test thông thường?

Metric là tỉ số của hai tổng, như CTR = tổng click / tổng lượt xem, khi thí nghiệm random theo user.
t-test (hoặc z-test tỉ lệ) trên từng lượt xem coi các lượt xem độc lập, nhưng các lượt xem của cùng
một user tương quan: user thích click thì click ở mọi lượt. SE bị đánh giá thấp, tỉ lệ báo động nhầm
vượt 5%.

Cách đúng: gộp về mức user (tổng tử $$Y_i$$, tổng mẫu $$X_i$$) rồi dùng delta method:

$$
\mathrm{var}\!\left(\frac{\bar Y}{\bar X}\right) \approx \frac{1}{n\,\mu_X^2}\left(\sigma_Y^2 - 2R\,\sigma_{XY} + R^2\sigma_X^2\right)
$$

Hoặc bootstrap theo **user**. Delta method rẻ hơn nhiều nên là lựa chọn của các platform.

## Bạn kiểm chứng một phương pháp tính SE mới cho platform thế nào?

Bằng **A/A trên dữ liệu thật**: lấy dữ liệu lịch sử, chia ngẫu nhiên đơn vị thành hai nhóm hàng nghìn
lần, tính p-value mỗi lần. Không có tác động nào, nên phương pháp đúng phải cho khoảng 5% số lần p <
0.05, và p-value phân phối đều. Sau đó cài một tác động đã biết vào một nhóm để đo power.

Ví dụ trên Olist: metric giá trung bình mỗi sản phẩm, random theo khách, 2 000 lần A/A. Delta method
báo nhầm 5.3%, cách coi mỗi sản phẩm độc lập báo nhầm 7.3% (design effect 1.17). Cài +2% giá: delta
method phát hiện được 51.8% số lần, tức thí nghiệm giá trên Olist chỉ nhạy với thay đổi lớn hơn 2%.

Một lần A/A cho p > 0.05 không chứng minh gì; cần phân phối của hàng trăm, hàng nghìn lần.

## Thí nghiệm của bạn random theo user nhưng PM muốn xem "doanh thu mỗi phiên". Bạn nói gì?

Hai việc. Về thống kê: đây là ratio metric, đơn vị phân tích (phiên) nhỏ hơn đơn vị random (user);
SE phải tính bằng delta method theo user, không phải t-test trên phiên.

Về sản phẩm: "doanh thu mỗi phiên" có thể tăng chỉ vì treatment làm user mở **ít phiên hơn** (bỏ các
phiên ngắn), trong khi tổng doanh thu không đổi hoặc giảm. Metric tỉ số dễ bị thay đổi ở mẫu số đánh
lừa. Đề xuất: OEC là doanh thu **mỗi user được random**, kèm số phiên mỗi user và doanh thu mỗi phiên
làm metric chẩn đoán để hiểu cơ chế.

## SUTVA là gì? Cho ví dụ thí nghiệm vi phạm SUTVA.

SUTVA (Stable Unit Treatment Value Assumption): kết quả của một đơn vị chỉ phụ thuộc nhánh của chính
nó, không phụ thuộc nhánh của đơn vị khác. Ví dụ vi phạm:

- Tính năng nhắn tin: user treatment nhắn cho user control, control cũng hưởng lợi. Tác động bị đánh
  giá **thấp**.
- Giảm phí ship cho khách treatment trong app giao hàng: khách treatment đặt nhiều hơn, chiếm shipper
  của khách control. Tác động bị **phóng đại**. Trong mô phỏng của module, A/B theo user báo tác động
  gấp khoảng 3.7 lần tác động thật khi bật cho tất cả.
- Thí nghiệm giá trên marketplace: seller đổi giá cho cả hai nhóm khách.

Vi phạm SUTVA tạo **thiên lệch**, không phải nhiễu: tăng cỡ mẫu chỉ làm CI hẹp lại quanh con số sai.

## Switchback experiment là gì? Thiết kế nó thế nào?

Random theo **khung thời gian** trong một vùng: trong một khung (30 phút, 1 giờ), mọi khách và nguồn
cung cùng một nhánh, nên không có chuyện nhánh này "cướp" của nhánh kia. Các quyết định:

- **Độ dài khung**: đủ dài để hệ thống phản ứng với thay đổi, đủ ngắn để có nhiều đơn vị và trải đều
  các giờ trong ngày, ngày trong tuần.
- **Carryover**: đơn tồn, tài xế đang chạy từ khung trước. Bỏ phần đầu mỗi khung (burn-in) khỏi phân
  tích. Trong mô phỏng của module: đổi nhánh mỗi khung không burn-in thì ước lượng còn khoảng 2% tác
  động thật; block 6 khung bỏ 2 khung đầu thì về khoảng 96%.
- **Phân tích theo khung**, không theo user, SE bằng randomization inference vì các khung liền nhau
  tương quan.

Giới hạn: chỉ đo tác động ngắn hạn. Tác động dài hạn (khách quen phí mới, tài xế đổi giờ làm) cần
random theo vùng địa lý trong nhiều tuần.

## Novelty effect và primacy effect khác nhau thế nào? Phát hiện ra sao?

Novelty: tác động lớn lúc đầu vì cái mới gây tò mò, rồi giảm. Primacy (change aversion): user quen cái
cũ, lúc đầu phản ứng tệ, rồi tăng dần. Cả hai làm trung bình toàn kỳ khác tác động dài hạn.

Phát hiện: vẽ tác động theo **số ngày kể từ lần đầu user thấy thay đổi**, không theo ngày lịch (theo
ngày lịch, user mới vào sau trộn với user cũ, che xu hướng). Kiểm định xu hướng bằng hồi quy có trọng
số. Tách theo user mới và user cũ: user mới không có "cái cũ" để so nên thường không có novelty hay
primacy, là nhóm đối chứng tự nhiên.

Ước lượng dài hạn: dùng cửa sổ ngày phơi nhiễm cao, nhưng nhớ hai bẫy: thành phần user trong cửa sổ đó
khác toàn kỳ (chỉ user vào sớm mới có ngày phơi nhiễm cao), và SE phải gộp theo user. Cách bền nhất là
holdout sau khi ship.

## Phân tích segment cho thấy tác động có ý nghĩa ở iOS (p = 0.01) nhưng không ở Android (p = 0.3). Kết luận gì?

Chưa kết luận được gì về **khác biệt** giữa hai platform. "Có ý nghĩa" ở nhóm này và "không" ở nhóm
kia có thể chỉ do cỡ mẫu hoặc may rủi; hai ước lượng có thể gần nhau với CI chồng lên nhau. Phải kiểm
định chính khác biệt: hồi quy `Y ~ treat * C(platform)`, xem hệ số tương tác.

Thêm: segment có được định trước không? Đã xem bao nhiêu segment? Nếu đã xem 20 chiều thì một kết quả
p = 0.01 là chuyện bình thường. Kết quả HTE tìm sau khi nhìn dữ liệu là giả thuyết cho thí nghiệm sau,
không phải căn cứ để ship riêng cho iOS.

## Case: Dashboard báo giao diện mới tăng thời gian đọc +0.85 phút/ngày sau 4 tuần, p rất nhỏ. PM muốn đưa con số này vào kế hoạch năm. Bạn làm gì?

1. Kiểm tra độ tin cậy cơ bản: SRM, đơn vị random, log đầy đủ.
2. Vẽ tác động theo ngày phơi nhiễm, tách user cũ và user mới. Nếu tác động ở user cũ giảm dần (ví dụ
   từ gần +2.9 phút ngày đầu xuống khoảng +0.8 sau 6 ngày) còn user mới phẳng, đó là novelty.
3. Ước lượng dài hạn: tác động ở cửa sổ ngày phơi nhiễm cao **cho từng segment**, gộp theo tỉ lệ user
   thật, SE gộp theo user. Trong bài Advanced 02 con số này khoảng +0.59 với CI [0.16, 1.02], so với
   +0.85 trên dashboard.
4. Khuyến nghị: ship nếu +0.59 (và cận dưới 0.16) vẫn đáng giá; kế hoạch dùng khoảng, không dùng
   +0.85; giữ holdout 1–5% user vài tháng để đo dài hạn thật.
5. Nói rõ giới hạn: 4 tuần không nói gì về tháng thứ 6; HTE theo trung bình 4 tuần có thể bị novelty
   che (user mới có tác động dài hạn gấp khoảng 2.4 lần user cũ dù trung bình 4 tuần gần bằng nhau).

## Case: Bạn là DS của một nền tảng giao đồ ăn. Team muốn thử giảm phí ship 30% vào giờ cao điểm. Thiết kế thí nghiệm.

**Vì sao không random theo user**: khách được giảm phí đặt nhiều hơn, chiếm shipper của khách không
được giảm, tác động bị phóng đại; và khách control có thể chờ lâu hơn bình thường, làm hại họ.

**Thiết kế**: switchback theo khung 30–60 phút trong từng thành phố, cân bằng số khung hai nhánh theo
giờ trong ngày và ngày trong tuần, burn-in 10–15 phút đầu mỗi khung (thời gian đơn tồn được xử lý).
Chạy ít nhất 2 tuần. Nếu muốn đo dài hạn (khách quen phí thấp, shipper đổi giờ làm), bổ sung thí nghiệm
theo cặp thành phố tương đồng.

**Metric**: OEC là tổng giá trị đơn hoàn thành (hoặc lợi nhuận đóng góp) mỗi khung; guardrail là thời
gian giao, tỉ lệ đơn bị huỷ do không có shipper, thu nhập mỗi giờ của shipper; chẩn đoán là số đơn đặt,
tỉ lệ chuyển đổi.

**Phân tích**: đơn vị là khung; CUPED với cùng metric của cùng khung giờ tuần trước (tương quan theo
khung giờ thường cao), SE bằng randomization inference. Định trước burn-in và quy tắc ship.

## Case: Một marketplace B2B chỉ có 40 thành phố. Muốn thử chương trình hoa hồng mới cho seller. Làm sao có đủ power?

40 đơn vị là rất ít; mỗi thành phố khác nhau nhiều về quy mô. Các đòn bẩy:

1. **CUPED / hồi quy với cùng metric của chính thành phố ở kỳ trước**: với metric ổn định như GMV, tương
   quan giữa hai kỳ thường rất cao (doanh số cửa hàng Rossmann giữa hai tháng tương quan 0.99, giảm 98%
   variance). Đo trên dữ liệu lịch sử trước.
2. **Stratified sampling hoặc matched pairs**: ghép cặp thành phố tương đồng (quy mô, tăng trưởng), random
   trong từng cặp. Với 20 cặp, mỗi cặp là một quan sát hiệu; tránh chuyện một nhánh nhận hết thành phố
   lớn.
3. **Kiểm chứng bằng A/A trên dữ liệu lịch sử**: chạy lại phân tích trên các kỳ không có thí nghiệm, xem
   tỉ lệ báo động nhầm và MDE thực tế.
4. **Chạy lâu hơn và metric nhạy hơn**: GMV của seller đang hoạt động thay vì GMV tổng.
5. Nếu vẫn không đủ: synthetic control hoặc difference-in-differences (module 06) trên một vài thành phố
   được chọn, chấp nhận giả định mạnh hơn, và nói rõ điều đó với người ra quyết định.

## Bạn sẽ xây phần variance reduction cho một experimentation platform thế nào?

- **Dữ liệu**: với mỗi metric, pipeline tính sẵn giá trị của cùng metric ở kỳ trước cho mọi đơn vị (cửa
  sổ bằng thời lượng thí nghiệm, kết thúc trước ngày bật). Đây là việc của Data Engineer, và là phần tốn
  công nhất.
- **Phương pháp mặc định**: CUPED (hồi quy) với covariate kỳ trước + chỉ báo "không có lịch sử"; delta
  method cho mọi ratio metric; SE theo đơn vị random.
- **CUPAC** cho vài metric chính khi có đặc trưng tốt, model huấn luyện trên kỳ trước, đóng băng phiên
  bản.
- **Kiểm chứng liên tục**: A/A định kỳ trên dữ liệu thật cho từng metric, theo dõi tỉ lệ báo động nhầm;
  báo cáo variance reduction đạt được cho mỗi thí nghiệm để team biết kỳ vọng.
- **Minh bạch**: dashboard hiện cả kết quả thô và kết quả điều chỉnh. Nếu hai con số lệch nhau nhiều hơn
  vài SE, đó là tín hiệu covariate có vấn đề (bị treatment ảnh hưởng, hoặc pipeline sai).
