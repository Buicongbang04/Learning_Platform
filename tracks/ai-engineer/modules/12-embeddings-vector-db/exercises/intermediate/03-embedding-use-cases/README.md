---
title: Embedding ngoài search - phân loại, trùng lặp, bất thường, gợi ý
level: intermediate
services: []
files:
  - path: starter/usecases.ipynb
    note: 8 hàm TODO
  - path: tests/test_usecases.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/03-embedding-use-cases/starter/usecases.ipynb
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/03-embedding-use-cases -q
---

## Mục tiêu

Dùng cùng một embedding cho bốn việc ngoài semantic search, mỗi việc ra một con số: phân loại cảm xúc UIT-VSFC (so với
mốc của module 04 và module 11), tìm câu trùng gần đúng và rò rỉ train/test, phát hiện bất thường bằng khoảng cách kNN
(AUROC), và gợi ý điều luật liên quan. Làm xong bạn biết khi nào "embedding + một lớp tuyến tính" là baseline đáng đánh
bại trước khi nghĩ tới LLM, và đo được bản sao giữa train và test ảnh hưởng con số test thế nào.

## Đề bài

**Phần cứng:** CPU · ~100 phút

Ngoài thời gian làm bài: embed 16 175 câu UIT-VSFC qua Ollama mất vài phút (cache ở `data/raw/uit-vsfc/cache/bge-m3-*.npy`);
phần gợi ý dùng cache Zalo của bài Intermediate 01. Khi đã có cache, cả notebook chạy khoảng 1 phút.

Mở `starter/usecases.ipynb`. Mọi vector đã chuẩn hoá L2. Notebook mô tả chính xác từng hàm; tóm tắt:

1. Phân loại: `class_centroids`, `predict_centroid` (centroid gần nhất), `knn_predict` (bỏ phiếu `k` láng giềng, hoà
   thì tổng cosine, rồi nhãn nhỏ; tính theo lô). Logistic regression của scikit-learn nằm ở cell `explore`.
2. Trùng lặp: `near_duplicates(x, threshold)` (mọi cặp `i < j`, sắp xếp quy định), `nearest_in(ref, x)`.
3. Bất thường: `knn_anomaly_scores(ref, x, k)` và `auroc(scores, labels)` tự viết theo thứ hạng.
4. Gợi ý: `recommend(x, liked, k)` theo hồ sơ là trung bình chuẩn hoá, bỏ mục đã thích.

Rồi chạy các cell `explore`: ba bộ phân loại trên toàn bộ test và trên 150 câu ghim của module 11
(`sample(50, random_state=0)` mỗi nhãn), trùng lặp trong train và giữa test với train, hai bài toán bất thường, và gợi ý
5 điều liên quan cho điều đúng của 300 câu hỏi Zalo ghim. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `class_centroids` chuẩn hoá trung bình, lớp rỗng là vector 0; `predict_centroid` chọn cosine lớn nhất.
- `knn_predict` đúng ở các ví dụ tính tay kể cả hai kiểu hoà, cho cùng kết quả với mọi kích thước lô, đúng trên
  `FakeLLM.embed`.
- `near_duplicates` đúng thứ tự, gồm cả cặp có cosine bằng đúng ngưỡng, không tự ghép một câu với chính nó;
  `nearest_in` chọn chỉ số nhỏ khi cách đều.
- `knn_anomaly_scores` khớp giá trị tính tay; `auroc` tính một nửa cho bằng điểm, khớp `roc_auc_score` trên dữ liệu ngẫu
  nhiên, không đảo chiều.
- `recommend` không gợi ý lại mục đã thích, kể cả khi `k` lớn hơn số mục còn lại.

## Gợi ý

### Gợi ý 1

`np.bincount(nhãn, weights=..., minlength=n_classes)` đếm phiếu và cộng cosine theo lớp trong một dòng mỗi thứ. Với
`near_duplicates` theo lô, chỉ số dòng trong lô phải cộng thêm vị trí bắt đầu của lô trước khi so với chỉ số cột.

### Gợi ý 2

AUROC bằng xác suất một mẫu dương ngẫu nhiên có điểm cao hơn một mẫu âm ngẫu nhiên. So mọi cặp (dương, âm) bằng
broadcasting là đủ cho vài nghìn mẫu; đếm riêng số cặp bằng điểm.
