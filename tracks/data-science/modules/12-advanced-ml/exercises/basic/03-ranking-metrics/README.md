---
title: Metric xếp hạng @k cho recommender
level: basic
services: []
files:
  - path: starter/ranking.py
    note: 5 hàm TODO
  - path: tests/test_ranking.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/basic/03-ranking-metrics -q
---

## Mục tiêu

Cài đúng bốn metric offline chuẩn của recommender (precision@k, recall@k, AP@k, NDCG@k) và hiểu
mỗi cái nhạy với điều gì. Đây là các hàm bạn sẽ dùng lại ở bài Intermediate 02 và Advanced 02.

## Đề bài

Relevance nhị phân: một item là relevant nếu nằm trong tập `relevant` của user (ví dụ phim user
thực sự xem trong giai đoạn test). Trong `starter/ranking.py`:

1. `precision_at_k(recommended, relevant, k)`: số hit trong `recommended[:k]` chia cho **k**, kể cả
   khi danh sách ngắn hơn k (gợi ý thiếu là lỗi của hệ thống).
2. `recall_at_k(recommended, relevant, k)`: số hit chia cho $$|\text{relevant}|$$; 0 nếu tập rỗng.
3. `average_precision_at_k`: theo quy ước phổ biến (MAP@k của Kaggle, `ml_metrics`):

   $$
   \mathrm{AP@}k = \frac{1}{\min(|\text{relevant}|, k)} \sum_{i=1}^{k} \mathrm{P@}i \cdot \mathbb{1}[\text{item}_i \in \text{relevant}]
   $$

4. `ndcg_at_k`: gain nhị phân, $$\mathrm{DCG@}k = \sum_{i=1}^{k} \frac{\mathrm{rel}_i}{\log_2(i + 1)}$$, chia
   cho IDCG@k là DCG của danh sách lý tưởng (mọi item relevant ở đầu, tối đa k item). 0 nếu không
   có item relevant.
5. `mean_at_k(recs, truth, metric, k)`: trung bình `metric` trên **mọi user trong `truth`**; user
   không có trong `recs` coi như nhận danh sách rỗng; user chỉ có trong `recs` bị bỏ qua.

## Tiêu chí đạt

- Đúng các ví dụ tính tay trong test, kể cả danh sách ngắn hơn k và tập relevant rỗng.
- AP@k và NDCG@k phân biệt được hai thứ tự có cùng precision@k.
- IDCG bị giới hạn ở k item.
- `mean_at_k` lấy trung bình theo user của `truth`, không theo user của `recs`.

## Gợi ý

### Gợi ý 1

Chuyển `relevant` sang `set` một lần ở đầu hàm; `item in set` là O(1).

### Gợi ý 2

Quy ước của `mean_at_k` không phải chi tiết vặt: nếu chỉ lấy trung bình trên user **có** gợi ý,
một hệ thống bỏ qua user khó (ít lịch sử) sẽ được điểm cao hơn thực tế. Cùng một bộ dữ liệu, hai
paper dùng hai quy ước khác nhau cho ra hai con số không so được với nhau.
