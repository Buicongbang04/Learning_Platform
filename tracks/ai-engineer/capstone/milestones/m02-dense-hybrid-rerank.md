# M02: Retrieval bằng embedding, hybrid và reranking, so với baseline

## Mục tiêu

Biết **bằng số** retrieval nào nên đứng sau trợ lý: dense `bge-m3`, hybrid BM25 + dense bằng RRF, có thêm reranker hay
không. Mỗi cấu hình được so với baseline M01 trên cùng 300 câu ghim, mọi tham số chọn trên tập dev từ split train, và
mỗi kết luận đi kèm số câu thật sự thay đổi chứ không chỉ chênh lệch trung bình.

Dùng lại: embedding và vector DB của [module 12](../../modules/12-embeddings-vector-db/README.md) (bài Intermediate 02
cho bạn chọn công cụ lưu vector), dense/hybrid/RRF/rerank của [module 13](../../modules/13-rag/README.md) mục 3, 4 và
các bài Intermediate 01, 03. Cache vector `bge-m3` của module 13 (`data/raw/zalo-legal/cache/bge-m3.npy` cùng
`bge-m3.ids.json`) dùng lại được: chỉ cần kiểm danh sách id khớp đúng corpus.

**Phần cứng:** CPU + Ollama (`bge-m3`), reranker trên GPU 4GB; khoảng 6 tới 8 giờ làm. Embed toàn corpus mất khoảng 45
phút trên laptop GPU 4GB nếu chưa có cache.

## Việc cần làm

1. **Tập dev**: 300 câu đầu của split train, bỏ các `query-id` có trong `qrels/test.jsonl`. Mọi lựa chọn (trọng số RRF,
   số ứng viên đưa vào rerank, có dùng bigram không) chọn trên tập này.
2. **Dense** (`fusion.py`): `normalize_rows`, `dense_top_k`. Embed câu hỏi bằng cùng model và cùng chuẩn hoá như lúc
   embed corpus. Đếm số dòng hỏng của ma trận và số điều dài hơn giới hạn ngữ cảnh của `bge-m3` qua Ollama (module 13
   mục 2).
3. **Hybrid**: `rrf` có trọng số. Đo RRF của BM25 âm tiết + dense và BM25 bigram + dense. Thử vài trọng số cho nhánh
   dense **trên dev**, chọn một, rồi chạy **một lần** trên tập ghim.
4. **Rerank**: cross-encoder `BAAI/bge-reranker-v2-m3` trên top-20 của hybrid tốt nhất (cả điều, cắt 512 token). Đo
   chất lượng, độ trễ mỗi câu và VRAM. Không có GPU thì chạy trên 50 câu đầu và ghi rõ.
5. **Phân tích theo cặp**: với từng cặp phương pháp, đếm số câu chỉ nhánh A có điều đúng trong top-10, chỉ nhánh B,
   cả hai, không nhánh nào. Với rerank: số câu điều đúng đầu tiên lên hạng, tụt hạng, giữ nguyên. Đọc ít nhất 5 câu
   mỗi loại "chỉ một nhánh cứu được" và 5 câu rerank làm tụt.
6. **Lưu trữ**: chọn một công cụ của module 12 (FAISS, Chroma, Qdrant, LanceDB, pgvector hoặc numpy) cho vector corpus,
   giải thích lựa chọn bằng số của module 12 (thời gian nạp, p95, lọc metadata). Với 61 425 vector, kNN chính xác bằng
   numpy vẫn là một phương án hợp lệ; nói rõ khi nào nó hết hợp lệ.
7. Cập nhật `reports/RETRIEVAL.md`: bảng so sánh, bảng theo cặp, độ trễ, khuyến nghị cấu hình cho M03.

## Kết quả nộp

- `legal_assistant/fusion.py`, test M02 pass; `scripts/m02_retrieval.py` và log.
- Bảng BM25 / dense / hybrid / hybrid + rerank trên 300 câu ghim, kèm kết quả dev dùng để chọn tham số.
- Phân tích lỗi theo cặp và khuyến nghị cấu hình cho M03 trong `reports/RETRIEVAL.md`.

## Tiêu chí đạt

- [ ] Bảng có ít nhất 5 dòng (BM25 âm tiết, BM25 bigram, dense, hybrid tốt nhất, hybrid + rerank) với R@1, R@5, R@10,
      R@20, MRR@10 trên đúng 300 câu ghim.
- [ ] Mọi tham số được chọn trên dev; báo cáo có bảng dev và câu nói rõ tập ghim chỉ chạy một lần cho cấu hình đã chọn.
- [ ] Hybrid tốt nhất của bạn đạt R@10 ≥ 0.91 và MRR@10 ≥ 0.73 (bản tham chiếu 0.925 và 0.750). Thấp hơn thì báo cáo chỉ
      ra nguyên nhân bằng số (nhánh nào yếu, ở câu nào).
- [ ] Mỗi khẳng định "A tốt hơn B" có số câu A thắng, B thắng; chênh lệch dưới khoảng 3 câu không được gọi là cải thiện.
- [ ] Rerank có số chất lượng, độ trễ p50/p95 mỗi câu và VRAM; kết luận "có dùng rerank không" theo số, kể cả khi số âm.

### Số tham chiếu

Bản cài đặt của người soạn, PC của track (Ollama `bge-m3` cho câu hỏi, cache vector corpus của module 13, GPU dùng chung
với một tiến trình khác). Hybrid lấy top-100 mỗi nhánh, RRF `k = 60`.

| Phương pháp | R@1 | R@5 | R@10 | R@20 | MRR@10 | nDCG@10 |
| --- | --- | --- | --- | --- | --- | --- |
| BM25 âm tiết (M01) | 0.433 | 0.767 | 0.837 | 0.867 | 0.574 | 0.638 |
| BM25 âm tiết + bigram (M01) | 0.523 | 0.837 | 0.882 | 0.922 | 0.658 | 0.714 |
| Dense `bge-m3` | 0.600 | 0.862 | 0.905 | 0.925 | 0.707 | 0.755 |
| RRF(BM25 âm tiết, dense) | 0.567 | 0.852 | 0.915 | 0.948 | 0.691 | 0.746 |
| RRF(BM25 bigram, dense) | **0.630** | **0.898** | **0.925** | **0.962** | **0.750** | **0.793** |
| RRF(BM25 bigram, dense) + rerank top-20 | 0.617 | 0.855 | 0.905 | 0.962 | 0.728 | 0.771 |

- Trọng số nhánh dense chọn trên dev (1.0; 1.5; 2.0; 3.0): 1.0 cho MRR@10 dev cao nhất (0.733), nên hybrid cuối là RRF
  không trọng số.
- Top-10 của BM25 bigram và dense: cả hai có điều đúng 258 câu, chỉ BM25 bigram 7, chỉ dense 14, không nhánh nào 21.
  Với BM25 âm tiết thay cho bigram: 244 / 7 / 28 / 21.
- Rerank (fp16 trên GPU, 0.33 giây mỗi câu cho 20 cặp, VRAM đỉnh 1.3 GiB): điều đúng đầu tiên lên hạng ở 49 câu, tụt
  ở 65 câu, giữ nguyên ở 175 câu.
- Embed 300 câu hỏi khoảng 3 giây; dense search trên 61 425 vector khoảng 10 ms mỗi câu (numpy, 4 luồng).

Hai điều đáng chú ý trong bảng, bạn nên tự kiểm lại trên số của mình: hybrid với BM25 âm tiết **thua** dense ở R@1 và
MRR (nhánh yếu kéo thứ hạng xuống, như module 13 đã thấy), nhưng hybrid với BM25 bigram thắng dense ở mọi cột; và
reranker nổi tiếng **làm tệ đi** top-k trên bộ này. Đừng chép kết luận của người khác về rerank mà không đo.
Số dense và hybrid có thể lệch ở chữ số thứ ba giữa các máy vì vector câu hỏi qua Ollama không hoàn toàn tất định.

## Gợi ý

- Hai danh sách xếp hạng đưa vào RRF phải cùng loại id (uid điều). Nếu sau này bạn index theo khoản, gộp điểm lên điều
  bằng `max_by_article` trước khi so với qrels.
- Tách việc embed khỏi việc đánh giá: lưu vector câu hỏi dev và ghim ra đĩa, để thử trọng số RRF mất vài giây thay vì
  gọi lại Ollama.
- Rerank trên CPU chậm hơn GPU hàng chục lần (module 13 mục 4). Batch mọi cặp của một câu, cắt độ dài tài liệu, và đo
  độ trễ tách khỏi thời gian nạp model.
- Khi một cải tiến thắng trung bình mà thua ở nhiều câu, nhìn xem những câu bị thua có chung đặc điểm gì (cùng văn bản
  dài, cùng loại câu hỏi mức phạt): đó thường là thông tin quý hơn con số trung bình.
