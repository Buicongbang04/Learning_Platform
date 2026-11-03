# Câu hỏi phỏng vấn: drift, nhãn về muộn và xử lý sự cố

## Phân biệt data drift, prediction drift và concept drift. Cái nào nguy hiểm nhất và vì sao?

Data drift (covariate shift) là $$P(X)$$ đổi; prediction drift là $$P(\hat{y})$$ đổi; concept drift là $$P(y \mid X)$$ đổi. Concept drift nguy hiểm nhất vì kiến thức model đã học thành sai ngay cả khi đầu vào trông quen, và nó thường không hiện trên
phân phối feature. Ví dụ thật: model ETA học trên taxi New York trước lockdown, sang tháng 4/2020 PSI cao nhất chỉ khoảng 0.15 nhưng MAE tăng gần 60%. Data drift thì hay vô hại: tháng lễ có nhiều chuyến khác loại nhưng model vẫn đúng ở chỗ nó đã học.
Prediction drift là proxy sớm, dùng được khi chưa có nhãn.

## Drift có nghĩa là phải retrain không? Bạn quyết định thế nào?

Không. Drift là tín hiệu để điều tra, không phải lệnh hành động. Tôi dùng bốn bước: detect (tín hiệu và độ tin của chính giám sát), verify (loại trừ lỗi dữ liệu hay pipeline), impact (chất lượng có xấu đi không, bằng nhãn đã về hoặc proxy),
decide (`keep`, `rollback` hoặc `retrain`). `keep` khi drift lớn mà MAE không xấu đi; `rollback` khi vấn đề bắt đầu cùng một thay đổi gần đây và có bản trước tốt hơn đã đo trên cùng lưu lượng; `retrain` khi chất lượng giảm thật mà không có bản trước nào tốt hơn.
Retrain theo phản xạ tốn tiền, có thể làm model tệ đi (train trên một tuần bất thường) và che nguyên nhân thật.

## Sự cố: dashboard báo drift mạnh từ hôm qua, không ai báo có thay đổi nào. Bạn làm gì trong giờ đầu?

Không đụng model trước. (1) Xác nhận tín hiệu thật: kiểm chính giám sát (cỡ mẫu, baseline cùng thứ, ngưỡng có vừa đổi không). (2) Xem phạm vi: một cột hay nhiều cột, cột nào, và các cột phụ thuộc vào nó có đổi cùng không. (3) Tìm điểm gãy: đột ngột trong một đêm
hay trôi dần; đột ngột gợi thay đổi hệ thống. (4) Loại trừ lỗi dữ liệu và pipeline: deploy, thay đổi nguồn hay lược đồ trong 48 giờ, tỉ lệ thiếu, khoảng giá trị của cột. (5) Chỉ sau đó xem MAE trên nhãn đã về và proxy để biết có thiệt hại không.
Mỗi bước loại một giả thuyết và tốn ít hơn bước sau. Kết thúc bằng việc sửa nguyên nhân (nguồn, rào kiểm), không phải bằng retrain.

## Vì sao p-value của KS test không dùng được làm ngưỡng cảnh báo khi mẫu lớn?

Với $$n$$ hàng trăm nghìn, KS phát hiện được độ lệch cực nhỏ: hai tập lệch 0.03 độ lệch chuẩn trên 200 000 dòng cho p-value dưới 0.001 dù tác động thực tế bằng không. p-value trả lời "chắc không chắc là khác", không trả lời "khác bao nhiêu".
Dùng thước đo độ lớn (PSI, Wasserstein, AUC của classifier phân biệt hai tập) với ngưỡng rút ra từ dữ liệu ngày bình thường, và gắn với tác động lên chất lượng.

## PSI phụ thuộc những lựa chọn nào? Hai công cụ có thể cho hai số khác nhau không?

Có. PSI phụ thuộc cách chia bin (quantile của reference hay bin rộng bằng nhau trên cả hai tập, số bin), cách xử lý bin rỗng và NaN. Trên cùng dữ liệu TLC, `fare_amount` cho 0.050 với bin quantile và khoảng 0.005 với bin rộng bằng nhau của Evidently.
Vì vậy ngưỡng 0.1 và 0.25 chỉ có nghĩa với một cách tính cụ thể; tôi ghi cách chia bin vào tài liệu giám sát và đừng so số của hai công cụ.

## Drift đa biến là gì và bắt nó bằng cách nào?

Quan hệ giữa các cột đổi mà phân phối biên từng cột giữ nguyên (vd. tương quan giữa cự ly và giá cước đổi dấu); PSI từng cột bỏ sót. Cách phổ biến: gộp hai tập, gán nhãn tham chiếu 0 và hiện tại 1, huấn luyện classifier (rừng ngẫu nhiên, gradient boosting)
và đo AUC bằng cross-validation. AUC gần 0.5 nghĩa là không phân biệt được; cao nghĩa là khác. Importance của classifier chỉ ra cột đóng góp. Đánh đổi: nhạy với cả khác biệt vô hại, tốn một lần fit, và AUC cao không có nghĩa chất lượng giảm.

## Nhãn về sau 14 ngày. Bạn giám sát chất lượng model thế nào trong lúc chờ?

Hai tầng. Tầng nhanh dùng proxy: phân phối dự đoán so với baseline *cùng thứ trong tuần* (để loại mùa vụ), tỉ lệ fallback và timeout, tỉ lệ thiếu và khoảng giá trị feature, shadow model hay bản trước nếu có. Tầng chậm dùng nhãn: MAE trên phần đã về, tính đúng theo thời điểm
nhãn về (không dùng nhãn tương lai khi phát lại lịch sử). Proxy cho cảnh báo sớm nhưng độ tin vừa; chỉ nhãn mới xác nhận chất lượng, nên quyết định lớn (retrain, rollback không rõ nguyên nhân) chờ nhãn nếu chi phí chờ thấp. Có thể dùng phương pháp ước lượng hiệu năng không cần nhãn như CBPE của NannyML, kèm cảnh báo về giả định.

## Vì sao so dự đoán hôm nay với hôm qua là baseline tồi?

Dữ liệu thật có chu kỳ tuần: thứ Hai khác Chủ nhật. So với hôm qua thì mỗi cuối tuần và mỗi thứ Hai đều báo động giả, đội học cách phớt lờ cảnh báo (alert fatigue). So với bốn ngày cùng thứ gần nhất loại được chu kỳ tuần mà vẫn theo kịp xu hướng; sự kiện không có tiền lệ (Tết, Black Friday) vẫn báo,
nên cần lịch sự kiện hoặc cùng kỳ năm trước. Ngưỡng nên đặt bằng ngân sách báo động giả (vd. tối đa một lần mỗi tuần trên dữ liệu bình thường).

## Khi nào rollback tốt hơn retrain?

Rollback hợp khi vấn đề bắt đầu ngay sau một thay đổi (deploy phiên bản mới, đổi feature) và có phiên bản trước đã biết tốt hơn trên cùng lưu lượng, tốt nhất là shadow đo trực tiếp. Nó nhanh (đổi alias trong registry) và ít rủi ro. Nhưng rollback chỉ chữa triệu chứng, nên đi kèm postmortem
về cách bản mới qua được cổng kiểm. Retrain hợp khi chất lượng giảm vì thế giới đổi bền vững và không bản nào tốt hơn (ví dụ sau cú sốc COVID, mọi bản huấn luyện trước đó đều sai như nhau); rollback ở đó vô ích.

## Bạn retrain sau khi thế giới thay đổi đột ngột (như lockdown). Những cạm bẫy nào?

Dữ liệu giai đoạn bất thường ngắn và lệch, dễ quá khớp, và khi thế giới quay lại bình thường model mới có thể tệ. Cách giảm rủi ro: chọn cửa sổ dữ liệu gần đây đủ dài cho tín hiệu, đánh giá trên holdout gần đây (không lẫn thời gian cũ), so challenger với champion, chạy shadow rồi promote theo bước,
giữ bản cũ để quay về, và đặt lịch huấn luyện lại thường xuyên thay vì chỉ khi sự cố. Cần cả cơ chế phát hiện lúc thế giới quay lại.

## Evidently, NannyML, WhyLabs hay Arize: bạn chọn gì và vì sao?

Tuỳ ràng buộc. Evidently (mã nguồn mở) khi đội tự vận hành, muốn chạy báo cáo và test ngay trong pipeline, không khoá nhà cung cấp; bù lại tự lo lưu trữ, lịch chạy và giao diện lâu dài. NannyML khi nhãn trễ nhiều tuần và cần ước lượng hiệu năng không có nhãn. WhyLabs hay Arize
(dịch vụ) khi có nhiều model, ít người vận hành và chấp nhận chi phí, dữ liệu rời khỏi hạ tầng, ràng buộc nhà cung cấp. Nếu đã có Prometheus và Grafana thì thêm vài metric drift cơ bản cũng là lựa chọn rẻ. Thước đo (PSI, cách chia bin, ngưỡng) quan trọng hơn thương hiệu công cụ.

## Hệ thống giám sát tốt phải tránh alert fatigue như thế nào?

Mỗi cảnh báo có người nhận, hành động đi kèm, và mức nghiêm trọng gắn với tác động (drift đơn lẻ là cấp thấp, drift cộng MAE xấu đi mới là cấp cao). Ngưỡng rút ra từ dữ liệu bình thường (baseline cùng thứ, ngân sách báo động giả). Gộp cảnh báo cùng nguyên nhân; dùng test tổ hợp
(vd. nhiều feature PSI vừa cộng AUC miền cao) thay vì bắn từng PSI. Một cảnh báo bắn giả lặp lại là nợ kỹ thuật cần sửa, không phải để tắt tiếng.

## Runbook tốt cho cảnh báo drift gồm những gì?

Viết cho người chưa từng thấy hệ thống: điều kiện kích hoạt và mức nghiêm trọng; các bước detect, verify, impact, decide, mỗi bước một câu hỏi có/không kèm hành động; ngưỡng truy được về dữ liệu bình thường; bảng quyết định giữ, rollback, retrain với người duyệt và cách kiểm sau đó;
mẫu cập nhật trạng thái và điều kiện leo thang; việc phải làm trong 48 giờ sau. Nhánh mặc định không được là retrain, và phải có hành động cụ thể cho lúc nhãn chưa về chứ không chỉ "chờ".

## Postmortem không đổ lỗi là gì? Hành động tốt khác hành động hình thức ở chỗ nào?

Postmortem không đổ lỗi hỏi "hệ thống nào đã để chuyện này xảy ra", không hỏi "ai làm sai": dòng thời gian bằng vai trò, nguyên nhân là chuỗi điểm hệ thống, mô tả điều mọi người biết lúc đó và các lựa chọn hợp lý tại thời điểm đó. Đổ lỗi khiến người ta giấu sự cố lần sau.
Hành động tốt có chủ sở hữu (vai trò), hạn, cách kiểm hoàn thành và trả lời được "nếu sự cố giống hệt xảy ra lại thì hành động này làm nó nhỏ hơn hay ngắn hơn ở chỗ nào". "Theo dõi sát hơn" hay "cẩn thận hơn" là hành động hình thức.

## Thiết kế hệ thống: đội có 20 model sản xuất, nhãn trễ từ vài giờ đến vài tuần. Thiết kế giám sát drift và quy trình quyết định.

Gồm ba lớp. (1) Thu thập: mọi dự đoán ghi `ts`, phiên bản model, feature, dự đoán, cờ fallback vào kho chung; nhãn ghép theo khoá khi về. (2) Phép đo theo model, cấu hình bằng khai báo: PSI hay Wasserstein từng feature với cách chia bin ghi rõ, tỉ lệ thiếu và khoảng giá trị,
phân phối dự đoán so với baseline cùng thứ, tỉ lệ fallback, AUC miền hằng tuần, MAE trên nhãn đã về (kèm độ trễ riêng của từng model). Chạy bằng job định kỳ (Evidently hoặc mã tự viết), lưu số đo lịch sử cho dashboard. Model nhãn trễ nhiều tuần cần ước lượng hiệu năng không nhãn hoặc proxy mạnh hơn.
(3) Quy trình: mức nghiêm trọng gắn tác động, runbook chung với nhánh quyết định giữ, rollback, retrain; rào dữ liệu ở cửa vào (schema, khoảng giá trị, so phân phối với các ngày trước) để lô lỗi bị chặn trước khi thành "drift"; registry có alias để rollback một lệnh; pipeline retrain kèm so champion và challenger; postmortem cho sự cố có ảnh hưởng.
Đo chính hệ thống giám sát: số cảnh báo giả mỗi tuần, thời gian từ sự cố tới phát hiện, tỉ lệ cảnh báo dẫn tới hành động.

## Nhìn lại một ca "drift lớn nhưng không cần làm gì" bạn từng gặp: bạn biết là vô hại bằng cách nào?

Câu trả lời tốt dẫn bằng chứng: PSI hay AUC miền lớn, nhưng MAE trên nhãn đã về (đủ phần trăm nhãn, đủ ngày) không xấu đi so với bốn tuần trước; dự đoán trung bình và tỉ lệ fallback không đổi; cùng kỳ năm trước có mẫu hình tương tự; không có deploy hay thay đổi nguồn. Sau đó họ giữ nguyên, ghi chú vào lịch,
đặt lại ngưỡng theo mùa, và đặt điều kiện đổi ý (vd. MAE xấu đi trên 15% hai ngày liên tiếp). Bằng chứng, không phải cảm giác, là thứ khiến "không làm gì" thành một quyết định chứ không phải bỏ sót.
