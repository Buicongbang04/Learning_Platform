# Lời giải: logistic regression cho churn

## Các hàm

- **`build_features`**: mỗi cột nhị phân là một phép so sánh `.astype(int)`; nhóm tham chiếu là giá trị không có cột
  riêng (month-to-month, DSL). `tech_support` chỉ là `"Yes"`: `"No internet service"` gộp với `"No"`, vì khách không có
  internet đã có cột `no_internet`. Biến số đổi đơn vị trước khi fit (năm, 10 USD) để odds ratio đọc được; đổi đơn vị
  không làm model tốt hay tệ hơn, chỉ đổi cách đọc.
- **`fit_logit`**: `sm.Logit(y, sm.add_constant(X, has_constant="add")).fit(disp=0)`. Không regularization nên hệ số là
  ước lượng maximum likelihood, có khoảng tin cậy và p-value. `LogisticRegression()` của scikit-learn mặc định có L2
  (`C=1.0`), co hệ số về 0: tốt cho dự đoán, sai cho việc đọc độ lớn hiệu ứng.
- **`odds_ratio_table`**: `np.exp` cho hệ số và hai cột của `conf_int()`, bỏ `const`, thêm `odds_change_pct`, sắp tăng.
- **`decile_table`**: `np.argsort(-score, kind="stable")`, nhóm theo vị trí `i * n_bins // n + 1`, rồi `groupby`.
  Chia theo vị trí (không theo `pd.qcut` trên điểm) để các nhóm cùng cỡ kể cả khi nhiều khách cùng điểm.

## Kết quả trên dữ liệu thật

| Đặc trưng | Odds ratio | Khoảng tin cậy 95% | p-value | Câu cho Head of Retention |
| --- | --- | --- | --- | --- |
| `contract_two_year` | 0.251 | 0.171–0.369 | < 0.001 | So với month-to-month, cùng các yếu tố khác, odds rời thấp hơn khoảng 75% |
| `contract_one_year` | 0.480 | 0.378–0.610 | < 0.001 | Odds thấp hơn khoảng một nửa |
| `no_internet` | 0.494 | 0.350–0.698 | < 0.001 | Khách chỉ dùng thoại: odds thấp hơn một nửa so với DSL |
| `tech_support` | 0.666 | 0.546–0.812 | < 0.001 | Có hỗ trợ kỹ thuật: odds thấp hơn 33% |
| `tenure_years` | 0.684 | 0.647–0.724 | < 0.001 | Mỗi năm gắn bó: odds thấp hơn 32%; hai năm: 0.684² = 0.47, thấp hơn 53% |
| `monthly_charges_10` | 1.088 | 1.013–1.169 | 0.022 | Mỗi 10 USD cước: odds cao hơn 9%; bằng chứng yếu nhất |
| `senior` | 1.309 | 1.086–1.577 | 0.005 | Khách cao tuổi: odds cao hơn 31% |
| `electronic_check` | 1.502 | 1.286–1.753 | < 0.001 | Trả bằng electronic check: odds cao hơn 50% |
| `paperless` | 1.599 | 1.355–1.887 | < 0.001 | Hoá đơn điện tử: odds cao hơn 60% |
| `fiber_optic` | 1.954 | 1.437–2.657 | < 0.001 | Cáp quang so với DSL, cùng cước tháng: odds gần gấp đôi |

Xếp hạng trên test 1 761 khách: ROC-AUC 0.8407.

| Decile | Khách | Rời bỏ | Tỉ lệ | Lift | Phủ cộng dồn |
| --- | --- | --- | --- | --- | --- |
| 1 | 177 | 130 | 73.4% | 2.77 | 27.8% |
| 2 | 176 | 96 | 54.5% | 2.06 | 48.4% |
| 3 | 176 | 83 | 47.2% | 1.78 | 66.2% |
| 4 | 176 | 60 | 34.1% | 1.29 | 79.0% |
| 5 | 176 | 38 | 21.6% | 0.81 | 87.2% |
| 6–10 | 880 | 60 | 6.8% | | 100% |

Cùng 476 cuộc gọi trên test: quy tắc bắt 246 khách rời (52.7%), model bắt 286 (61.2%), thêm 40 khách, tức khoảng 8.6
điểm phần trăm độ phủ. Muốn quy ra tiền cần thêm: giá trị một khách giữ được (cước × thời gian ở lại thêm), chi phí
một cuộc gọi và ưu đãi, và **tỉ lệ cuộc gọi giữ được khách**, thứ chỉ đo được bằng thử nghiệm có nhóm đối chứng.

Câu chuyện cho Head of Retention: *"Ba nhóm rủi ro rõ nhất là khách month-to-month, khách mới (dưới 1–2 năm) và khách
cáp quang; hợp đồng dài và gói hỗ trợ kỹ thuật đi kèm rủi ro thấp hơn nhiều. Dùng model thay quy tắc, cùng số cuộc gọi,
đội bắt thêm khoảng 40 trên 467 khách sắp rời trong mẫu kiểm tra. Đây là tương quan: muốn biết đưa khách lên hợp đồng
dài có giữ được họ không, cần một thử nghiệm."*

## Đáp án trắc nghiệm

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `two-year-sentence` | c | OR 0.25 là odds nhân 0.25, tức thấp hơn 75%, có điều kiện "cùng các yếu tố khác". (a) là tỉ lệ churn của nhóm (thực tế 2.8%), không phải OR; (b) odds ratio không phải chênh lệch xác suất; (d) là kết luận nhân quả |
| `tenure-two-years` | b | Odds ratio nhân theo từng đơn vị: 0.684 × 0.684 = 0.468, thấp hơn 53%. (a) cộng phần trăm (32 + 32 thành 63, làm tròn), sai vì hiệu ứng nhân; (c) là một năm |
| `weakest-factor` | d | `monthly_charges_10`: khoảng tin cậy 1.013–1.169, p = 0.022. Các yếu tố khác p < 0.01. Lưu ý cước tháng tương quan mạnh với cáp quang (cáp quang đắt hơn), nên phần lớn hiệu ứng của giá đã nằm trong `fiber_optic` |
| `paperless-causal` | b | Odds ratio là tương quan có điều kiện trên các biến trong model; paperless có thể đánh dấu nhóm khách quen dịch vụ số, dễ đổi nhà mạng. (a), (d) là kết luận nhân quả; (c) loại biến vì "khó giải thích" làm hệ số khác bị lệch |
| `top-decile` | a | 130 / 177 = 73.4%, lift = 73.4% / 26.5% = 2.77. (b) là phủ cộng dồn của decile 1; (c) là decile 2 |
| `same-budget` | c | Lấy 476 khách điểm cao nhất trên test: 286 khách rời, 61.2% của 467. (b) là số của 30% khách (529 cuộc gọi), không cùng ngân sách |
| `why-statsmodels` | b | `LogisticRegression()` mặc định `penalty="l2"`, `C=1.0`: hệ số bị co, và sklearn không trả sai số chuẩn. Có thể đặt `penalty=None` để ra cùng hệ số, nhưng vẫn phải tự tính khoảng tin cậy |
| `auc-meaning` | d | ROC-AUC là xác suất model xếp một khách rời ngẫu nhiên cao hơn một khách ở lại ngẫu nhiên. (a) là accuracy; (c) nhầm với tác động của chiến dịch; (b) không phải định nghĩa (và trên dữ liệu này 50% khách điểm cao nhất phủ 87.2%) |

## Sai lầm hay gặp

- One-hot cả ba loại hợp đồng cộng hệ số chặn: các cột phụ thuộc tuyến tính, `statsmodels` báo `Singular matrix` hoặc
  ra hệ số vô nghĩa. Luôn bỏ một nhóm làm tham chiếu và nói rõ đó là nhóm nào.
- Đọc odds ratio như tỉ số xác suất ("khách cáp quang rời gấp đôi"). Với tỉ lệ churn 26.5% hai thứ khác nhau rõ.
- Dùng `pd.qcut(score, 10)` khi nhiều khách cùng điểm: báo lỗi biên trùng hoặc ra nhóm lệch cỡ.
- So model với quy tắc ở hai cỡ danh sách khác nhau.
