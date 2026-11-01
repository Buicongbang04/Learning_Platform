# Lời giải: classifier phát hiện prompt injection

## Cách làm

**`near_duplicate_pairs`**: `TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)` fit trên `a + b`
(IDF tính trên cả hai phía để một n-gram hiếm ở phía này vẫn có trọng số đúng khi so với phía kia), `cosine_similarity`
giữa hai ma trận thưa, lấy `np.nonzero(sims >= threshold)`, sắp theo `(-cosine, i, j)`. Char n-gram bắt được câu gần
trùng khác một từ, khác dấu câu, khác hoa thường, mà so khớp chính xác bỏ sót.

**`oof_scores`**: `StratifiedKFold(n_splits, shuffle=True, random_state=seed)`; mỗi fold gọi `make_model()` lấy một
pipeline **mới**, fit trên phần train của fold, ghi `predict_proba(...)[:, 1]` vào đúng chỉ số của phần validation. Truyền
**hàm tạo model** thay vì model là thiết kế: vectorizer TF-IDF là một bước học (từ vựng, IDF), fit nó trên toàn bộ dữ
liệu rồi mới chia fold là rò rỉ.

**`metrics_at`**: ép `y` về `bool`, dự đoán dương khi `score >= threshold`, đếm bốn ô; tỉ lệ có mẫu số 0 là `nan` (không
dự đoán dương nào thì precision **không xác định**, không phải 0 hay 1). **`threshold_for_fpr`**: FPR không tăng khi
ngưỡng tăng, nên duyệt `np.unique(scores)` tăng dần và trả giá trị đầu tiên đạt `fpr <= max_fpr`: đó là ngưỡng có recall
cao nhất trong các ngưỡng đạt điều kiện. Các điểm bằng nhau đi cùng nhau vì ngưỡng là `>=`. **`daily_cost`** là
$$(N - N\pi)\,\mathrm{FPR}\,c_{fp} + N\pi\,(1 - \mathrm{recall})\,c_{fn}$$.

## Kết quả thật

PC của track, scikit-learn trong env gốc, `bge-m3` qua Ollama 0.13.5, ngày 2026-11-01.

**Trùng lặp.** Không có câu trùng chính xác trong mỗi tập hay giữa hai tập. Ở ngưỡng cosine 0.9 có 4 cặp gần trùng giữa
train và test, chạm 3 câu test, **đều là câu bình thường** (nhãn 0 ở cả hai phía), ví dụ "War der Atomausstieg sinnvoll?"
và "Ist der Atomausstieg sinnvoll?"; ở ngưỡng 0.8 có 8 cặp. Ba câu trên 116 không đủ làm lệch đáng kể con số test, nhưng
cho thấy bộ dữ liệu có các cặp viết lại và dịch qua lại Anh, Đức của cùng một câu.

**Ba mô hình trên tập test** (116 câu, 60 injection; ngưỡng "FPR ≤ 5%" chọn trên out-of-fold của train):

CLF_TABLE

Theo ngôn ngữ (tập test, ngưỡng 0.5, heuristic phát hiện tiếng Đức theo chữ `äöüß` và từ thường gặp, 44 câu tiếng Đức):

LANG_TABLE

**40 câu tiếng Việt** (20 injection, 20 bình thường):

VI_TABLE

**Chi phí** với giả định minh hoạ của notebook (20 000 request mỗi ngày, 0.5% injection, chặn oan 0.2 USD, bỏ sót 20
USD), dùng recall và FPR đo trên tập test:

COST_TABLE

## Đọc kết quả

READ_SECTION

## Bẫy thường gặp

- Fit `TfidfVectorizer` một lần trên toàn bộ train rồi mới chia fold, hoặc chọn ngưỡng trên tập test.
- Báo precision trên tập cân bằng như con số production.
- Đánh giá trên ngôn ngữ của bộ dữ liệu rồi triển khai cho ngôn ngữ khác.
- `metrics_at` trả precision 0 (hoặc 1) khi không có dự đoán dương, làm bảng so sánh lệch âm thầm.
- `threshold_for_fpr` duyệt từ ngưỡng cao xuống: trả ngưỡng đạt điều kiện nhưng recall thấp nhất.
