# Câu hỏi phỏng vấn: Embeddings & Vector Database

## Embedding của câu được tạo ra và train thế nào? Vì sao cosine 0.5 không có nghĩa là "giống một nửa"?

Một Transformer encoder cho mỗi token một vector theo ngữ cảnh, rồi **pooling** (CLS hoặc trung bình các token) gộp thành
một vector cho cả đoạn, thường kèm chuẩn hoá L2. Encoder được train **contrastive**: với lô gồm cặp (câu hỏi, đoạn đúng),
loss InfoNCE kéo cặp đúng lại gần và đẩy mọi đoạn khác trong lô ra xa, chia cosine cho nhiệt độ nhỏ.

Loss chỉ quan tâm **thứ tự** (đoạn đúng phải gần hơn đoạn sai), không quan tâm giá trị tuyệt đối. Thực tế embedding dồn vào
một hình nón hẹp (anisotropy): với `bge-m3`, hai điều luật ngẫu nhiên có cosine trung bình 0.50, hai phản hồi sinh viên
ngẫu nhiên 0.57; với `nomic-embed-text` con số là 0.73. Hệ quả: mọi ngưỡng (trùng lặp, từ chối, bất thường) phải chọn từ
phân phối điểm của chính model và dữ liệu, và chọn lại khi đổi model.

Ứng viên tốt nói thêm pooling là một phần của model: dùng mean pooling cho model train với CLS vẫn ra vector, chỉ tệ hơn
một cách im lặng.

## Bạn chọn embedding model cho một hệ thống tiếng Việt thế nào?

1. Lọc ứng viên theo **ngôn ngữ** (tokenizer và dữ liệu train), **độ dài tối đa**, **số chiều**, giấy phép, chạy ở đâu,
   chi phí. MTEB là để lọc ứng viên, không phải để quyết định.
2. Kiểm vài cặp câu tối thiểu trong ngôn ngữ thật. Ví dụ đo trong module: với `nomic-embed-text` **chạy qua Ollama**
   (GGUF), "giảng viên dạy **rất** nhiệt tình", "... **không** nhiệt tình" và "... **hơi** nhiệt tình" cho cosine đúng bằng 1,
   nhiều khả năng vì tokenizer của bản port biến các âm tiết có dấu thành cùng một token `[UNK]`; tokenizer gốc trên Hugging
   Face thì bỏ dấu và tách ba câu khác nhau. Bỏ dấu thì bản Ollama lại phân biệt được. `bge-m3` (đa ngôn ngữ) cho 0.766 và
   0.950. Bài học: kiểm trên đúng runtime sẽ chạy production, không chỉ trên tên model.
3. Đo trên **tập đánh giá của chính bạn** (Recall@k, MRR với retrieval; macro-F1 với phân loại), cùng throughput và bộ nhớ.
4. Kiểm hành vi khi văn bản dài: `bge-m3` qua Ollama cắt im lặng ở 4 096 token; `nomic-embed-text` qua Ollama báo HTTP 400.
   Cả hai đều cần chunking, nhưng lỗi im lặng nguy hiểm hơn.

## Cosine, dot product hay L2? Chuẩn hoá có quan trọng không?

Với vector đơn vị, $$\lVert a - b\rVert^2 = 2 - 2\cos(a, b)$$ và dot bằng cosine, nên **ba độ đo cho cùng thứ hạng**. Cách làm
chuẩn: chuẩn hoá L2 một lần lúc index và lúc query, dùng inner product (nhanh nhất).

Khi vector chưa chuẩn hoá thì khác hẳn: dot thưởng vector dài, L2 phạt vector dài. Thí nghiệm trong module: nhân mỗi vector
`bge-m3` của corpus Zalo với một số ngẫu nhiên trong $$[0.5, 2]$$ rồi tìm bằng dot, Recall@10 tụt từ 0.905 xuống 0.193.

Bẫy vận hành: Chroma và LanceDB mặc định **L2**; pgvector chọn metric theo toán tử (`<->` L2, `<#>` âm inner product, `<=>`
cosine distance) và index chỉ được dùng khi toán tử khớp opclass; mỗi công cụ trả "khoảng cách" hay "điểm" theo quy ước
riêng. Một số model cố ý **không** chuẩn hoá và dùng dot (độ dài mang thông tin, ví dụ độ phổ biến trong gợi ý): khi đó
dùng đúng metric model được train.

## Khi nào bạn KHÔNG cần vector database?

- Dưới vài trăm nghìn vector, chỉ đọc, lưu lượng vừa: numpy hoặc `IndexFlatIP` exact. 61 425 vector 1 024 chiều mất 4.7 ms
  mỗi câu khi gom lô, 14 ms khi gọi lẻ, không tham số, không sai số.
- Đã có Postgres và cần transaction, join với dữ liệu nghiệp vụ: pgvector trong chính Postgres đó, thay vì thêm một hệ thống
  phải đồng bộ.
- Batch offline (dedup, gom nhóm hằng đêm): FAISS trong một job.

Cần vector DB khi có ít nhất hai trong: hàng triệu vector, lọc metadata và phân quyền, cập nhật liên tục, nhiều service
cùng đọc, yêu cầu sẵn sàng cao.

## Giải thích HNSW. Ba tham số M, efConstruction, efSearch làm gì?

Đồ thị láng giềng nhiều tầng như skip list. Mỗi nút có tầng cao nhất $$\lfloor -\ln(u)/\ln M \rfloor$$, nên tầng trên thưa và có
cạnh dài. Tìm: bắt đầu từ entry point ở tầng cao nhất, đi tham lam tới nút gần query nhất ở mỗi tầng rồi xuống tầng dưới;
ở tầng 0 chạy beam search với độ rộng `efSearch`.

- **M**: số láng giềng mỗi nút (2M ở tầng 0). Tăng thì recall tốt hơn ở cùng ef, tốn bộ nhớ hơn (khoảng 8M byte mỗi
  vector cho id láng giềng) và dựng chậm hơn.
- **efConstruction**: độ rộng beam lúc chèn, chất lượng đồ thị đổi lấy thời gian dựng.
- **efSearch**: núm vặn recall theo độ trễ **lúc chạy**, không cần dựng lại.

Số đo trong module (FAISS, 61 425 vector `bge-m3`, M=32): efSearch 16 cho recall ANN 0.950 ở 0.28 ms, efSearch 128 cho
0.997 ở 1.16 ms, so với 13.9 ms của exact. Ứng viên giỏi nhắc **heuristic chọn láng giềng**: giữ ứng viên chỉ khi nó gần nút
gốc hơn gần mọi láng giềng đã chọn, để giữ cạnh nối giữa các cụm; và nhắc HNSW xoá bằng đánh dấu, đồ thị xấu dần.

## IVF và HNSW khác nhau thế nào? Khi nào chọn cái nào?

| | IVF | HNSW |
| --- | --- | --- |
| Cấu trúc | k-means chia ô, mỗi ô một danh sách | Đồ thị láng giềng nhiều tầng |
| Cần train | Có (k-means), train lại khi dữ liệu trôi | Không |
| Bộ nhớ thêm | Rất ít (centroid, id) | Khoảng 8M byte mỗi vector |
| Núm vặn lúc chạy | `nprobe` | `efSearch` |
| Thêm, xoá | Thêm dễ, xoá dễ; cụm lệch dần | Thêm tốn, xoá bằng đánh dấu |
| Ghép nén | Rất hợp (IVF-PQ, tỉ số nén lớn) | Có (HNSW + SQ/PQ) nhưng đồ thị vẫn chiếm RAM |

Chọn HNSW khi cần recall cao, độ trễ thấp, đủ RAM. Chọn IVF (thường IVF-PQ) khi bộ nhớ là ràng buộc chính hoặc quy mô rất
lớn, chấp nhận recall thấp hơn hoặc thêm rescoring. Trên corpus của module, IVF 1 024 cụm cần `nprobe = 64` để tới recall
0.98, khi đó chậm hơn HNSW ở cùng recall.

## Product Quantization là gì? Vì sao recall của IVF-PQ có trần?

Chia vector thành $$m$$ đoạn, mỗi đoạn lượng tử hoá bằng 256 centroid học bằng k-means; vector lưu thành $$m$$ byte. Khoảng
cách tới query tính bằng bảng tra (ADC): một bảng $$m \times 256$$ cho mỗi query, mỗi vector chỉ còn $$m$$ phép tra và cộng.

Recall có trần vì khoảng cách tính trên vector **xấp xỉ**: tăng `nprobe` chỉ quét thêm cụm, không bớt sai số lượng tử. Đo
trong module: IVF-PQ $$m = 64$$ (157 byte mỗi vector so với 4 096) dừng ở recall ANN khoảng 0.63 dù tăng `nprobe` từ 16 lên 64.
Cách lấy lại: **rescoring** top vài trăm bằng vector gốc (trên đĩa), tăng $$m$$, hoặc dùng int8 (nén 4 lần, recall 0.995).

## Recall của ANN khác Recall@k của retrieval thế nào? Nên báo cáo cái nào?

Recall của ANN so index xấp xỉ với kNN chính xác trên **cùng** vector: đo index. Recall@k của retrieval so với tài liệu đúng
theo nhãn: đo cả hệ thống (embedding, chunking, index). Báo cả hai. Chúng không tỉ lệ thuận: trong module, HNSW efSearch 16
mất 0.05 recall ANN nhưng chỉ mất 0.027 Recall@10 theo nhãn (0.905 xuống 0.878), vì láng giềng bị sót thường ở cuối top-10.
Ngược lại, tối ưu recall ANN từ 0.99 lên 0.999 thường không đổi gì với người dùng; đổi embedding model mới đổi.

## Lọc theo metadata với ANN khó ở đâu?

- **Post-filter** (tìm top-k' rồi lọc) trả ít hơn k, thậm chí rỗng, khi bộ lọc chặt; tăng k' chỉ giảm vấn đề.
- **Pre-filter** (lọc rồi tìm chính xác) đúng nhưng chậm khi tập khớp lớn.
- **Lọc trong lúc duyệt** đồ thị: đúng hơn, nhưng với bộ lọc rất chặt đồ thị "nhìn qua bộ lọc" bị đứt; Qdrant dùng payload
  index và tự chuyển sang quét phẳng khi ước lượng tập khớp nhỏ, pgvector 0.8 có iterative index scan.

Với phân quyền, lọc phải nằm **trong** truy vấn ở tầng retrieval, có test tự động rằng không chunk trái quyền nào lọt ra.
Không bao giờ dựa vào LLM để "bỏ qua tài liệu không được phép".

## Dùng embedding cho phân loại thế nào, và khi nào nó thắng prompting LLM?

Ba cách, từ rẻ tới mạnh: centroid mỗi lớp (cosine tới trung bình), kNN bỏ phiếu, và **linear probe** (logistic regression
trên embedding). Linear probe train vài giây trên CPU, dự đoán dưới mili giây, chi phí gần như chỉ là embed câu.

Thắng prompting khi có vài nghìn nhãn, lưu lượng lớn, cần độ trễ thấp và ổn định (không phụ thuộc chữ LLM sinh ra). Prompting
thắng khi không có nhãn, nhãn thay đổi thường xuyên, hoặc cần lập luận. Bẫy: embedding bắt **chủ đề** mạnh hơn **cực tính**
(câu phủ định có cosine với câu gốc gần ngang một câu cùng nghĩa), nên zero-shot bằng cosine tới mô tả nhãn thường kém; lớp hiếm (neutral chỉ 5% UIT-VSFC)
là nơi các phương pháp không train tụt nhiều nhất. Luôn kiểm rò rỉ: tìm câu test có bản sao gần đúng trong train và báo số riêng cho hai nhóm.

## Đổi embedding model cho một index đang phục vụ: bạn làm thế nào?

Vector của hai model không so được với nhau (khác cả số chiều), nên không có "cập nhật dần tại chỗ":

1. Index B mới, tên có phiên bản model; **ghi kép** dữ liệu mới vào A và B.
2. **Backfill** B từ nguồn (đọc cache theo hash nội dung nếu có). Ước lượng thời gian từ throughput đo được: 61 425 điều
   mất khoảng 47 phút ở 15 tới 28 điều mỗi giây trên GPU dùng chung; 10 triệu chunk ở cùng tốc độ là gần 5 ngày, nên cần
   nhiều GPU hoặc batch lớn.
3. Đánh giá B trên tập ghim (Recall@k, MRR) và **shadow read** trên lưu lượng thật (so kết quả, độ trễ).
4. Chuyển alias đọc sang B khi đạt tiêu chí đặt trước; giữ A vài ngày để **rollback**; rồi dừng ghi kép và xoá A.

Câu hỏi được truy vấn bằng model nào thì phải dùng index của model đó: router đọc theo alias, không theo cấu hình rải rác.

## Thiết kế hệ thống: semantic search cho 50 triệu sản phẩm, p95 dưới 50 ms, lọc theo danh mục và tồn kho.

Làm rõ: số chiều, QPS cao điểm, tần suất cập nhật tồn kho (giây hay giờ), độ chặt của bộ lọc, ngôn ngữ.

- **Bộ nhớ**: 50 triệu × 1 024 × 4 byte = 205 GB `float32`. Giảm số chiều (model 384 tới 768 chiều, hoặc Matryoshka), nén int8
  (4 lần) hoặc PQ/nhị phân kèm rescoring; phân mảnh theo id trên nhiều node, mỗi node HNSW hoặc IVF-PQ.
- **Lọc**: danh mục là payload có index; tồn kho đổi liên tục nên **không** nhúng vào vector, cập nhật payload riêng (Qdrant
  cho cập nhật payload không đụng vector) hoặc lọc ở tầng sau với over-fetch có giới hạn và đo tỉ lệ thiếu kết quả.
- **Độ trễ**: embed query trên GPU (5 tới 10 ms), ANN song song trên các shard (10 tới 20 ms), gộp top-k, rerank nhẹ nếu còn
  ngân sách. Cache query phổ biến.
- **Cập nhật**: sản phẩm mới qua queue, embed theo lô, upsert; dựng lại index định kỳ để dọn nút đánh dấu xoá.
- **Chất lượng**: tập truy vấn có nhãn (click, mua), đo Recall@k và recall ANN; hybrid với BM25 cho mã sản phẩm, tên thương
  hiệu (dense yếu với khớp chính xác).
- Giám sát p95 theo shard, recall ANN trên mẫu so với exact, độ tươi index.

## Thiết kế hệ thống: phát hiện câu hỏi trùng trên một diễn đàn hỏi đáp tiếng Việt, 2 triệu câu, mỗi ngày 20 000 câu mới.

- **Embedding**: model đa ngôn ngữ kiểm trên tiếng Việt có dấu (mục 1 của module); câu hỏi ngắn nên embed nhanh.
- **Ứng viên**: với mỗi câu mới, ANN top-20 trên index HNSW của 2 triệu câu (8 GB `float32` 1 024 chiều, hoặc 2 GB int8).
- **Quyết định**: ngưỡng cosine chọn trên một tập cặp người gán nhãn (trùng / không trùng), theo precision mục tiêu, vì ngưỡng
  phụ thuộc model (cặp ngẫu nhiên đã có cosine trung bình 0.5 tới 0.7 tuỳ model); vùng xám đưa cho cross-encoder hoặc LLM
  xác nhận, hoặc hỏi người đăng "có phải câu này không?".
- **Bẫy**: phủ định và con số ("có được" và "không được", "năm 2019" và "năm 2024") gần nhau trong không gian embedding, nên
  cần tầng xác nhận; trùng **từng ký tự** xử lý rẻ hơn bằng hash trước.
- **Đo**: precision và recall trên cặp có nhãn, tỉ lệ người dùng chấp nhận gợi ý, độ trễ đăng bài.
- **Offline**: dedup toàn kho một lần bằng ANN theo lô (không phải 2 triệu bình phương cặp), gom thành cụm bằng union-find.
