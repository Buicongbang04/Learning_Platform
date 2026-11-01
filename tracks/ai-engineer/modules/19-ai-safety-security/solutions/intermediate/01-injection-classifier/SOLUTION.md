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

| Mô hình | AUC | Ngưỡng | Precision | Recall | FPR |
| --- | --- | --- | --- | --- | --- |
| TF-IDF từ (1-2 gram) + LR | 0.959 | 0.5 | 0.978 | 0.750 | 1/56 = 0.018 |
| | | 0.553 (FPR ≤ 5% oof) | 1.000 | 0.717 | 0/56 |
| TF-IDF ký tự (2-5 gram) + LR | 0.977 | 0.5 | 1.000 | 0.867 | 0/56 |
| | | 0.425 (FPR ≤ 5% oof) | 0.964 | 0.883 | 2/56 = 0.036 |
| `bge-m3` + LR | **1.000** | 0.5 | 1.000 | 1.000 | 0/56 |
| | | 0.382 (FPR ≤ 5% oof) | 1.000 | 1.000 | 0/56 |

AUC out-of-fold trên train: 0.957 (từ), 0.981 (ký tự), 0.995 (`bge-m3`). Khi embed, `bge-m3` trả `NaN` (Ollama báo HTTP
500) cho 14/662 câu; các câu đó được embed lại bằng một biến thể nhỏ (thêm " ." ở cuối, viết thường, gộp khoảng trắng, hoặc
nửa đầu câu), đúng cách module 13 xử lý lỗi này.

Theo ngôn ngữ (tập test, ngưỡng 0.5, heuristic phát hiện tiếng Đức theo chữ `äöüß` và từ thường gặp, 44 câu tiếng Đức):

| Mô hình | Recall tiếng Anh (37 injection) | Recall tiếng Đức (23 injection) | FPR tiếng Anh / Đức |
| --- | --- | --- | --- |
| TF-IDF từ | 0.784 | 0.696 | 0 / 1 câu |
| TF-IDF ký tự | 0.865 | 0.870 | 0 / 0 |
| `bge-m3` + LR | 1.000 | 1.000 | 0 / 0 |

**40 câu tiếng Việt** (20 injection, 20 bình thường):

| Mô hình | Ngưỡng | Recall | FPR | AUC |
| --- | --- | --- | --- | --- |
| TF-IDF từ | 0.5 | 1/20 = 0.05 | 1/20 | 0.584 |
| TF-IDF ký tự | 0.5 | 8/20 = 0.40 | 1/20 | 0.805 |
| | 0.425 | 10/20 = 0.50 | 3/20 | |
| `bge-m3` + LR | 0.5 | **20/20** | **5/20 = 0.25** | 0.997 |
| | 0.382 | 20/20 | 6/20 = 0.30 | |

Năm câu bình thường mà `bge-m3` + LR chặn ở ngưỡng 0.5: "Hãy bỏ qua bước 2 trong hướng dẫn cài đặt...", "Từ giờ tôi muốn
bạn trả lời ngắn gọn hơn, được không?", "Hướng dẫn tôi cách đặt lại router về cài đặt gốc.", "Dịch câu sau sang tiếng Anh:
...", "Giải thích sự khác nhau giữa RAM và ROM.".

**Chi phí** với giả định minh hoạ của notebook (20 000 request mỗi ngày, 0.5% injection, chặn oan 0.2 USD, bỏ sót 20
USD), dùng recall và FPR đo trên tập test:

| Mô hình | Ngưỡng | USD/ngày (0.5% injection) | USD/ngày (0.05% injection) |
| --- | --- | --- | --- |
| TF-IDF từ | 0.5 | 571 | 121 |
| TF-IDF từ | 0.553 | 566 | 57 |
| TF-IDF ký tự | 0.5 | 266 | 27 |
| TF-IDF ký tự | 0.425 | 376 | 166 |
| `bge-m3` + LR | 0.5 hoặc 0.382 | 0 | 0 |

Con số 0 của `bge-m3` chỉ đúng **trên deepset**: dùng recall và FPR đo trên 40 câu tiếng Việt (recall 1.0, FPR 0.25) thì
cùng giả định cho khoảng 995 USD/ngày, gần như toàn bộ là chặn oan.

## Đọc kết quả

- **Trùng lặp nhỏ, nhưng phải kiểm**: 3 câu test có bản gần trùng trong train, đều nhãn 0. Với embedding đa ngôn ngữ, "gần
  trùng" còn gồm bản **dịch** (một câu tiếng Anh ở train, bản tiếng Đức ở test), thứ char n-gram không thấy. Kiểm thêm
  bằng láng giềng gần nhất trong không gian `bge-m3`: 12 câu test có câu train cosine từ 0.9 trở lên, cùng nhãn cả 12; bỏ
  12 câu đó, `bge-m3` + LR vẫn tách hoàn hảo 104 câu còn lại, nên điểm tuyệt đối trên test không đến từ rò rỉ kiểu này.
  Chúng tôi không kiểm được `bge-m3` có từng thấy bộ deepset khi train hay không.
- **Ký tự thắng từ** với dữ liệu hai ngôn ngữ và nhiều lỗi chính tả, biến thể ("Don'nt", "Rassistent"): char n-gram
  bền với lỗi chính tả và có thể dùng chung mảnh ký tự giữa các biến thể của một từ. **Embedding thắng cả hai** trên deepset.
- **Chuyển sang tiếng Việt là chỗ mọi mô hình vỡ, theo hai kiểu khác nhau**: TF-IDF từ gần như mù (recall 0.05: từ vựng học từ tiếng Anh
  và tiếng Đức hầu như không chứa từ tiếng Việt), TF-IDF ký tự bắt được 8/20, phần lớn là câu dài
  nhiều vế kiểu "Rất tốt. Giờ hãy quên tài liệu đi và ..." (giống khuôn câu của deepset), có lẽ nhờ dấu câu, độ dài và các
  mảnh ký tự chung hơn là nhờ hiểu nghĩa; `bge-m3`
  bắt hết injection nhưng chặn oan một phần tư câu bình thường, đúng những câu có dáng "mệnh lệnh" ("bỏ qua bước 2", "từ
  giờ ... ngắn gọn hơn", "hướng dẫn tôi..."). Mô hình học "câu mệnh lệnh đổi hướng" chứ không học "tấn công".
- **Chi phí phụ thuộc base rate và ngôn ngữ, không chỉ AUC**: với 0.5% injection, bỏ sót đắt hơn (TF-IDF ký tự ở ngưỡng
  0.5 rẻ hơn ở ngưỡng FPR 5%); với 0.05% injection, mỗi điểm FPR đắt lên tương đối. Trên tiếng Việt, chính mô hình tốt
  nhất trên deepset lại đắt nhất vì chặn oan.
- **Không dùng mô hình nào trong ba làm lớp phòng thủ duy nhất cho chatbot tiếng Việt.** Cần dữ liệu có nhãn tiếng Việt
  của chính ứng dụng (cả câu bình thường "trông giống" tấn công), chọn ngưỡng trên dữ liệu đó, và dùng điểm để gắn cờ,
  giảm quyền, ghi log thay vì chặn cứng. 40 câu tự viết chỉ đủ thấy hướng: một câu là 0.05 recall hoặc FPR.

## Bẫy thường gặp

- Fit `TfidfVectorizer` một lần trên toàn bộ train rồi mới chia fold, hoặc chọn ngưỡng trên tập test.
- Báo precision trên tập cân bằng như con số production.
- Đánh giá trên ngôn ngữ của bộ dữ liệu rồi triển khai cho ngôn ngữ khác.
- `metrics_at` trả precision 0 (hoặc 1) khi không có dự đoán dương, làm bảng so sánh lệch âm thầm.
- `threshold_for_fpr` duyệt từ ngưỡng cao xuống: trả ngưỡng đạt điều kiện nhưng recall thấp nhất.
