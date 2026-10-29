# Câu hỏi phỏng vấn: Feature Engineering & Validation

## Data leakage là gì? Kể ba loại và một ví dụ thật cho mỗi loại.

Leakage là khi model dùng thông tin không có ở thời điểm dự đoán thật. Hậu quả luôn giống nhau: điểm
offline đẹp, điểm production tệ hơn, và thường chỉ lộ ra khi đã triển khai.

- **Target leakage**: feature là hệ quả của nhãn. Dự đoán review xấu của Olist mà dùng độ dài bình
  luận review: AUC một mình 0.756, mạnh hơn cả độ trễ giao hàng, vì khách bực thì viết dài.
- **Temporal leakage**: feature dùng dữ liệu tương lai. Tỉ lệ review xấu của seller tính trên toàn bộ
  dữ liệu (kể cả các đơn sau thời điểm dự đoán) đẩy AUC test từ 0.711 lên 0.759, một con số không hệ
  thống nào đạt được khi chạy thật.
- **Train-test contamination**: tham số tiền xử lý học từ cả dữ liệu đánh giá (scaler, imputer,
  target encoding fit trên toàn bảng), hoặc cùng một thực thể ở cả hai phía (một khách ở cả train
  và test).

Ứng viên senior nói thêm: leakage là quan hệ giữa feature và **thời điểm dự đoán**, không phải tính
chất của cột. Thời gian giao hàng hợp lệ nếu dự đoán lúc giao xong, là leakage nếu dự đoán lúc mua.

## Bạn phát hiện leakage thế nào trước khi model lên production?

Theo thứ tự rẻ tới đắt:

1. **Đóng khung trước**: viết ra thời điểm dự đoán, rồi với mỗi feature hỏi "giá trị này được ghi
   nhận lúc nào, bởi hệ thống nào". Phần lớn leakage bị bắt ở đây.
2. **AUC một mình** của từng feature: feature tốt bất thường so với độ khó của bài toán phải giải
   thích được.
3. **So thời điểm ghi nhận** với thời điểm dự đoán trên dữ liệu: tỉ lệ dòng mà feature chỉ có sau
   lúc dự đoán.
4. **Điểm quá tốt** so với baseline hay so với người khác từng làm bài toán.
5. **Feature importance**: feature quan trọng nhất là id, timestamp, hay cột không ai giải thích được.
6. **Shadow deployment**: chạy model song song, tính feature như production sẽ tính, so phân phối
   feature và điểm với lúc offline.

Phép kiểm tự động chỉ là sàng lọc: leakage yếu không có AUC một mình cao nhưng vẫn làm điểm lạc quan.

## Vì sao phải fit scaler, imputer, encoder chỉ trên train? Hiệu ứng có lớn không?

Vì ở production model gặp dữ liệu mà lúc train chưa tồn tại; mọi thống kê dùng để biến đổi dữ liệu
phải đến từ dữ liệu đã có. Fit trên toàn bảng là để thông tin của tập đánh giá chảy vào model.

Độ lớn tuỳ bước: với `StandardScaler` trên dữ liệu lớn thì gần như không đáng kể (trung bình của
100 nghìn dòng gần bằng trung bình của 80 nghìn dòng). Với bước **học từ nhãn** (target encoding,
chọn feature) thì rất lớn: chọn 20 trong 5 000 feature nhiễu trên toàn bộ dữ liệu rồi mới
cross-validate cho AUC 0.89 với nhãn ngẫu nhiên. Câu trả lời thực tế: không cần đo từng bước, cứ gói
mọi bước học tham số vào `Pipeline` là cross-validation tự làm đúng.

## Target encoding là gì? Rủi ro và cách làm đúng?

Thay mỗi category bằng tỉ lệ nhãn của category đó, làm trơn về prior để category ít dòng không nhận
giá trị cực đoan:

$$
\mathrm{enc}(c) = \frac{s_c + m \cdot \text{prior}}{n_c + m}
$$

Rủi ro: tính trên chính các dòng train thì với category ít dòng, mã gần bằng nhãn của chính dòng đó.
Trên Olist, mã hoá zip của khách (12 036 giá trị) theo cách ngây thơ cho AUC 0.856 trên train nhưng
0.536 trên validation; smoothing 20 không cứu được.

Làm đúng: **out-of-fold** trên train (dòng ở fold k dùng bảng học từ các fold khác), bảng học trên
toàn train cho validation/test. `sklearn.preprocessing.TargetEncoder` làm cross fitting trong
`fit_transform`. Với category gắn với thời gian (seller tốt lên hay xấu đi), thay bằng feature lịch sử
point-in-time.

## One-hot, target encoding, hashing, embedding: chọn thế nào?

| Số giá trị và tình huống | Chọn |
| --- | --- |
| Vài chục trở xuống | One-hot (với `handle_unknown`, gộp category hiếm) |
| Hàng trăm tới hàng nghìn, có tín hiệu | Target encoding out-of-fold; với model cây có thể dùng category native của LightGBM |
| Rất nhiều, liên tục xuất hiện giá trị mới (từ ngữ, URL) | Hashing (không lưu từ điển, chịu được giá trị mới, chấp nhận va chạm) |
| Rất nhiều, có quan hệ với nhau, dữ liệu lớn | Embedding học cùng model |

Cân nhắc thêm: model tuyến tính cần one-hot hoặc encoding số; model cây chịu được ordinal. Chi phí
serving: target encoding cần lưu bảng và cập nhật; hashing không cần.

## Bạn xử lý missing value thế nào?

Trước hết hỏi **vì sao thiếu**. Thiếu ngẫu nhiên (lỗi log) khác thiếu có hệ thống (sản phẩm không
có danh mục vì là seller mới). Thiếu có hệ thống thường mang tín hiệu.

- Numeric: impute median học trên train, kèm cột chỉ báo thiếu (`add_indicator=True`).
- Category: thêm giá trị `"missing"`.
- Model cây (LightGBM, HistGradientBoosting) xử lý NaN gốc, thường tốt hơn impute.
- Tránh `fillna(0)` mặc định: 0 thường là một giá trị có nghĩa.
- Không impute bằng model dùng cả nhãn; không impute bằng thống kê toàn bảng.

Và hỏi production sẽ thiếu giống lúc train không: nếu ở production một nguồn dữ liệu hay chậm, tỉ lệ
thiếu lúc serving cao hơn lúc train, model gặp phân phối khác.

## sklearn Pipeline và ColumnTransformer giải quyết vấn đề gì?

1. **Contamination**: cross-validation fit lại cả pipeline trong từng fold, nên không bước nào thấy
   fold kiểm tra.
2. **Training-serving skew**: một đối tượng chứa cả tiền xử lý và model; serve đúng cái đã train.
3. **Tuning cả tiền xử lý**: `GridSearchCV` tìm chiến lược impute, số chiều hashing cùng với tham số
   model.
4. **Dữ liệu dị loại**: mỗi nhóm cột một cách xử lý; cột không nêu tên bị bỏ (`remainder="drop"`),
   nên truyền cả DataFrame có cột nhãn vào cũng an toàn.

Giới hạn: Pipeline xử lý từng dòng độc lập. Feature tổng hợp qua nhiều dòng theo thời gian (tỉ lệ
review xấu của seller tới nay) không đặt gọn vào Pipeline; phải tính point-in-time trước, bằng as-of
join hoặc feature store.

## Khi nào dùng KFold, StratifiedKFold, GroupKFold, TimeSeriesSplit?

Câu hỏi quyết định: **dữ liệu đánh giá có giống dữ liệu model sẽ gặp không?**

- `KFold`/`StratifiedKFold`: dữ liệu i.i.d. thật, không có thời gian, không có nhiều dòng mỗi thực
  thể. Stratified khi nhãn hiếm để mỗi fold có đủ dòng dương.
- `GroupKFold`: nhiều dòng mỗi thực thể và model sẽ gặp thực thể mới (khách, bệnh nhân, seller).
- `TimeSeriesSplit`/chia theo mốc ngày: model chấm điểm cho tương lai, tức gần như mọi bài toán kinh
  doanh. Thêm `gap` khi nhãn cần thời gian mới biết.
- Kết hợp thời gian và nhóm khi phục vụ khách mới trong tương lai (cold-start).

Ví dụ thật: trên Olist, KFold cho AUC 0.754 ± 0.005; chia theo thời gian cho 0.743 với các fold từ
0.67 tới 0.83; test thật 0.695. KFold cho con số chắc chắn và sai.

## Vì sao KFold ngẫu nhiên lạc quan với dữ liệu theo thời gian, kể cả khi không có feature nào rò rỉ?

Ba cơ chế:

1. **Drift**: model được train trên dữ liệu trộn mọi giai đoạn, kể cả giai đoạn *sau* dòng kiểm tra,
   nên đã "thấy" chế độ của giai đoạn đó. Ở production nó chỉ thấy quá khứ.
2. **Nội suy thay vì ngoại suy**: model linh hoạt học được "tuần này tỉ lệ cao" từ các dòng lân cận
   trong thời gian. Với KFold, dòng lân cận có ở cả hai phía; ở production chỉ có phía trước.
3. **Che độ biến thiên**: mỗi fold KFold là một hỗn hợp giống nhau của mọi giai đoạn, nên std giữa
   các fold nhỏ giả tạo, giấu việc hiệu năng phụ thuộc giai đoạn.

Trên Olist trung bình chỉ lệch 0.01 AUC, nhưng độ lệch chuẩn giữa các fold khác nhau hơn mười lần (0.059 so với 0.005). Trên dữ liệu mô
phỏng có drift mạnh, KFold cao hơn chia thời gian trên 0.15 AUC.

## Bạn chọn feature thế nào, và lỗi nào hay gặp nhất?

Mục tiêu trước: bớt chi phí serving, bớt thứ có thể hỏng, dễ giải thích; hiếm khi là để tăng điểm.

- **Permutation importance** trên validation chia theo thời gian, lặp vài lần: theo metric thật, áp
  cho mọi model.
- **L1**: nhanh, nhưng chọn ngẫu nhiên một trong các feature tương quan.
- **Độ ổn định**: feature được chọn ở bao nhiêu fold thời gian.
- **Chi phí**: feature cần join bảng lớn hay gọi dịch vụ ngoài đắt hơn feature có sẵn.

Lỗi hay gặp nhất: **chọn feature trên toàn bộ dữ liệu rồi mới cross-validate**. Bước chọn đã thấy nhãn
của fold kiểm tra; với nhiều feature nhiễu nó tạo ra AUC 0.89 từ nhãn ngẫu nhiên. Lỗi thứ hai: bỏ hai
feature tương quan cùng lúc vì từng cái trông yếu. Trên Olist, hoán vị từng cột trong ba cột giao hàng
cho tổng mức giảm AUC 0.137, hoán vị cả nhóm cho 0.257.

## Feature tổng hợp theo thời gian (point-in-time) là gì? Tính thế nào?

Feature tổng hợp qua nhiều dòng (tỉ lệ review xấu của seller, số đơn của khách 30 ngày qua) phải được
tính **tại thời điểm dự đoán của từng dòng**, chỉ dùng sự kiện đã xảy ra và đã được ghi nhận trước đó.

Ba bẫy: so sánh phải chặt (sự kiện cùng lúc chưa chắc đã vào hệ thống); loại sự kiện của chính dòng
đó (khoảng 5% đơn Olist có review trả lời trước cả ngày giao); dùng **thời điểm ghi nhận nhãn**
(`review_answer_timestamp`), không phải thời điểm sự kiện xảy ra.

Cài đặt: cộng dồn theo thực thể trên dãy sự kiện đã sắp, rồi `pd.merge_asof(..., by=entity, allow_exact_matches=False)`.
O(n log n), chạy dưới 0.1 giây cho 96 nghìn đơn. Ở production: feature store có as-of join (Feast,
Tecton, bảng snapshot), dùng chung một logic cho training và serving.

## Model đạt AUC 0.80 trên validation nhưng 0.70 trên test. Bạn điều tra gì?

Không vội kết luận overfit. Theo thứ tự:

1. **Phân phối có đổi không**: tỉ lệ nhãn, tỉ lệ các feature mạnh nhất ở hai giai đoạn. Trên Olist,
   chính xác chuyện này xảy ra: tỉ lệ giao trễ 14.4% ở validation, 5.9% ở test, review xấu 18.0% so
   với 10.4%. Khi ít đơn trễ, tín hiệu mạnh nhất có ít đất dụng võ, AUC giảm dù model không đổi.
2. **Leakage chỉ có ở validation**: feature tính khác nhau giữa hai giai đoạn? Pipeline có fit trên
   train + val khi đo test không?
3. **Overfit validation**: đã thử bao nhiêu cấu hình trên validation? Nhiều thì điểm validation lạc
   quan.
4. **Chia theo thời gian nhiều fold**: điểm thay đổi theo giai đoạn ra sao? Nếu dao động 0.67–0.83 thì
   0.70 nằm trong khoảng bình thường.

Rồi báo cáo con số test kèm giải thích, không chỉnh model theo test.

## Case: PM muốn model dự đoán khách sẽ huỷ đơn, dùng mọi cột trong bảng orders. Bạn làm gì trước?

Đóng khung trước khi đụng dữ liệu:

- **Dự đoán lúc nào và để làm gì?** Lúc đặt hàng (để giữ hàng/ưu tiên) khác lúc sau khi thanh toán
  (để CSKH gọi). Mỗi thời điểm cho một tập feature hợp lệ khác.
- **Bảng orders lưu trạng thái cuối cùng**: `order_status`, ngày giao, ngày duyệt bị ghi đè khi đơn
  tiến triển. Cột `order_status = "canceled"` *chính là* nhãn; ngày giao trống là *hệ quả* của huỷ.
  Dùng chúng là target leakage hoàn hảo, AUC gần 1.
- Cần **lịch sử trạng thái** (event log hoặc snapshot) để biết lúc dự đoán đơn trông thế nào.
- **Nhãn**: huỷ trong bao lâu kể từ lúc dự đoán? Huỷ do khách hay do seller? Hai bài toán khác nhau.
- **Chia theo thời gian**, và nếu khách đặt nhiều đơn, kiểm tra cả theo nhóm.

Rồi mới tới feature: lịch sử huỷ của khách và seller (point-in-time), phương thức thanh toán, giá
trị đơn, thời gian chờ duyệt tính tới lúc dự đoán.

## Case: Model chống gian lận đạt AUC 0.97 offline, tuần đầu production chỉ còn 0.75. Chuyện gì có thể xảy ra?

Các giả thuyết, kèm cách kiểm:

- **Leakage qua nhãn trễ**: giao dịch bị đánh dấu gian lận sau vài tuần (chargeback); feature "số
  giao dịch bị khoá của thẻ" lúc train dùng trạng thái *hiện tại*, đã bao gồm kết luận điều tra. Kiểm:
  tính lại feature as-of thời điểm giao dịch.
- **Training-serving skew**: feature tính bằng batch SQL lúc train, bằng code khác lúc serve; khác
  cửa sổ thời gian, múi giờ, xử lý NaN. Kiểm: log feature lúc serve, so phân phối với lúc train trên
  cùng giao dịch.
- **Chia train/test sai**: KFold ngẫu nhiên, cùng một thẻ/thiết bị ở cả hai phía; model nhớ thẻ.
  Kiểm: đánh giá lại với GroupKFold theo thẻ, chia theo thời gian.
- **Phân phối đổi thật**: kẻ gian thích nghi (adversarial drift). Kiểm: hiệu năng theo tuần trên dữ
  liệu cũ.
- **Nhãn production chưa chín**: tuần đầu mới chỉ biết một phần gian lận; AUC tính trên nhãn chưa đủ.

Thường là kết hợp; leakage qua nhãn trễ và skew là hai thủ phạm hay gặp nhất.

## Case: Bạn xây model dự đoán review xấu cho Olist để CSKH gọi trước cho 10% đơn rủi ro nhất mỗi tuần. Thiết kế phần feature và validation thế nào?

**Đóng khung**: dự đoán lúc đơn vừa giao, nhãn là review ≤ 2 sao (review trả lời sau cùng), chỉ đơn
giao xong có review (nêu giới hạn: model không học từ khách không review).

**Feature**, tất cả biết được lúc giao:

- Giao hàng: thời gian giao, độ trễ so với lời hứa (quan hệ bậc thang: trễ 3–10 ngày có 67% review
  xấu, giao sớm chỉ 9%), thời gian hứa.
- Đơn và sản phẩm: số món, số seller, danh mục, giá, phí vận chuyển.
- Địa lý: khoảng cách khách–seller (haversine trên toạ độ trung vị zip, đã lọc toạ độ lỗi), bang.
- Seller: lịch sử review xấu tính point-in-time, số review quá khứ.
- Loại khỏi bảng: mọi cột review, id.

**Validation**: chia theo thời gian (train trước 2018, validation quý 1/2018, test sau đó), tuning và
chọn feature trên validation, test đo một lần. Metric khớp quyết định: không chỉ AUC mà precision
trong top 10% mỗi tuần, vì CSKH chỉ gọi được chừng đó. Ngưỡng đặt theo tỉ lệ (top 10%), không theo
xác suất cố định, vì tỉ lệ review xấu đổi theo giai đoạn (18.0% ở validation, 10.4% ở test).

**Sau triển khai**: theo dõi phân phối feature và precision theo tuần; đo tác động thật bằng A/B test
(gọi so với không gọi), vì model tốt chưa chắc can thiệp có tác dụng (module 03).

## Bạn giải thích cho PM vì sao model "kém hơn" sau khi bạn sửa leakage thế nào?

"Con số cũ đo một thứ không tồn tại. Model cũ được chấm điểm trong lúc được phép nhìn trộm đáp án:
nó biết trước một phần review của tương lai. Khi chạy thật, không ai đưa cho nó đáp án đó, nên điểm
thật của nó vốn đã thấp như con số mới, chỉ là chưa ai đo đúng."

Rồi đưa bằng chứng cụ thể: trên Olist, tỉ lệ review xấu của seller tính trên toàn bộ dữ liệu cho AUC
test 0.759; tính đúng point-in-time chỉ 0.711. Con số 0.711 là con số sẽ thấy ở production. Nhấn
mạnh lợi ích: kế hoạch kinh doanh (bao nhiêu cuộc gọi, giảm được bao nhiêu review xấu) giờ dựa trên
con số thật, và lần sau khi model "tụt" ở production sẽ không phải vì lý do này.
