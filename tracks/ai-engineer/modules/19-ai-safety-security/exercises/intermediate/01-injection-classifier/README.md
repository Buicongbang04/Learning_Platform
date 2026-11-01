---
title: Classifier phát hiện prompt injection - chia tập đúng, ngưỡng theo FPR, chi phí chặn oan
level: intermediate
services: []
files:
  - path: starter/classifier.ipynb
    note: 5 hàm TODO
  - path: tests/test_classifier.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py prompt-injections
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/01-injection-classifier/starter/classifier.ipynb
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/01-injection-classifier -q
---

## Mục tiêu

Train và đánh giá bộ phát hiện prompt injection trên bộ công khai deepset/prompt-injections theo cách một kỹ sư có
trách nhiệm làm: kiểm trùng lặp giữa train và test, chọn ngưỡng bằng out-of-fold không nhìn test, báo precision, recall
và **FPR**, đổi FPR thành chi phí vận hành, và thử mô hình trên tiếng Việt, ngôn ngữ nó chưa từng thấy. Bạn so ba mô
hình: TF-IDF theo từ, TF-IDF theo ký tự, và embedding `bge-m3` (module 12) cộng logistic regression.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Cần bộ `prompt-injections` (546 train, 116 test, cột `text`, `label`) và Ollama với `bge-m3` cho phần embedding (embed
khoảng 700 câu; cả notebook lời giải chạy khoảng 3 phút trên PC của track khi Ollama dùng chung). Phần TF-IDF chạy vài
giây. Với vài câu, `bge-m3` qua Ollama trả lỗi `NaN` (module 13 đã gặp); notebook embed lại các câu đó bằng một biến thể
nhỏ.

Trong `starter/classifier.ipynb`, cell chấm điểm:

1. `near_duplicate_pairs(a, b, threshold=0.9)`: các cặp gần trùng giữa hai danh sách câu theo cosine TF-IDF char n-gram.
2. `oof_scores(make_model, texts, y, n_splits=5, seed=0)`: điểm out-of-fold, mỗi fold một model mới, chia theo tầng.
3. `metrics_at(y, scores, threshold)`: `tp, fp, fn, tn, precision, recall, fpr` khi dự đoán dương là `score >= threshold`.
4. `threshold_for_fpr(y, scores, max_fpr)`: ngưỡng nhỏ nhất có FPR không quá `max_fpr`.
5. `daily_cost(n_requests, base_rate, recall, fpr, cost_fp, cost_fn)`: chi phí kỳ vọng mỗi ngày của chặn oan và bỏ sót.

Notebook mô tả chính xác từng hàm. Rồi chạy các cell `explore`: nhìn dữ liệu và cặp gần trùng, hai baseline TF-IDF và
mô hình embedding (ngưỡng 0.5 và ngưỡng FPR 5% chọn trên out-of-fold), tách theo ngôn ngữ, 40 câu tiếng Việt tự viết, và
bảng chi phí. Trả lời các câu hỏi ở cuối notebook, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `near_duplicate_pairs` tìm đúng cặp gần trùng (không phân biệt hoa thường, vectorizer fit trên cả hai danh sách), sắp
  theo cosine giảm dần, không trả gì khi ngưỡng quá cao; trên dữ liệu thật tìm được vài cặp.
- `oof_scores` không để câu validation lọt vào lúc fit, tạo model mới mỗi fold, giữ tỉ lệ nhãn mỗi fold, cùng seed cùng
  cách chia, khác seed khác cách chia.
- `metrics_at` đúng cả khi không có dự đoán dương nào (`precision` là `nan`); `threshold_for_fpr` đúng với điểm bằng
  nhau và trả `inf` khi không ngưỡng nào đạt.
- `daily_cost` đúng công thức.
- Cell `explore` chạy hết và in bảng ba mô hình, bảng tiếng Việt và bảng chi phí.

## Gợi ý

### Gợi ý 1

Một `sklearn.pipeline.make_pipeline(TfidfVectorizer(...), LogisticRegression(...))` vừa là "model" có `fit` và
`predict_proba`, vừa bảo đảm vectorizer học lại trong mỗi fold: đó là lý do `oof_scores` nhận một **hàm tạo model**
chứ không nhận một model đã tạo. `StratifiedKFold(...).split(texts, y)` trả chỉ số của từng fold.

### Gợi ý 2

FPR không tăng khi ngưỡng tăng, nên duyệt các giá trị điểm từ nhỏ tới lớn và dừng ở giá trị đầu tiên đạt điều kiện.
`np.unique` vừa bỏ trùng vừa sắp tăng dần. Với `metrics_at`, ép `y` về `bool` trước khi dùng `&` và `~`.
