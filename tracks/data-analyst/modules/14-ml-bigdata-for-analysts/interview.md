# Câu hỏi phỏng vấn: ML & Big Data cho DA

## Supervised, unsupervised và reinforcement learning khác nhau thế nào? Cho một ví dụ DA gặp ở mỗi loại.

- **Supervised**: học từ dữ liệu có nhãn đúng để đoán nhãn cho dữ liệu mới. Classification khi nhãn là nhóm (khách rời
  hay ở lại), regression khi nhãn là số (doanh số tuần sau). DA gặp nhiều nhất: chấm điểm rủi ro churn để chọn danh sách gọi.
- **Unsupervised**: không có nhãn, tìm cấu trúc trong dữ liệu: phân cụm (k-means chia khách theo RFM), phát hiện bất
  thường, giảm chiều. DA dùng để phân khúc và khám phá.
- **Reinforcement**: agent chọn hành động, nhận phần thưởng, học chính sách tối đa phần thưởng dài hạn. DA hiếm khi xây,
  nhưng gặp dạng đơn giản nhất là **multi-armed bandit** (thử nhiều phiên bản, dồn lưu lượng về phiên bản thắng), và việc
  của DA là đo kết quả.

Tôi thêm một câu: loại bài toán do **câu hỏi và dữ liệu có nhãn hay không** quyết định, không do thuật toán. "Chia khách
thành nhóm rời / không rời" nghe như phân cụm nhưng là supervised vì có nhãn churn.

## Khi nào DA không nên làm ML?

Khi một trong các điều sau đúng:

1. Câu hỏi là **"vì sao"** hoặc **"nếu làm X thì sao"**: cần phân tích chẩn đoán hoặc thí nghiệm, không phải model dự đoán.
2. Không có **quyết định** nào thay đổi theo dự đoán, hoặc không ai vận hành model sau khi bàn giao.
3. Một **quy tắc 1–2 dòng** đã gần bằng model. Trên Telco, quy tắc "month-to-month và gắn bó tối đa 12 tháng" gắn cờ 28.3%
   khách và phủ 54.8% khách rời; logistic regression ở cùng cỡ danh sách phủ khoảng 66%. Đáng hay không là bài toán tiền.
4. **Nhãn không đáng tin** hoặc dữ liệu cần lúc dự đoán không có sẵn (thời tiết thực tế so với dự báo).
5. Dữ liệu quá ít so với số cột, hoặc chi phí sai lớn mà model không giải thích được (tín dụng, y tế cần quy định).

Khi đó tôi đề xuất bảng SQL, quy tắc trong dashboard, hoặc thiết kế thí nghiệm, và nói rõ điều kiện để quay lại ML.

## Vendor báo model churn "đúng 97%". Bạn hỏi gì?

Năm câu, theo thứ tự:

1. **Baseline là bao nhiêu?** Trên nhóm hợp đồng hai năm của Telco chỉ 2.8% rời, "luôn đoán ở lại" đã đúng 97.2%.
2. **Precision và recall ở ngưỡng sẽ dùng**: trong số khách được gọi bao nhiêu thật sự sắp rời, và bắt được bao nhiêu phần
   trăm khách rời.
3. **Đo trên dữ liệu nào**: tập test chưa dùng khi học, chia theo thời gian nếu model dùng cho tháng sau.
4. **Có leakage không**: cột nào chỉ có giá trị sau khi khách rời (tổng cước chốt, cuộc gọi huỷ dịch vụ).
5. **Trên dữ liệu của chúng tôi**, trong một pilot có nhóm đối chứng, con số còn bao nhiêu.

Accuracy là con số sai để mở đầu cuộc nói chuyện; tôi xin bảng lift theo decile hoặc confusion matrix ở ngưỡng vận hành.

## Giải thích precision và recall cho một trưởng nhóm CSKH.

"Đội anh/chị gọi 400 khách mỗi tuần. **Precision** là trong 400 cuộc đó, bao nhiêu cuộc trúng khách thật sự sắp rời: đo
hiệu quả mỗi cuộc gọi. **Recall** là trong tất cả khách sắp rời, bao nhiêu người được gọi: đo độ phủ. Gọi ít khách điểm
rất cao thì precision cao, recall thấp; gọi rộng thì ngược lại."

Ví dụ thật: logistic regression trên Telco, ngưỡng 0.7 gắn cờ 116 khách, precision 78% nhưng recall 19.5%; ngưỡng 0.3 gắn
cờ 680, precision 53%, recall 77.5%. Chọn ngưỡng nào phụ thuộc số cuộc gọi đội làm được và giá trị một khách giữ được,
không phụ thuộc thói quen 0.5.

## Đọc hệ số logistic regression cho business thế nào?

Đổi hệ số thành **odds ratio** (e mũ hệ số) và nói theo nhóm tham chiếu, "cùng các yếu tố khác":

$$
\text{OR} = e^{\beta}, \qquad \text{thay đổi odds} = (\text{OR} - 1) \times 100\%
$$

Trên Telco: hợp đồng hai năm OR 0.25 (khoảng tin cậy 0.17–0.37): "so với month-to-month, odds rời thấp hơn khoảng 75%".
Mỗi năm gắn bó OR 0.68: "mỗi năm, odds giảm khoảng 32%"; hai năm là 0.68 bình phương, giảm 53%, không phải 64%.

Ba lưu ý tôi luôn nói kèm: odds ratio không phải tỉ số xác suất khi tỉ lệ cao; hệ số là tương quan có điều kiện, không
phải nguyên nhân; và để đọc hệ số tôi dùng model không regularization (statsmodels), vì `LogisticRegression()` mặc định
của scikit-learn co hệ số về 0.

## Decision tree, Naive Bayes, KNN, logistic regression: chọn cái nào khi nào?

| Thuật toán | Chọn khi | Tránh khi |
| --- | --- | --- |
| Logistic regression | Cần xác suất và hệ số giải thích, dữ liệu bảng ít cột; luôn là baseline đầu tiên | Quan hệ phi tuyến mạnh mà không muốn tự tạo đặc trưng |
| Decision tree nông | Stakeholder cần luật đọc được, viết lại thành SQL `CASE WHEN` | Cần độ chính xác cao (cây sâu overfit, cây nông kém) |
| Naive Bayes | Văn bản (đếm từ), cần baseline rất nhanh, ít nhãn | Cần xác suất đáng tin (thường quá tự tin) |
| KNN | Bài toán "tìm khách giống khách này", dữ liệu nhỏ, đã scale | Dữ liệu lớn, nhiều cột, cần giải thích |

Trên Telco, ở cùng 10 đặc trưng, logistic regression xếp hạng tốt nhất (ROC-AUC 0.841), KNN 0.826, Naive Bayes 0.824,
cây sâu 5 0.821, cây sâu 3 0.803. Cây sâu 3 kém hơn nhưng cho một câu nói được trong họp: "khách gắn bó dưới khoảng 10
tháng dùng cáp quang là nhóm rủi ro cao nhất". Thực tế tôi thường dùng hai model: một để giải thích, một để xếp hạng.

## Accuracy lừa khi nào? Cho ví dụ số.

Khi lớp không cân bằng và khi hai loại sai có giá khác nhau. Telco có 26.5% rời bỏ, nên "luôn đoán ở lại" đúng 73.5%.
Decision tree sâu 3 đạt 77.7%, chỉ hơn 4 điểm, và ở ngưỡng mặc định chỉ bắt 141 trong 467 khách rời (30%). Hạ ngưỡng
logistic regression từ 0.5 xuống 0.3 làm accuracy **giảm** từ 79.2% xuống 76.0% nhưng bắt thêm 119 khách rời. Nếu một khách
giữ được đáng hơn vài cuộc gọi nhầm, ngưỡng accuracy thấp hơn lại tốt hơn cho business.

## Case study: Head of CRM muốn "dùng AI chia khách thành nhóm". Bạn làm gì?

1. **Làm rõ quyết định**: chia nhóm để làm gì, bao nhiêu chương trình CRM làm được (3–5), kênh nào, ngân sách.
2. **Bắt đầu đơn giản**: RFM (recency, frequency, monetary) theo định nghĩa doanh thu chung. Thử quy tắc ngũ phân vị trước.
3. **K-means nếu cần**: `log1p` rồi chuẩn hoá (không đổi thang thì k-means trên Online Retail cho cụm cỡ 4 300 / 5 / 31 / 2,
   vô dụng); chọn k theo cả silhouette và số chương trình; k = 4 trên Online Retail cho Champions (16% khách, 65% doanh
   thu), At risk (27%, 24%), New / promising (19%, 5%), Hibernating (37%, 6%).
4. **Đặt tên bằng quy tắc** so median cụm với median chung, để ai cũng kiểm được.
5. **Kiểm ổn định** (đổi seed: 99.4% khách giữ tên) và cách gán khách mới (lưu tham số đổi thang và tâm cụm).
6. **Giao kèm đề xuất hành động** và cách đo bằng nhóm đối chứng.

## K-means có điểm yếu gì? Silhouette cao nhất có phải k tốt nhất?

Điểm yếu: phải chọn k; nhạy với thang đo và outlier; giả định cụm tròn, cỡ tương đương; luôn trả k cụm kể cả khi không có
cụm thật; kết quả phụ thuộc khởi tạo (dùng `n_init`).

Silhouette đo độ tách bạch, không đo độ hữu ích. Trên RFM Online Retail silhouette cao nhất ở k = 2 (0.434): "khách tốt /
còn lại", điều CRM đã biết. k = 3 và 4 gần nhau (0.338, 0.336), nên tôi chọn theo số chương trình CRM vận hành được và
kiểm mỗi cụm đủ lớn, khác nhau về hành động.

## Case study: vendor đề xuất Deep Learning cho dự báo churn trên bảng 7 000 khách. Bạn trả lời thế nào?

Tôi không từ chối ngay, mà yêu cầu so trên cùng tập test với hai baseline: quy tắc nghiệp vụ và logistic regression. Kinh
nghiệm và bằng chứng: trên bảng dữ liệu kinh doanh nhỏ, deep learning hiếm khi thắng; trên Telco, một MLP hai lớp ẩn đạt
ROC-AUC 0.828, thấp hơn logistic regression 0.841. Deep learning mạnh khi dữ liệu có cấu trúc mà mạng khai thác được: ảnh
(CNN), văn bản và chuỗi (Transformer, RNN), và khi có rất nhiều dữ liệu. Với bảng, thứ tự hợp lý là quy tắc → logistic
regression / cây → gradient boosting.

## CNN, RNN, Transformer: giải thích cho người không làm ML, và DA dùng chúng ở đâu?

- **CNN**: những bộ lọc nhỏ quét qua ảnh, học từ cạnh tới hình dạng tới vật thể. Dùng cho **image recognition**: phân loại
  ảnh sản phẩm, đọc hoá đơn, kiểm hàng lỗi.
- **RNN / LSTM**: đọc chuỗi lần lượt từng bước và giữ "trí nhớ". Từng là chuẩn cho văn bản và chuỗi thời gian.
- **Transformer**: mỗi từ "nhìn" mọi từ khác cùng lúc (attention), học song song được trên dữ liệu rất lớn. Là nền của LLM
  và NLP hiện đại.

DA hiếm khi train chúng từ đầu, nhưng hay **dùng** model pre-trained hoặc LLM: phân loại phản hồi khách theo chủ đề, chấm
sentiment, trích thông tin từ ticket, embeddings để tìm sản phẩm giống nhau. Việc của DA là kiểm chất lượng trên một mẫu
gán nhãn tay và không gửi dữ liệu nhạy cảm ra API ngoài khi chưa được phép.

## Vì sao chọn scikit-learn/statsmodels thay vì AutoML hay Power BI Key Influencers cho một phân tích churn?

Vì tôi cần **kiểm soát và giải thích được**: chọn cách chia train/test giống cách dùng thật, kiểm leakage, so với baseline,
đọc hệ số kèm khoảng tin cậy, và để người khác chạy lại notebook ra cùng con số. Key Influencers trong Power BI tiện để
khám phá trên dashboard nhưng không đánh giá trên test và dễ bị đọc như nhân quả. AutoML hữu ích khi đã chắc bài toán đáng
làm và cần model mạnh nhanh, nhưng dễ che mất baseline và leakage. Nếu dữ liệu nằm trong BigQuery/Snowflake và model cần chạy
định kỳ, tôi cân nhắc SQL ML (BigQuery ML) để không kéo dữ liệu ra ngoài. Công cụ chọn theo câu hỏi, nơi dữ liệu nằm, và ai
sẽ vận hành.

## Big Data là gì? Khi nào dữ liệu của bạn thật sự "lớn"?

Big Data là dữ liệu mà công cụ một máy không xử lý kịp trong thời gian chấp nhận được, thường mô tả bằng các chữ V: volume,
velocity, variety, veracity, value. Ngưỡng thay đổi theo phần cứng: một laptop 16 GB với DuckDB/Polars xử lý hàng trăm
triệu dòng Parquet. Online Retail II (khoảng 1 triệu dòng) chiếm khoảng 60 MB trong RAM: nhỏ.

Trước khi nói "cần Spark", tôi đổi thành con số: bao nhiêu dòng, bao nhiêu GB sau nén, định dạng gì, nằm ở đâu, chạy bao lâu
một lần. Thường câu trả lời là: đổi CSV sang Parquet, chỉ đọc cột cần, tổng hợp trên warehouse rồi mới kéo về.

## MapReduce hoạt động thế nào? Vì sao trung bình và median khó trong hệ phân tán?

Ba bước: **map** (mỗi máy xử lý khối của nó, phát cặp khoá–giá trị), **shuffle** (gom cặp cùng khoá về một máy, đắt nhất vì
đi qua mạng), **reduce** (gộp giá trị của mỗi khoá). Phép gộp phải cộng dồn được: sum, count, min, max.

Trung bình không cộng dồn được, nhưng (tổng, đếm) thì được: map trả cặp đó, reduce cộng rồi mới chia. Lấy trung bình của các
trung bình từng khối là sai khi các khối khác cỡ. Median cần thứ tự của mọi giá trị, không có kết quả từng phần nhỏ nào gộp
lại ra median chính xác, nên hệ phân tán dùng hàm xấp xỉ (`approx_percentile`) hoặc trả giá bằng shuffle lớn.

Tôi từng tự làm MapReduce bằng `multiprocessing` cho doanh thu theo nước trên Online Retail II: kết quả khớp `groupby` tới
phần tỉ GBP (chỉ khác thứ tự cộng số thực), nhưng chạy song song chậm hơn `groupby` vì chi phí tạo tiến trình và gửi dữ liệu.

## Hadoop, Spark, MPI khác nhau thế nào? DA cần biết tới đâu?

- **Hadoop**: HDFS lưu tệp chia block nhân bản trên nhiều máy, YARN cấp tài nguyên, MapReduce tính, ghi trung gian xuống
  đĩa nên chậm với việc nhiều bước. Hive cho viết SQL trên đó. Còn trong hệ thống cũ.
- **Spark**: giữ dữ liệu trung gian trong bộ nhớ, tối ưu cả chuỗi phép tính, có DataFrame và Spark SQL. Thay MapReduce trong
  hầu hết hệ thống mới, chạy trên YARN, Kubernetes, Databricks.
- **MPI**: chuẩn gửi nhận thông điệp giữa tiến trình (send, recv, allreduce), dùng trong HPC và huấn luyện deep learning phân
  tán (cộng gradient giữa GPU). Không tự chịu lỗi, không tự chia dữ liệu.

DA cần: viết Spark SQL / Databricks SQL như SQL thường, hiểu vì sao query chậm (quét nhiều, shuffle, skew khi một khoá quá
lớn), biết khi nào yêu cầu là việc của DE. DA gần như không viết MPI hay MapReduce thủ công.

## Case study: data platform muốn chuyển báo cáo doanh thu 1 triệu dòng sang Spark "vì sẽ lớn". Bạn góp ý gì?

1. **Đo hiện trạng**: báo cáo chạy bao lâu, tốn bao nhiêu, dữ liệu tăng bao nhiêu mỗi năm. 1 triệu dòng chạy dưới một giây
   trên pandas/DuckDB.
2. **Chi phí của Spark**: khởi động cụm, chi phí cụm, kỹ năng đội, debug khó hơn. Với dữ liệu nhỏ Spark chậm hơn.
3. **Ngưỡng chuyển**: khi dữ liệu đã nằm trong lakehouse dùng Spark, khi một máy không còn đọc kịp lịch chạy, hoặc khi pipeline
   phía trước đã là Spark. Ghi ngưỡng đó thành số (ví dụ trên 100 GB Parquet hoặc báo cáo chạy quá 30 phút).
4. **Trong lúc chờ**: viết logic bằng SQL chuẩn để khi chuyển chỉ đổi engine, không viết lại định nghĩa metric.

## Case study: Ops muốn mua model ML dự báo nhu cầu theo giờ. Bạn đánh giá thế nào?

Trên Bike Sharing (học trước 01/10/2012, đo quý 4/2012): bảng trung bình theo (ngày làm việc, giờ) có MAE khoảng 80 lượt/giờ
trên mức trung bình 219. Gradient boosting chỉ dùng lịch không hơn baseline (khoảng 88); thêm thời tiết **đo thực tế** thì
giảm còn khoảng 44. Câu hỏi quyết định không phải "model tốt không" mà là "lúc lên lịch tối hôm trước có dữ liệu gì":
chỉ có dự báo thời tiết, nên phải đo lại model với thời tiết kém chính xác hơn trước khi tin con số "giảm một nửa". Tôi
cũng kiểm ngày bất thường (29–30/10/2012 gần như không có dữ liệu, bão Sandy) và đề xuất chạy song song model với baseline vài
tuần, quyết định theo sai số ở giờ cao điểm, nơi điều phối sai tốn nhất.
