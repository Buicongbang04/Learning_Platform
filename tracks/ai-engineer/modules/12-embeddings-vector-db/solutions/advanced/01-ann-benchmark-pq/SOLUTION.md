# Hướng làm và rubric: PQ tự viết và chọn index theo ngân sách

Bài mở, không có một đáp án. Dưới đây là hướng làm, một bảng tham chiếu đo bằng bản lời giải giữ ngoài repo, và rubric.

## Hướng làm

**Hàm.** `pq_train` gọi k-means (khởi tạo như Basic 02) trên từng đoạn `x[:, j*ds:(j+1)*ds]` với `seed + j`, xếp thành mảng
`(m, ks, ds)`. `pq_encode`: với mỗi đoạn, khai triển L2 tới `ks` centroid rồi `argmin`, ép `uint8`. `pq_decode`: ghép
`codebooks[j][codes[:, j]]`. `pq_search`: bảng `table[j, s] = ‖q_j − C_j[s]‖²` shape `(m, ks)`, khoảng cách của cả corpus là
`table[np.arange(m)[None, :], codes].sum(1)`, sort ổn định. `pareto_front`: hai vòng lặp với hàm "trội" đúng định nghĩa (bằng
nhau ở cả ba thì không ai trội ai).

**Đo.** Train PQ trên một mẫu ngẫu nhiên 20 000 vector (seed ghim), encode cả 61 425. Rescoring: lấy top-100 theo ADC, xếp
lại bằng tích vô hướng với vector gốc. FAISS: `IndexFlatIP`, `IndexHNSWFlat`, `IndexIVFFlat`, `IndexPQ` (train trên cùng mẫu),
`IndexIVFPQ`, và `IndexRefineFlat` bọc IVF-PQ (phải bọc **trước** khi `add`: FAISS kiểm số vector của hai index bằng nhau).
Byte/vector lấy từ `faiss.serialize_index(index).nbytes / N` (gồm id, centroid, codebook) hoặc công thức; với rescoring ghi rõ
vector gốc nằm ở RAM hay trên đĩa.

## Bảng tham chiếu

PC của track, 4 luồng, gọi **từng câu một**, máy dùng chung (load 10 tới 13 lúc đo), 300 câu ghim
(`.superpowers/scratch/logs/adv01_ref.log`):

| Cấu hình | recall ANN@10 | Recall@10 (nhãn) | ms/câu | byte/vector | Dựng |
| --- | --- | --- | --- | --- | --- |
| Exact `IndexFlatIP` | 0.998 | 0.905 | 11.5 | 4 096 | 0.1 s |
| HNSW M=16, efC=100, ef=32 | 0.974 | 0.895 | 0.17 | 4 240 | 8.9 s |
| HNSW, ef=128 | 0.992 | 0.898 | 0.51 | 4 240 | |
| IVF nlist=256, nprobe=8 | 0.903 | 0.842 | 0.59 | 4 121 | 1.3 s |
| IVF, nprobe=32 | 0.962 | 0.898 | 2.34 | 4 121 | |
| PQ tự viết m=16 | 0.310 | 0.473 | 10.5 | 16 | 11.5 s |
| PQ tự viết m=16 + rescore 100 | 0.743 | 0.820 | 10.7 | 16 (+4 096 trên đĩa) | |
| PQ tự viết m=32 | 0.466 | 0.648 | 15.0 | 32 | 19.1 s |
| PQ tự viết m=32 + rescore 100 | 0.878 | 0.858 | 15.3 | 32 (+4 096) | |
| PQ tự viết m=64 | 0.678 | 0.847 | 25.2 | 64 | 38.6 s |
| PQ tự viết m=64 + rescore 100 | 0.986 | 0.905 | 25.3 | 64 (+4 096) | |
| FAISS `IndexPQ` m=16 / 32 / 64 | 0.305 / 0.484 / 0.670 | 0.457 / 0.687 / 0.830 | 0.76 / 1.28 / 2.30 | 33 / 49 / 81 | 2.2 / 3.6 / 4.2 s |
| `IndexIVFPQ` nlist=256, m=64, nprobe=32 | 0.658 | 0.852 | 0.57 | 106 | 10.1 s |
| `IndexRefineFlat`(IVF-PQ), k_factor=10 | 0.943 | 0.892 | 0.67 | 4 202 | 10.4 s |

Khi tính byte/vector theo RAM (vector gốc của rescoring trên đĩa), biên Pareto gồm: các PQ thuần (ít byte nhất), IVF-PQ,
HNSW ef=32 và ef=128 (nhanh nhất ở recall cao), IVF-PQ + refine; exact chỉ còn trên biên nhờ recall 0.998.

Điều cần thấy trong bảng:

- PQ tự viết và `IndexPQ` cùng `m` cho recall gần nhau (0.678 và 0.670 ở m=64): cùng thuật toán. FAISS nhanh hơn 10 lần (bảng
  ADC tính bằng SIMD, mã 8 bit duyệt trong C++). Byte/vector của FAISS lớn hơn `m` vì id 8 byte và codebook chia đều.
- Recall của PQ thuần thấp nhưng **rescoring** đưa m=64 lên 0.986 và Recall@10 theo nhãn bằng exact: PQ là bộ lọc ứng viên tốt,
  không phải bộ xếp hạng cuối.
- IVF-PQ có trần recall khoảng 0.66 (sai số lượng tử); `IndexRefineFlat` k_factor 10 lên 0.943 với 0.67 ms nhưng cần giữ
  vector gốc để xếp lại.
- Recall@10 theo nhãn kém nhạy hơn recall ANN rất nhiều: PQ m=64 thuần mất 0.32 recall ANN nhưng chỉ 0.06 Recall@10.

## Ba kịch bản (một lời giải hợp lý)

- **(a) Laptop 8 GB, p95 dưới 20 ms**: 61 425 × 4 KB = 252 MB. Exact đã đạt (11.5 ms một câu, 4.7 ms khi gom lô) và không có
  tham số; HNSW M=16 ef=128 nếu muốn dư độ trễ cho phần còn lại của pipeline (thêm 9 giây dựng, 144 byte/vector). Không cần nén.
- **(b) 10 triệu vector trên 32 GB**: `float32` là 41 GB, HNSW thêm khoảng 1.4 GB đồ thị: không vừa. Int8 (SQ8) còn 10 GB + đồ
  thị: vừa, recall gần như không đổi (mục 5 lý thuyết đo SQ8 0.995). Hoặc IVF-PQ m=64 (khoảng 1 GB) + rescoring từ vector gốc
  trên SSD, nhắm recall ANN ≥ 0.9 như dòng refine ở trên. Cần nói rõ đánh đổi: SQ8 + HNSW đơn giản và recall cao; IVF-PQ +
  refine rẻ RAM nhất nhưng mỗi query đọc đĩa.
- **(c) recall ≥ 0.99 và cập nhật hằng ngày**: HNSW ef=128 (0.992) chịu thêm nút tốt; xoá đánh dấu và dựng lại định kỳ (9 giây ở
  quy mô này). Hoặc exact (0.998, thêm/xoá tức thì). IVF cần nprobe rất cao để tới 0.99 và centroid lệch dần khi dữ liệu đổi.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Hàm PQ và `pareto_front` | 15 | Test pass; `pq_search` dùng bảng ADC, không giải nén cả corpus mỗi query |
| Bảng đo | 25 | Đủ các nhóm (exact, HNSW ≥ 2, IVF ≥ 2, PQ tự viết ≥ 2 m, rescoring, IVF-PQ); có cả recall ANN và Recall@10 theo nhãn; điều kiện đo ghi rõ (từng câu hay lô, số luồng, máy dùng chung) |
| Biên Pareto và biểu đồ | 15 | Biên khớp bảng; hai biểu đồ có nhãn trục, đơn vị, đánh dấu điểm trên biên; nói rõ byte tính theo RAM hay gồm cả đĩa |
| PQ tự viết so với FAISS | 10 | So cùng `m`, cùng mẫu train; giải thích chênh tốc độ (SIMD, Python) và byte (id, codebook) |
| Ba kịch bản | 25 | Mỗi kịch bản có phép tính bộ nhớ ra số, chọn một điểm từ bảng, nói đánh đổi và điều kiện làm lựa chọn sai |
| Trung thực và tái lập | 10 | Seed ghim, số khớp notebook, nêu giới hạn (300 câu, một máy, một corpus) |
