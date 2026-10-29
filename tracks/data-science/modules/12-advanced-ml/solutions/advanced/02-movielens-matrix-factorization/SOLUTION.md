# Hướng làm: matrix factorization và chọn recommender

Bài Advanced không có đáp án duy nhất. Dưới đây là cài đặt tham chiếu, các con số tham chiếu trên
MovieLens và rubric.

## Cài đặt tham chiếu (ALS có bias)

- $$\mu$$ là trung bình rating train, cố định. Ma trận phần dư $$R - \mu$$ dạng `csr_matrix`.
- Mỗi vòng: với từng user, giải ridge regression của $$r_{ui} - \mu - b_i$$ theo thiết kế
  $$[q_i, 1]$$ để có $$[p_u, b_u]$$; với từng phim, giải tương tự theo $$[p_u, 1]$$ để có $$[q_i, b_i]$$:

  $$
  [p_u, b_u] = \left(A^\top A + \lambda I\right)^{-1} A^\top \left(r_u - \mu - b_{I_u}\right),
  \qquad A = [Q_{I_u}, \mathbf{1}]
  $$

- Mặc định `n_factors=20`, `reg=10` (λ của ALS nhân với tổng bình phương, nên lớn hơn hẳn reg của
  SGD), `n_iters=15`. Fit MovieLens khoảng 2–3 giây.
- `predict`: tra chỉ số bằng `searchsorted`; phần nào lạ thì đóng góp 0. `recommend`: dự đoán cho mọi
  phim của train, gán `-inf` cho phim bị loại, sort.

SGD cũng đạt test nếu chọn learning rate và reg hợp lý; đánh đổi: SGD dễ mở rộng cho implicit
feedback và dữ liệu khổng lồ, ALS song song hoá tốt (mỗi user giải độc lập) và không cần chọn
learning rate.

## Số liệu tham chiếu (split 20% mới nhất mỗi user)

| Model | RMSE test | precision@10 | recall@10 | coverage |
| --- | --- | --- | --- | --- |
| Trung bình toàn cục | 1.068 | | | |
| Chỉ bias (`n_factors=0`) | 0.902 | 0.053 | 0.026 | 60 |
| MF `n_factors=20, reg=10` | 0.893 | 0.071 | 0.035 | 357 |
| MF `n_factors=20, reg=30` | 0.913 | 0.069 | 0.034 | 80 |
| Popularity (bài Intermediate 02) | | 0.075 | 0.039 | 98 |
| Item-item (bài Intermediate 02) | | 0.097 | 0.055 | 473 |

- MF chỉ cải thiện RMSE 1% so với baseline bias trên split theo thời gian. Phần lớn "tín hiệu" của
  rating nằm ở bias user/phim (như bài học từ Netflix Prize).
- MF tối ưu RMSE **thua popularity** ở precision@10 (0.071 so với 0.075) và thua xa item-item. RMSE
  đo sai số trên những cặp user đã chọn xem; top-10 phải xếp hạng trên mọi phim chưa xem. Baseline
  chỉ bias gợi ý phim điểm trung bình cao nhưng ít người xem (P@10 chỉ 0.053). Danh sách của MF có
  trung vị 115 rating mỗi phim trong train, so với 244 của top-10 phổ biến.
- Muốn MF tốt cho top-k, đổi mục tiêu: implicit feedback (mọi cặp chưa xem là âm tính có trọng số
  thấp, như iALS của Hu, Koren, Volinsky 2008) hoặc loss xếp hạng (BPR).
- Cold start: 8.3% rating trong test thuộc phim chưa có trong train. MF và item-item đều không gợi
  ý được những phim đó; cần feature nội dung (thể loại, tag, mô tả) hoặc slot "phim mới" có kiểm
  soát.

## Các quyết định thiết kế cần cân nhắc

- **Metric chính**: theo mục tiêu sản phẩm (xem nhiều hơn: precision/recall trên mọi tương tác;
  hài lòng: chỉ tính rating cao; khám phá: coverage, novelty).
- **User mới**: popularity theo ngữ cảnh (thời gian, vùng), hỏi sở thích lúc đăng ký, chuyển sang CF
  khi đủ vài tương tác.
- **Phim mới**: content-based, boost có giới hạn, exploration (bandit).
- **Feedback loop**: model chỉ học từ những gì đã được gợi ý; giữ một phần traffic ngẫu nhiên hoặc
  exploration để có dữ liệu không thiên lệch.
- **Online**: A/B test (module 03) với metric chính như số phim xem/tuần, guardrail như tỉ lệ bỏ
  dở, đa dạng nội dung.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Cài đặt MF (test pass) | 20 | 8/8 test pass |
| So sánh offline công bằng | 20 | Cùng split cho mọi model; tune trên validation tách từ train; có cả RMSE và metric top-k |
| Giải thích RMSE vs top-k | 15 | Nhận ra và giải thích được vì sao MF tối ưu RMSE không thắng ở top-10 |
| Cold start | 15 | Đo tỉ lệ phim/user mới, chiến lược riêng cho từng loại |
| Rủi ro và giới hạn offline | 15 | Popularity bias, feedback loop, khác biệt xem/thích |
| Kế hoạch online | 10 | Metric chính, guardrail, thiết kế A/B test |
| Trình bày | 5 | PM đọc hiểu được trong 5 phút |

Đạt từ 70 điểm. Lỗi trừ nặng: tune trên test; chia ngẫu nhiên theo dòng; khuyến nghị MF chỉ vì RMSE
thấp nhất.
