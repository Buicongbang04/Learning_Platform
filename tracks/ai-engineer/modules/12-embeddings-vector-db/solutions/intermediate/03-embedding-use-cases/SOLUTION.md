# Lời giải: embedding ngoài search

## Cách làm

- **`class_centroids`**: trung bình theo mặt nạ nhãn, chia chuẩn (lớp rỗng giữ 0). **`predict_centroid`**: `argmax` của
  `x @ centroids.T`.
- **`knn_predict`**: theo lô, `sims = x_lô @ train.T`, `argsort(-sims, kind="stable")[:, :k]`; với mỗi dòng, `np.bincount`
  đếm phiếu và cộng cosine (`weights=`), chọn lớp theo khoá `(phiếu, tổng cosine, -nhãn)`.
- **`near_duplicates`**: theo lô dòng, `np.nonzero(sims >= threshold)`, cộng vị trí bắt đầu lô vào chỉ số dòng, giữ `i < j`,
  sắp theo `(-cos, i, j)`. **`nearest_in`**: `argmax` theo lô (argmax chọn chỉ số nhỏ khi bằng nhau).
- **`knn_anomaly_scores`**: theo lô, `np.partition` lấy `k` cosine lớn nhất (không cần sort hết), `1 - mean`.
- **`auroc`**: so mọi cặp (dương, âm) bằng broadcasting, đếm `>` cộng nửa số `==`, chia số cặp.
- **`recommend`**: trung bình vector đã thích, chuẩn hoá, xếp giảm dần, bỏ mục đã thích, lấy `k`.

## Kết quả thật

PC của track, `bge-m3` qua Ollama (`.superpowers/scratch/logs/usecases_results.txt`). Embed 16 175 câu UIT-VSFC mất 314 s;
3 câu làm `bge-m3` trả `NaN` (Ollama báo HTTP 500) và được embed lại bằng biến thể thêm " .". Có cache thì notebook chạy
khoảng 1 phút.

**Phân loại cảm xúc** (C của logistic regression chọn trên validation trong {0.1, 1, 10}: 0.697, 0.785, 0.821, chọn 10):

| Bộ phân loại | macro-F1 test (3 166 câu) | accuracy | F1 neutral | macro-F1 150 câu ghim |
| --- | --- | --- | --- | --- |
| `bge-m3` + LogReg (C = 10) | **0.770** | 0.925 | **0.420** | 0.761 |
| kNN k = 10 | 0.716 | 0.918 | 0.269 | 0.667 |
| centroid | 0.706 | 0.830 | 0.342 | 0.782 |
| *Mốc module 04: TF-IDF + LogReg / BiLSTM* | *0.716 / 0.755* | | | |
| *Mốc module 11: `qwen2.5:3b` zero-shot / JSON schema* | | | | *0.804 / 0.852* |

LogReg fit 0.8 s trên 11 426 câu, dự đoán 0.001 ms/câu (chưa tính thời gian embed câu).

**Trùng lặp**: train có đúng 1 câu trùng từng ký tự, nhưng 216 cặp cosine ≥ 0.99, 10 651 cặp ≥ 0.95, 155 255 cặp ≥ 0.90; cặp
≥ 0.95 cùng nhãn cảm xúc 99.3%. Ví dụ 0.999: "đôi lúc giảng bài hơi nhanh ." và "đôi khi giảng bài hơi nhanh .". Câu test có câu
train gần nhất ≥ 0.99: 84; ≥ 0.95: **756 / 3 166** (24%), nhãn 1-NN khớp 97.5%; ≥ 0.90: 1 491. macro-F1 LogReg trên 756 câu đó
**0.850**, trên phần còn lại **0.753**.

**Bất thường**: 300 câu hỏi Zalo lẫn vào 300 câu test UIT-VSFC, tham chiếu là train: AUROC **1.000**. Tham chiếu là 8 166 câu
train chủ đề giảng viên, test 2 435 câu chủ đề giảng viên hoặc cơ sở vật chất (145 câu): AUROC **0.940** (k = 1: 0.927, k = 50:
0.939).

**Gợi ý**: 5 điều gần nhất cho điều đúng của 300 câu ghim, 25 ms một lần trên 61 425 vector: **60.3%** cùng văn bản với điều
gốc; gợi ý ngẫu nhiên là 0.13%. Ví dụ `100/2019/nđ-cp+5` (xử phạt người điều khiển ô tô) gợi ý điều 6, 7, 8, 16, 23 cùng nghị
định.

## Đọc kết quả

- **Linear probe là baseline phải đánh bại.** Trên tập test đầy đủ, `bge-m3` + LogReg (0.770) vượt cả TF-IDF (0.716) lẫn BiLSTM
  tự train (0.755), với 0.8 giây train và không GPU. Trên 150 câu ghim cân bằng của module 11, nó (0.761) thấp hơn prompting
  `qwen2.5:3b` (0.804): tập ghim có 1/3 neutral, đúng lớp mà dữ liệu train chỉ có 4% nên LogReg học yếu. Centroid "không biết"
  tần suất lớp nên đứng tốt trên tập cân bằng (0.782) và tệ trên tập lệch (0.706). Con số phụ thuộc phân phối tập đánh giá
  nhiều không kém phương pháp.
- **kNN và lớp hiếm**: láng giềng của một câu neutral phần lớn là câu khen hoặc chê có cùng chủ đề, nên bỏ phiếu chôn lớp
  neutral (F1 0.269). Muốn kNN công bằng hơn: trọng số theo tần suất lớp, hoặc dùng LogReg với `class_weight`.
- **Rò rỉ train/test**: gần một phần tư tập test có câu gần như y hệt trong train, và điểm trên nhóm đó cao hơn phần còn lại
  0.1. Không phải lỗi của bộ dữ liệu (phản hồi sinh viên lặp lại tự nhiên) nhưng là lý do báo cáo cả số trên phần "không
  trùng", và kiểm bản sao trước khi tin một con số test đẹp.
- **Bất thường dễ hay khó tuỳ khác biệt về nội dung**: câu hỏi pháp luật khác hẳn miền nên tách tuyệt đối; chủ đề cơ sở vật
  chất cùng miền, cùng văn phong với phản hồi về giảng viên nên AUROC 0.94, và k ít ảnh hưởng.
- **Gợi ý**: 60% cùng văn bản là thước đo thô (điều liên quan có thể ở văn bản khác, như thông tư hướng dẫn một nghị định) nhưng
  cho thấy embedding bắt được cấu trúc "cùng chủ đề pháp lý" mà không dùng metadata nào.

## Bẫy thường gặp

- Dựng ma trận cosine 11 426 × 11 426 một lần (522 MB `float32`, chưa kể bản sao trung gian): theo lô.
- `auroc` đảo chiều (điểm cao là bình thường) cho 1 - AUROC; không tính nửa cho bằng điểm làm sai khi điểm rời rạc.
- `recommend` gán `-inf` cho mục đã thích rồi lấy top-k: khi `k` lớn hơn số mục còn lại, mục đã thích vẫn lọt vào.
- So macro-F1 trên hai tập đánh giá khác phân phối (test đầy đủ lệch và 150 câu cân bằng) như thể cùng một thước đo.
