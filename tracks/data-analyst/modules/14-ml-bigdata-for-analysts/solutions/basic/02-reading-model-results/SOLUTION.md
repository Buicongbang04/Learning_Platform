# Lời giải: đọc kết quả model churn

## Ba hàm

- **`confusion_table`**: đổi hai đầu vào bằng `np.asarray(...).astype(int)` (nhận list, Series, bool), kiểm cùng
  `shape`, đếm từng ô bằng `((yt == a) & (yp == p)).sum()`. Đếm thủ công thay vì `pd.crosstab` để luôn đủ 4 ô: crosstab
  bỏ cột `1` khi model không bao giờ đoán `1`, đúng trường hợp "luôn đoán ở lại".
- **`scorecard`**: lấy 4 ô từ `confusion_table`. `baseline_accuracy = max(dương, âm) / n` là accuracy của model ngây
  thơ nhất, phải đi kèm mọi con số accuracy. Precision khi không gắn cờ ai và recall khi không có ca dương trả `0.0`
  thay vì lỗi chia 0 (sklearn cũng làm vậy với `zero_division=0`).
- **`threshold_table`**: với mỗi ngưỡng, `pred = score >= t`, gọi `scorecard`. Dùng `>=` cho khớp `sklearn`
  (`predict` của cây đoán `1` khi xác suất lớp 1 lớn hơn 0.5; ở đây quy ước rõ trong đề).

## Đọc kết quả trên dữ liệu thật

| Chính sách | Khách gắn cờ | Bắt được (TP) | Precision | Recall | Accuracy |
| --- | --- | --- | --- | --- | --- |
| Luôn đoán ở lại (7 043 khách) | 0 | 0 | 0 | 0 | 73.46% |
| Quy tắc (7 043 khách) | 1 994 (28.3%) | 1 024 | 51.35% | 54.79% | 74.23% |
| Quy tắc (test 1 761) | 476 (27.0%) | 246 | 51.68% | 52.68% | 74.39% |
| Tree, ngưỡng 0.5 (test) | 208 (11.8%) | 141 | 67.79% | 30.19% | 77.68% |
| Tree, ngưỡng 0.3 (test) | 672 (38.2%) | 348 | 51.79% | 74.52% | 74.79% |
| Tree, ngưỡng 0.15 (test) | 1 056 (60.0%) | 416 | 39.39% | 89.08% | 60.82% |
| Tree, ngưỡng 0.7 (test) | 55 (3.1%) | 49 | 89.09% | 10.49% | 75.89% |

Trả lời Head of Customer Care:

- **"77.7% có tốt không?"** Baseline trên cùng tập test là 73.5%: model chỉ hơn 4.2 điểm accuracy. Accuracy không phải
  câu hỏi đúng; câu hỏi đúng là bắt được bao nhiêu khách sắp rời với bao nhiêu cuộc gọi.
- **"Bắt được bao nhiêu?"** Ở ngưỡng mặc định, 141 trong 467 khách rời (30%), với precision 68%. Model này "thận trọng":
  gọi ít, trúng nhiều, bỏ sót 70%.
- **"Có hơn quy tắc không?"** Ở precision tương đương (khoảng 52%), tree ở ngưỡng 0.3 gắn cờ 672 khách và bắt 348; quy
  tắc gắn cờ 476 và bắt 246. Tree phủ rộng hơn với cùng hiệu quả mỗi cuộc gọi, nhưng cần nhiều cuộc gọi hơn. Nếu đội
  chỉ gọi được khoảng 400 khách, tree không cho chọn đúng cỡ đó (điểm chỉ có 8 giá trị, mỗi lá một giá trị): từ 208
  nhảy lên 672. Model cho điểm liên tục (logistic regression, phần 4 lý thuyết) hợp hơn với ngân sách cố định.
- Accuracy cao nhất (ngưỡng 0.5) không phải ngưỡng tốt nhất cho chiến dịch. Chọn ngưỡng theo số cuộc gọi làm được và
  giá trị một khách giữ được.

## Đáp án trắc nghiệm

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `tree-vs-baseline` | c | Test có 467/1 761 khách rời (26.5%), "luôn đoán ở lại" đúng 73.5%. 77.7 − 73.5 = 4.2 điểm. Baseline không phải 50% (a) vì hai lớp không cân bằng; (b) nhầm baseline với tỉ lệ churn; (d) baseline accuracy luôn tính được |
| `tree-recall` | b | TP = 141, recall 30.2%. 208 (a) là số khách bị gắn cờ, không phải số bắt đúng; 348 (c) là ở ngưỡng 0.3; 363 (d) là 77.7% của 467, nhầm accuracy với recall |
| `rule-reading` | d | 1 994 khách (28.3%), 1 024 rời (51.4%), phủ 1 024/1 869 = 54.8%. (a) nhầm precision; (c) là số của tree ở ngưỡng 0.5 trên test; (b) accuracy gần baseline không có nghĩa quy tắc vô dụng: nó vẫn phủ hơn nửa khách rời |
| `two-year-97` | b | Nhóm hai năm chỉ 48/1 695 = 2.8% rời, nên đoán "ở lại" cho mọi khách đúng 97.2%. Phải hỏi recall và precision. Accuracy cao không chứng minh overfit (c); 1 695 khách đủ để đo (d) |
| `same-precision` | a | Đọc bảng ngưỡng của tree và dòng quy tắc trên test. (b) là tree ở ngưỡng 0.5 (precision 68%, không gần 52%); (d) đảo hai bên |
| `precision-meaning` | c | Precision = TP / số khách được gọi. (a) là recall; (b) là accuracy; (d) là tác động của cuộc gọi, model không đo được điều đó (cần nhóm đối chứng) |
| `lower-threshold` | d | Hạ ngưỡng gắn cờ thêm khách điểm thấp hơn: bắt thêm khách rời (recall tăng) nhưng cũng thêm khách ở lại (precision thường giảm). Accuracy có thể giảm (a sai: từ 0.5 xuống 0.3 accuracy giảm từ 77.7% xuống 74.8%) |
| `ask-ds-team` | a, b, d | Cách chia test và leakage quyết định con số có thật không; precision/recall ở ngưỡng vận hành quyết định có dùng được không. Thư viện (c) không ảnh hưởng chất lượng kết quả |

## Sai lầm hay gặp

- Báo accuracy mà không kèm baseline, hoặc so accuracy giữa hai nhóm có tỉ lệ churn khác nhau.
- Dùng `pd.crosstab` rồi đọc `cm.loc[1, 1]` và bị `KeyError` khi model không bao giờ đoán `1`.
- So hai model ở ngưỡng mặc định của mỗi model (hai chính sách gắn cờ khác số khách) rồi kết luận model nào tốt hơn.
- Đọc precision là "tỉ lệ khách được giữ lại": model chỉ chọn ai để gọi, không đo cuộc gọi có tác dụng không.
