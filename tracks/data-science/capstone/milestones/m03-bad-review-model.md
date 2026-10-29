# M03: Model dự đoán đơn có nguy cơ review xấu

## Mục tiêu

Dựng model chấm điểm nguy cơ review 1–2 sao cho từng đơn **tại lúc giao cho đơn vị vận chuyển**, đánh
giá trung thực theo thời gian, đặt nó cạnh một luật không ML và cạnh model "lúc vừa giao" của module 11,
rồi chọn chính sách cảnh báo theo năng lực CSKH. Output của milestone là danh sách đơn được cảnh báo mà
M05 dùng làm tổng thể thí nghiệm và M06 đem đi serve.

**Vì sao thời điểm giao vận chuyển.** Can thiệp của capstone là nhắn tin chủ động **trước khi** đơn tới
tay khách (M05). Model của module 10/11/12 dự đoán lúc đơn vừa giao, dùng `delivery_days` và
`late_days`, hai feature mạnh nhất nhưng chỉ có **sau** khi giao: dùng chúng cho can thiệp trước khi giao
là leak. Lúc đặt hàng thì quá sớm (chưa biết seller xử lý nhanh hay chậm). Lúc giao vận chuyển có thêm
`handling_days` và số ngày còn lại tới ngày hẹn, mà khách vẫn còn trung vị khoảng 7 ngày nữa mới nhận
hàng. Giá phải trả: model yếu hơn rõ rệt so với model lúc vừa giao. Bạn sẽ đo cái giá đó.

## Việc cần làm

1. **Hợp đồng feature theo thời điểm** trong `project/src/olist_cx/features.py`: hàm
   `features_at(point)` trả danh sách cột hợp lệ cho `"purchase"`, `"carrier"`, `"delivered"`. Test
   rằng `"carrier"` không chứa cột nào biết sau `order_delivered_carrier_date` (ngày giao thực tế, trễ,
   số ngày trễ, mọi cột review).
2. **Bảng huấn luyện**: từ `orders_cx` (M01), đơn có review, nhãn `bad_review`, chia theo thời gian của
   định nghĩa dùng chung. Feature gợi ý lúc giao vận chuyển: `promised_days`, `handling_days`,
   `remaining_days` (từ lúc giao vận chuyển tới ngày hẹn), `same_state`, `log_price`, `log_freight`,
   `n_items`, `n_sellers`, `customer_state`, số kỳ trả góp. Nếu thêm feature lịch sử seller (tỉ lệ trễ,
   tỉ lệ review xấu quá khứ), tính **point-in-time** như bài
   `modules/10-feature-engineering/exercises/advanced/01-point-in-time-seller`: chỉ dùng đơn đã có nhãn
   chín trước thời điểm dự đoán.
3. **So sánh model** trên validation (logistic regression trong `Pipeline`, cây nông, random forest,
   gradient boosting / LightGBM), theo cách bài `modules/11-classic-ml/exercises/intermediate/01-olist-bad-review-models`:
   ROC-AUC, PR-AUC (so với tỉ lệ dương), log loss, Brier, train ROC-AUC để thấy overfitting.
4. **Ba mốc so sánh trên test** cho model tốt nhất:
   - cùng model ở thời điểm `"purchase"` (cận dưới),
   - cùng model ở thời điểm `"delivered"` (cận trên, không dùng được cho can thiệp trước khi giao),
   - luật không ML "còn dưới 5 ngày tới ngày hẹn lúc giao vận chuyển", so ở **cùng số đơn được chọn**.
5. **Calibration** (reliability curve, Brier) trên validation; hiệu chỉnh nếu cần. Giải thích vì sao
   PR-AUC và precision đổi mạnh giữa validation (18.0% review xấu) và test (10.4%).
6. **Chính sách cảnh báo**: dùng `capacity_threshold` và `bootstrap_saving` từ bài
   `modules/11-classic-ml/exercises/advanced/02-olist-contact-policy` (đổi giả định chi phí sang tin
   nhắn chủ động, ghi rõ). So "ngưỡng cố định chọn trên validation" với "top k mỗi tuần". Chọn ngưỡng
   trên **validation**, báo cáo trên **test**.
7. **Xuất tổng thể cho M05**: `artifacts/flagged.parquet` (đơn được cảnh báo trên test, điểm, nhãn, tuần)
   và một bảng nhỏ: số cảnh báo mỗi tuần, tỉ lệ review xấu trong nhóm được cảnh báo, tỉ lệ đơn trễ trong
   nhóm đó. Quay lại `EXPERIMENT_DESIGN.md` của M05, thay kịch bản giả định bằng các con số này và tính
   lại power.
8. **`reports/MODEL_CARD.md`**: mục đích và thời điểm dự đoán, dữ liệu và cách chia, feature, metric
   trên validation và test, so với luật và hai thời điểm khác, calibration, chính sách cảnh báo, giới
   hạn (chỉ đơn có review, drift giữa các giai đoạn), không dùng cho việc gì.

Số tham chiếu trên test (LightGBM 300 cây, learning rate 0.05, `min_child_samples=50`, 10 feature ở bước 2
trừ lịch sử seller; bản cài đặt của người soạn):

| Thời điểm | ROC-AUC | PR-AUC | Precision top 5% |
| --- | --- | --- | --- |
| Lúc đặt hàng | 0.578 | 0.173 | 0.282 |
| Lúc giao vận chuyển | 0.631 | 0.222 | 0.342 |
| Lúc vừa giao (thêm `delivery_days`, `late_days`) | 0.693 | 0.341 | 0.543 |

Tỉ lệ review xấu trên test là 10.4%. Luật "còn dưới 5 ngày" chọn 4.9% đơn test với precision 0.171;
model lúc giao vận chuyển ở cùng số đơn có precision 0.341. Trong nhóm top 5% của model, chỉ khoảng 18%
đơn thật sự trễ. Ghi nhớ con số cuối: nó quyết định can thiệp "báo ngày giao mới" tác động được tới bao
nhiêu đơn.

## Kết quả nộp

- `project/src/olist_cx/features.py` kèm test hợp đồng feature.
- `project/notebooks/m03_model.ipynb`: so sánh model, ba mốc, calibration, chính sách.
- `project/artifacts/flagged.parquet` (không commit) và bảng tóm tắt trong `MODEL_CARD.md`.
- `project/reports/MODEL_CARD.md`.
- `EXPERIMENT_DESIGN.md` của M05 đã cập nhật bằng số thật của model.

## Tiêu chí đạt

- [ ] Feature lúc giao vận chuyển không chứa thông tin sau thời điểm đó; có test chứng minh.
- [ ] Chia theo thời gian đúng mốc; số đơn train / validation / test là 43 362 / 20 468 / 31 994.
- [ ] Bảng ba thời điểm có trên test; nói được giá của việc dự đoán sớm hơn (ROC-AUC, PR-AUC, precision).
- [ ] Model được so với luật không ML ở cùng số đơn được chọn; kết luận theo số, không theo kỳ vọng.
- [ ] PR-AUC luôn được đọc cạnh tỉ lệ dương của tập tương ứng.
- [ ] Ngưỡng chọn trên validation, báo cáo trên test, có khoảng tin cậy bootstrap cho khoản tiết kiệm.
- [ ] `MODEL_CARD.md` nêu rõ thời điểm dự đoán, giới hạn và việc model **không** được dùng.
