# Câu hỏi phỏng vấn: MLOps cho Data Scientist

## Một model "xong" khi nào? Bạn giao gì cho đội kỹ thuật?

Model xong khi nó **vận hành được**, không phải khi AUC trên notebook đẹp. Thứ DS giao tối thiểu:

- Một artifact có phiên bản (trong registry) gồm **toàn bộ pipeline**, từ dữ liệu thô của request
  tới xác suất, không chỉ hệ số model.
- Signature: tên, kiểu, cột nào được phép thiếu, output là xác suất hay nhãn.
- Thời điểm dự đoán và danh sách feature có sẵn lúc đó.
- Metric trên tập test theo thời gian, so với baseline đơn giản, tách theo segment quan trọng.
- Ngưỡng quyết định và lý do kinh doanh, tách khỏi model.
- Kế hoạch monitoring: chỉ số, ngưỡng, độ trễ của nhãn.
- Một tập "golden" vài nghìn dòng kèm output kỳ vọng để kiểm parity.

Ứng viên senior nói thêm: "xong" còn gồm cả cách **gỡ** model, tức rollback về version trước trong
vài phút.

## MLflow Tracking lưu những gì? Backend store và artifact store khác nhau thế nào?

Mỗi run có params, metrics (có thể theo step), tags, và artifacts. **Backend store** là database
(SQLite, PostgreSQL, MySQL) giữ metadata và model registry. **Artifact store** giữ tệp (model, hình,
bảng) trên thư mục, S3, GCS, Azure Blob. Tách hai thứ vì metadata cần truy vấn nhanh còn artifact
cần lưu rẻ và lớn.

Lỗi thực tế: không đặt artifact location, artifact rơi vào `./mlruns` của thư mục đang chạy;
dùng file store `./mlruns` làm backend (MLflow 3 đã đưa vào chế độ bảo trì); chạy server MLflow mà
máy client không có quyền đọc ghi artifact store. Một run nên có cả phiên bản dữ liệu và git commit,
không chỉ hyperparameter.

## Bạn chọn model tốt nhất trong 200 run thế nào?

Theo **một metric trên validation** đã định trước, bằng truy vấn (`search_runs` với `order_by`), chỉ
trong các run `FINISHED`. Rồi kiểm:

- Chênh lệch giữa top run có lớn hơn sai số của metric không? Trên Olist, bốn giá trị C cho
  `val_auc` từ 0.7983 tới 0.7998: chênh 0.0015 AUC trên 20 nghìn đơn là nhiễu.
- Model đơn giản hơn có gần bằng không? Hoà thì chọn đơn giản.
- Chọn 200 lần trên cùng validation là một dạng overfit vào validation. Tập test chỉ dùng một lần
  cho model cuối.

Bẫy: chọn theo AUC test, hoặc chọn run có metric tốt nhất mà không để ý run đó bị lỗi giữa chừng.

## Model signature là gì, và vì sao `pyfunc` của một classifier có thể trả toàn số 0?

Signature là schema đầu vào/đầu ra lưu cùng model. Khi nạp qua `mlflow.pyfunc`, MLflow kiểm đầu
vào: thiếu cột thì báo lỗi; kiểu không ép được an toàn (ví dụ `int64` sang `float64`) cũng báo lỗi.
Signature nên được suy trên dữ liệu đủ lớn để cột hay thiếu được đánh dấu optional.

Pyfunc mặc định gọi `predict`, tức nhãn ở ngưỡng 0.5. Với bài toán mất cân bằng (review xấu 12.8%),
gần như không đơn nào vượt 0.5 nên service trả toàn số 0, trông như model "hỏng". Sửa bằng
`pyfunc_predict_fn="predict_proba"` khi log, và đặt ngưỡng ở tầng ứng dụng.

## Model Registry dùng để làm gì? Alias khác stage thế nào?

Registry giữ mọi version của một model có tên, mỗi version trỏ về run sinh ra nó. Service nạp theo
tên + alias (`models:/bad-review@champion`), nên phát hành là đổi alias, rollback là trỏ alias về
version cũ, không cần deploy lại code.

Stage cũ (`Staging`, `Production`, `Archived`) là danh sách cố định, mỗi stage một version. Alias
là con trỏ đặt tên tự do: `champion`, `challenger`, `previous_champion`, `shadow`, nhiều alias có
thể cùng tồn tại, khớp với quy trình phát hành thật (shadow, canary). MLflow đã chuyển sang alias.

## Batch hay online scoring? Bạn quyết định thế nào?

Hỏi ba câu: kết quả cần ngay trong request của người dùng không? Feature có sẵn lúc request không?
Sai một lần thì hậu quả gì?

- Batch khi kết quả có thể chờ (danh sách CSKH mỗi sáng, điểm tín dụng định kỳ, gợi ý email). Rẻ,
  đơn giản, dễ chạy lại.
- Online khi quyết định nằm trong luồng người dùng (gợi ý trên trang, chặn gian lận lúc thanh toán).
  Đắt hơn: service luôn chạy, cần SLA, fallback.
- Lai: tính sẵn phần nặng theo batch (embedding, đặc trưng lịch sử), online chỉ ghép phần mới.

Nhiều yêu cầu "realtime" thực ra là "cần mới hơn một ngày": batch mỗi giờ thường đủ. Nói được điều
đó là dấu hiệu senior.

## Training-serving skew là gì? Kể ba nguồn và cách phòng.

Skew là khi cùng một đơn nhận feature (và score) khác nhau giữa lúc train/batch và lúc serve.
Nguồn hay gặp:

1. Hai bản cài feature: SQL ở batch, Python ở online, lệch nhau ở làm tròn ngày (đơn giao 15:00 đúng
   ngày hẹn: 0 ngày trễ ở bên này, 0.625 ở bên kia).
2. Kiểu và giá trị thiếu: NULL thành NaN ở batch, chuỗi rỗng ở online; `int` với `float`.
3. Múi giờ: UTC ở kho dữ liệu, giờ địa phương ở app.
4. Thời điểm: online gọi model khi chưa có thông tin mà model được train với giả định là có.

Cách phòng: một hàm feature duy nhất cho cả hai đường, pipeline gói cả tiền xử lý, log feature lúc
serve, và kiểm parity định kỳ (chấm lại request online bằng đường batch, so score). Ở quy mô lớn:
feature store.

## Bạn viết API FastAPI cho model. Những gì không được thiếu?

- Schema Pydantic có ràng buộc nghiệp vụ, chỉ chứa feature có sẵn ở thời điểm dự đoán; sai thì 422
  trước khi tới model.
- Model nạp **một lần** lúc khởi động (từ registry theo alias), không nạp trong mỗi request.
- Endpoint nhận batch, gọi model một lần cho cả batch.
- Response có `model_version`; log request, score, độ trễ để monitoring và debug.
- `/health` (và `/ready` nếu nạp model lâu).
- Ngưỡng là cấu hình, không cứng trong code.
- Test bằng `TestClient` với model giả để kiểm cách gọi, và với model thật để kiểm parity.

Phần Docker, CI/CD, autoscale thường thuộc đội platform; DS nên viết được bản tối thiểu chạy được
và test được.

## PSI là gì? Tính thế nào, đọc thế nào, và có những bẫy gì?

PSI so phân phối hiện tại với reference qua các bin (thường theo quantile của reference):

$$
\mathrm{PSI} = \sum_i (a_i - e_i)\ln\frac{a_i}{e_i}
$$

Quy ước: dưới 0.1 ổn định, 0.1 tới 0.25 trôi vừa, từ 0.25 trôi lớn. Bẫy:

- Con số phụ thuộc cách chia bin, số bin, cách xử lý bin rỗng (`eps`), nên ngưỡng chỉ có nghĩa đi
  kèm một cách tính cố định.
- Biên ngoài cùng phải mở ra vô cực, nếu không giá trị ngoài khoảng train biến mất khỏi phép đếm.
- PSI đơn biến không thấy drift ở tương quan giữa các feature.
- PSI lớn không có nghĩa model kém đi; phải xem feature đó quan trọng cỡ nào với model và hiệu năng
  theo segment khi nhãn về.

## Vì sao không dùng p-value của KS test làm cảnh báo drift?

Với hàng chục nghìn dòng, KS test phát hiện được cả khác biệt rất nhỏ. Trên Olist, `delay_days`
giữa train và test có KS p-value cỡ 5e-99 trong khi PSI chỉ 0.073 và thống kê KS 0.0785: khác biệt
"có ý nghĩa thống kê" nhưng không đáng đánh thức ai. Cảnh báo theo p-value sẽ kêu mỗi ngày và bị
tắt. Dùng **độ lớn** (PSI, thống kê KS, Wasserstein) với ngưỡng hiệu chỉnh trên lịch sử. Đây là
cùng bài học "statistical vs practical significance" của A/B testing.

## Data drift, concept drift, và label shift khác nhau thế nào?

- **Data drift (covariate shift)**: phân phối feature $$P(X)$$ đổi, quan hệ $$P(Y \mid X)$$ giữ nguyên.
  Ví dụ Olist rút ngắn ngày hẹn giao: `promised_days` trôi.
- **Concept drift**: $$P(Y \mid X)$$ đổi. Cùng một đơn trễ 3 ngày nhưng khách bớt khó chịu vì đã được
  nhắn tin trước. Model sai thật, cần retrain.
- **Label shift (prior shift)**: $$P(Y)$$ đổi (tỉ lệ review xấu giảm), thường kéo theo calibration lệch.

Thêm **mix shift**: tổ hợp các segment đổi làm metric toàn cục đổi dù model trong từng segment như
cũ. Trên Olist, AUC 0.799 ở validation xuống 0.696 ở test, nhưng AUC trong nhóm đơn trễ là 0.738 và
0.741: cái đổi là tỉ lệ đơn trễ (14.4% so với 5.9%).

## Nhãn của bạn về sau 90 ngày. Monitor hiệu năng model thế nào?

- Tín hiệu sớm: drift của feature quan trọng và của score; tỉ lệ vượt ngưỡng; dữ liệu thiếu.
- Proxy label: hành vi sớm có tương quan với nhãn (với churn: số lần đăng nhập 14 ngày đầu).
- Đánh giá theo cohort: khi nhãn của cohort tháng 1 về, tính AUC, calibration cho cohort đó; báo cáo
  hiệu năng luôn trễ một khoảng bằng độ trễ của nhãn, và nói rõ điều đó.
- Một nhóm holdout nhỏ không áp model (nếu model gây can thiệp) để đo được tác động thật.

Với review của Olist, độ trễ nhỏ (trung vị khoảng 2 ngày sau giao), nhưng câu trả lời nên bao quát
trường hợp xấu.

## ONNX là gì, và khi nào bạn khuyên dùng?

ONNX là định dạng mở mô tả model như một graph phép toán; `onnxruntime` (C++) chạy graph đó từ Python,
C, C++, C#, Java, JavaScript, và qua C API từ Go, Rust. Dùng khi:

- Service gọi model viết bằng Go/Rust/C++/Java và cần độ trễ thấp, không muốn thêm một service
  Python.
- Model chạy trên thiết bị (mobile, trình duyệt, edge).

Không nên khi feature cần logic Python phức tạp phải viết lại ở phía gọi (sinh skew), hoặc khi độ
trễ không phải vấn đề. Luôn kèm kiểm parity: trên pipeline của module, xác suất ONNX lệch scikit-learn
khoảng 1e-7; model cây có thể rẽ nhánh khác ở vài điểm vì `float32`. Chấm một dòng nhanh hơn nhiều
(khoảng 3 ms so với 0.02 ms) chủ yếu vì loại được chi phí cố định của Python, không phải vì phép tính
nhanh hơn.

## Retrain bao lâu một lần? Retrain tự động có nên không?

Không có con số chung. Căn cứ: tốc độ thế giới đổi (đo bằng hiệu năng theo thời gian trên dữ liệu
lịch sử, ví dụ train trên tháng t, đo trên t+1, t+2…), chi phí retrain và phát hành, độ trễ nhãn.
Phổ biến: retrain theo lịch (tuần, tháng, quý) **cộng** retrain sớm khi hiệu năng theo segment giảm
quá ngưỡng.

Retrain tự động được, **promote** tự động thì cần quy tắc chặt: model mới phải qua cùng bộ kiểm như
model đầu tiên (validation theo thời gian, so với champion, parity, latency) và tốt nhất qua shadow.
Retrain chỉ vì cảnh báo drift là sai: tháng 6/2018 của Olist có PSI `delay_days` 0.65 vì gần như
không đơn nào trễ; model train lại trên tháng đó sẽ kém đi khi đơn trễ quay lại.

## Case: Sau khi deploy, AUC trên dashboard giảm từ 0.80 xuống 0.70 trong hai tháng. PM hỏi model có hỏng không. Bạn làm gì?

Đừng trả lời ngay. Trình tự:

1. **Kiểm dữ liệu và pipeline trước**: tỉ lệ thiếu, giá trị lạ, schema upstream đổi, nhãn có bị
   tính sai (review chưa về được tính là "không xấu"?). Phần lớn "model hỏng" là dữ liệu hỏng.
2. **So cùng một thứ**: AUC 0.80 đo trên tập nào? Nếu là validation lúc phát triển thì hai giai đoạn
   có tổ hợp khác nhau.
3. **Tách theo segment**: AUC trong nhóm đơn trễ và đơn đúng hẹn. Trên Olist, AUC toàn cục từ 0.799
   xuống 0.696 nhưng trong từng nhóm gần như không đổi: tỉ lệ đơn trễ giảm từ 14.4% xuống 5.9%, bài
   toán khó hơn chứ model không tệ đi.
4. **Xem calibration và metric kinh doanh**: ở ngưỡng đang dùng, precision và số khách được liên hệ
   có đổi không? Đó mới là thứ đội CSKH cảm nhận.
5. Kết luận với PM bằng ngôn ngữ của họ: "Model vẫn xếp hạng đơn tốt như trước trong từng nhóm; số
   đơn trễ ít đi nên ít đơn rủi ro rõ ràng hơn. Không cần retrain gấp; tôi đề xuất báo cáo AUC theo
   nhóm thay cho một con số."

Nếu AUC trong segment cũng giảm: concept drift, chuẩn bị retrain với dữ liệu mới qua quy trình
promote.

## Case: Đội CSKH muốn dùng model review xấu để nhắn tin cho khách **trước** khi đơn giao. Bạn trả lời thế nào?

Không dùng được model hiện tại. Nó được train với thời điểm dự đoán "lúc đơn vừa giao xong", và hai
feature mạnh nhất (`delivery_days`, `delay_days`) chỉ có sau khi giao. Gọi nó cho đơn chưa giao thì
hoặc phải đoán giá trị hai feature đó (dự đoán dựa trên dự đoán), hoặc để trống (model chưa từng
thấy). Không có lỗi nào được báo, chỉ có dự đoán sai.

Đề xuất: một model mới với thời điểm dự đoán là lúc mua hoặc lúc giao cho hãng vận chuyển; feature
chỉ gồm thông tin có lúc đó (ngày hẹn, khoảng cách, seller, lịch sử trễ của seller tính tới thời
điểm đó, phí vận chuyển), không có kết quả giao hàng. Nhãn có thể là "giao trễ" (8.1% đơn giao xong)
hoặc trực tiếp "review xấu". Rồi đo tác động của việc nhắn tin bằng A/B test (module 03), vì model
chỉ nói ai có nguy cơ, không nói nhắn tin có giúp không. Schema API của model mới chỉ nhận feature
lúc mua để khoá việc dùng sai.

## Case: Đội backend viết dịch vụ đơn hàng bằng Go, muốn gọi model trong vòng 5 ms p99. Bạn đề xuất kiến trúc nào?

Ba phương án, chọn theo ràng buộc:

| Phương án | p99 điển hình | Vận hành | Rủi ro |
| --- | --- | --- | --- |
| Service Python (FastAPI) qua mạng | Vài ms tới chục ms, cộng mạng | Thêm một service, autoscale, on-call | Khó đạt 5 ms ổn định |
| ONNX nhúng trong service Go | Dưới 1 ms cho model tuyến tính, cây nhỏ | Không có service mới; cập nhật tệp model | Feature ngoài graph phải viết lại ở Go (skew) |
| Tính sẵn theo batch, Go tra cứu | Thời gian một lần tra cache | Job batch + key-value store | Chỉ dùng được khi feature không đổi trong ngày |

Với model review xấu (feature đều có trong request, pipeline xuất được), ONNX nhúng là hợp lý.
Điều kiện đi kèm: hợp đồng input theo tên cột, quy tắc điền thiếu ghi rõ, tệp `.onnx` và hợp đồng
version cùng nhau trong registry, tập golden để cả Python lẫn Go kiểm parity trong CI, và log score
từ phía Go để monitoring vẫn chạy. Nếu sau này model cần feature lịch sử phức tạp, cân nhắc lại
phương án lai: feature tính sẵn trong store, model nhúng trong Go.

## Case: Bạn có challenger tốt hơn champion 0.01 AUC offline. Đưa nó ra production thế nào?

1. **Offline đúng cách**: cùng tập test theo thời gian, khoảng tin cậy bootstrap cho chênh lệch AUC
   (0.01 có thể là nhiễu), so theo segment, kiểm latency và kích thước.
2. **Shadow**: challenger chấm mọi request nhưng không hành động. Đo `flip_rate` (bao nhiêu khách sẽ
   được xử lý khác), PSI giữa score hai model, latency; đợi nhãn về để so AUC trên dữ liệu thật. Tính
   thời lượng từ số nhãn cần và độ trễ của nhãn.
3. **Quy tắc promote viết trước**: đủ nhãn, AUC tăng ít nhất X, p95 latency dưới SLA, `flip_rate` cao
   thì cần người duyệt.
4. **Canary / A/B**: challenger quyết định cho 10% khách (random theo khách). Đây là nơi đo tác động
   kinh doanh, thứ shadow không đo được.
5. **Promote bằng alias**, giữ `previous_champion`, viết sẵn điều kiện rollback.

Bẫy: promote ngay vì "offline tốt hơn"; quên rằng 0.01 AUC có thể đổi danh sách khách được liên hệ
rất nhiều; không có đường rollback.
