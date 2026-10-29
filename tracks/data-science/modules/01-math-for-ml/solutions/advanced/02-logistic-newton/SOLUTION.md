# Hướng làm: logistic regression từ đầu bằng gradient descent và Newton

## Cài đặt

- `build_review_table`: lọc đơn giao xong, bỏ đơn mua từ 2018-09-01, giữ review mới nhất theo
  `review_answer_timestamp`, `late` so nguyên timestamp, `delay_days` và `delivery_days` là
  `Timedelta / 1 ngày` (số thực, không làm tròn), split theo quy ước chung.
- `logistic_loss_grad_hess`: loss viết theo logit với `np.logaddexp`; $$p$$ tính bằng
  `np.exp(-np.logaddexp(0, -z))` để không tràn số; Hessian $$\frac1n X^\top\mathrm{diag}(p(1-p))X$$ tính
  bằng `(X * (p * (1 - p))[:, None]).T @ X`, không tạo ma trận chéo n×n; L2 nhân với mặt nạ bỏ intercept.
- `fit_logistic_newton`: `np.linalg.solve(H, g)`, dừng theo chuẩn gradient.
- `fit_logistic_gd`: lr cố định; cận trên độ cong là $$\lambda_{\max}(X^\top X/n)/4$$ vì $$p(1-p) \le 1/4$$, nên
  lr = 1/L luôn an toàn.

## Kết quả tham chiếu

Bảng dữ liệu: 43 362 đơn train, 20 468 val, 31 994 test; tỉ lệ review xấu 12.1% / 18.0% / 10.4%, tỉ lệ
trễ 6.5% / 14.4% / 5.9%. Tỉ lệ review xấu trên toàn bộ bảng: 12.8%.

Feature chuẩn hoá trên train `[late, delay_days, delivery_days]`:

| | Newton | Gradient descent (lr = 1/L) |
| --- | --- | --- |
| Feature chuẩn hoá, κ(X) ≈ 2.6 | 5 bước, ‖∇L‖ ≈ 6 · 10⁻¹¹ | 63 bước tới loss cách tối ưu 1e-6, 140 bước tới 1e-10 |
| Đơn vị gốc (ngày), κ(X) ≈ 98.9 | 6 bước | sau 20 000 bước vẫn cách tối ưu 0.002 |

Hệ số (chuẩn hoá): intercept −2.1452, late 0.4517, delay_days −0.0464, delivery_days 0.3332; khớp
`LogisticRegression(C=np.inf)`. Trên đơn vị gốc: odds ratio 6.27 cho `late`, 0.995 mỗi ngày
`delay_days`, 1.036 mỗi ngày `delivery_days`. Đọc gộp: vượt ngày hẹn nhân odds review xấu khoảng 6 lần;
mỗi ngày giao thêm tăng odds khoảng 3.6%. Hệ số âm nhỏ của `delay_days` là hiệu ứng "giữ các biến khác
cố định" giữa ba feature tương quan, không nên diễn giải riêng.

Tỉ lệ review xấu theo số ngày trễ (toàn bộ bảng): giao sớm hơn 7 ngày 9.0%, sớm 0–7 ngày 10.2%,
trễ 0–3 ngày 19.1%, trễ 3–7 ngày 61.3%, trễ 7–14 ngày 78.1%, trễ trên 14 ngày 78.8%. Quan hệ không tuyến
tính: tăng vọt sau 3 ngày rồi bão hoà. Một logistic regression tuyến tính trên `delay_days` bỏ lỡ hình dạng
này; feature dạng khoảng (bucket) hoặc spline sẽ khớp hơn.

Chất lượng: AUC val 0.760, AUC test 0.636; log loss test 0.311 so với 0.335 của dự đoán hằng. Val
(tháng 1–3/2018) có nhiều đơn trễ (14.4%) nên feature trễ phân biệt tốt; test (4–8/2018) chỉ 5.9% đơn
trễ, phần lớn review xấu đến từ lý do khác (sản phẩm, seller). Đây là **dịch chuyển phân phối theo thời
gian**, lý do track bắt buộc chia theo thời gian.

**Non-convex**: `MLPClassifier(hidden_layer_sizes=(8,))` trên cùng feature chuẩn hoá, 10 seed: loss
train cuối 0.3202 – 0.3281 (logistic: 0.3281), AUC val 0.760 – 0.765, trọng số lớp đầu khác hẳn nhau
giữa các seed (cùng một phần tử có thể là −1.06 hoặc 0.83). Loss lồi có một optimum, mọi khởi tạo tới
cùng chỗ; loss không lồi cho nhiều nghiệm khác nhau, kết quả phụ thuộc seed, nên phải cố định seed, chạy
nhiều seed để báo cáo độ dao động, và không diễn giải từng trọng số.

**Dữ liệu tách được**: không có MLE hữu hạn; loss giảm mãi khi $$\lVert w\rVert \to \infty$$, Newton gặp Hessian
gần suy biến (vì $$p(1-p) \to 0$$), gradient descent chạy mãi với hệ số tăng dần. L2 làm loss **strongly
convex**, có nghiệm duy nhất, hữu hạn. Thực tế hay gặp khi có feature rò rỉ nhãn hoặc khi một nhóm nhỏ
toàn nhãn 1.

## Các quyết định cần cân nhắc

- **Newton hay gradient descent**: Newton mỗi bước $$O(nd^2 + d^3)$$, hội tụ bậc hai, không quan tâm thang
  đo; tốt khi d tới vài nghìn. d lớn hoặc dữ liệu thưa: L-BFGS (xấp xỉ Hessian từ lịch sử gradient,
  mặc định của `sklearn`) hoặc SGD. Dữ liệu không vừa bộ nhớ: SGD / minibatch.
- **Chuẩn hoá** vẫn nên làm cả khi dùng Newton: cho regularization công bằng giữa các feature và
  hệ số so sánh được.
- **Diễn giải**: logistic regression trên dữ liệu quan sát cho tương quan có điều kiện, không phải tác
  động nhân quả của giao trễ (module 06).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Cài đặt đúng | 20 | Test pass; ổn định số; không tạo ma trận n×n; dùng `solve` |
| Kiểm chứng | 10 | Gradient check, so với sklearn, kiểm Hessian nửa xác định dương, nói rõ đã kiểm gì |
| Hội tụ | 20 | Số bước và thời gian cả hai optimizer, có và không chuẩn hoá; giải thích bằng condition number và hội tụ bậc hai; nói khi nào chọn L-BFGS / SGD |
| Diễn giải kinh doanh | 15 | Odds ratio dễ hiểu; nhận ra quan hệ phi tuyến theo số ngày trễ; nói rõ tương quan, không nhân quả |
| Đánh giá theo thời gian | 10 | Báo cáo val và test, giải thích vì sao khác nhau |
| Convex vs non-convex | 15 | Thí nghiệm nhiều seed có số liệu; hệ quả thực tế (seed, báo cáo độ dao động, không diễn giải trọng số) |
| Tách được và L2 | 10 | Giải thích MLE không tồn tại, vai trò strongly convex của L2, cách chọn λ |

Từ 70 điểm: đạt.
