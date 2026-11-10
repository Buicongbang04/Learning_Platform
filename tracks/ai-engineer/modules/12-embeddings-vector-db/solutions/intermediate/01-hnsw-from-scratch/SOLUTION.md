# Lời giải: HNSW tự viết

## Cách làm

**`random_level`** là một dòng theo công thức; dùng `1 - u` vì `rng.random()` có thể trả đúng 0.

**`search_layer`** giữ hai heap: `candidates` (min-heap theo khoảng cách, nút còn phải mở rộng) và `best` (max-heap qua
khoảng cách âm, tối đa `ef` phần tử). Khởi tạo cả hai bằng các điểm vào (tính khoảng cách một lần cho cả danh sách), cắt
`best` về `ef`. Vòng lặp: lấy ứng viên gần nhất; nếu nó **xa hơn hẳn** phần tử xa nhất của `best` thì dừng (dùng `>`, không
phải `>=`: với `>=`, đồ thị dựng tay của test dừng sớm ở hai nút cách đều); lấy các láng giềng chưa thăm, đánh dấu thăm, tính
khoảng cách **một lần cho cả lô** qua `dist`, đẩy những láng giềng đủ gần vào cả hai heap. Trả `sorted` của `best` đổi dấu.

**`select_neighbors`**: chế độ đơn giản là `m` id đầu. Heuristic: duyệt ứng viên đã sắp, giữ `e` nếu danh sách chọn còn rỗng
hoặc `d(gốc, e)` nhỏ hơn mọi `d(e, r)` với `r` đã chọn (một lời gọi `dist(vectors[e], chosen)`), dừng khi đủ `m`.

**`_insert`** theo đúng Algorithm 1: đăng ký nút ở mọi tầng của nó; đi tham lam (`ef = 1`) từ tầng của entry point xuống
tầng `level + 1`; ở mỗi tầng từ `min(level, top)` xuống 0, `search_layer` với `ef_construction`, chọn `M` láng giềng, nối hai
chiều, tỉa láng giềng nào vượt `max_degree(lc)` bằng `select_neighbors` trên danh sách của nó sắp theo khoảng cách **tới
nó**; điểm vào tầng dưới là mọi kết quả `found`. Nút mới thành entry point chỉ khi tầng của nó **lớn hơn hẳn**.

**`search`**: tham lam xuống tới tầng 1, rồi beam search `max(ef, k)` ở tầng 0.

## Kết quả thật

PC của track, numpy 4 luồng, 300 câu hỏi ghim (`.superpowers/scratch/logs/hnsw_results.txt`). Dữ liệu sinh 20 cụm × 100
điểm, M = 8, efConstruction = 40:

| | ef = 10 | ef = 40 |
| --- | --- | --- |
| heuristic | 0.950 | 1.000 |
| chọn m gần nhất | 0.842 | 0.884 |

20 000 điều đầu của Zalo Legal, `bge-m3`. HNSW tự viết M = 16, efConstruction = 100: dựng **275 s**, 5 tầng (20 000, 1 235,
91, 5, 1 nút), bậc trung bình tầng 0 là 17.4. IVF tự viết nlist = 128: dựng 0.9 s, danh sách từ 15 tới 368 vector (trung
vị 146). Exact (numpy, cả lô): 1.40 ms/câu, 20 000 khoảng cách mỗi câu.

| Index | Tham số | recall ANN@10 | ms/câu | Khoảng cách/câu |
| --- | --- | --- | --- | --- |
| HNSW tự viết | ef = 10 | 0.816 | 0.57 | 257 |
| | ef = 20 | 0.909 | 0.83 | 377 |
| | ef = 40 | 0.960 | 1.30 | 579 |
| | ef = 80 | 0.988 | 2.21 | 933 |
| | ef = 160 | 0.997 | 3.97 | 1 543 |
| IVF tự viết | nprobe = 1 | 0.556 | 0.44 | 178 |
| | nprobe = 4 | 0.799 | 1.22 | 660 |
| | nprobe = 8 | 0.869 | 2.29 | 1 264 |
| | nprobe = 16 | 0.926 | 5.00 | 2 528 |
| | nprobe = 32 | 0.966 | 11.63 | 5 153 |
| FAISS HNSW (cả lô) | efSearch = 40 | 0.965 | 0.05 | |
| | efSearch = 160 | 0.993 | 0.16 | |
| FAISS IVF (cả lô) | nprobe = 8 | 0.887 | 0.11 | |
| | nprobe = 32 | 0.974 | 0.43 | |

FAISS dựng HNSW cùng tham số trong 2.3 s (khoảng 120 lần nhanh hơn bản Python), IVF trong 0.3 s. Trên cả 61 425 điều (exact
4.9 ms/câu cả lô): FAISS HNSW efSearch 40 cho 0.980, efSearch 160 cho 0.993; IVF nlist 256 nprobe 8 cho 0.903, nprobe 32 cho
0.962. 5 000 điều đầu, ef = 40: heuristic 0.970, chọn m gần nhất 0.945 (ef = 10: 0.801 và 0.781). Cả notebook chạy 6 phút
khi đã có cache, phần lớn là dựng HNSW Python.

## Đọc kết quả

- **Số khoảng cách** là thước đo công bằng giữa Python và C++: ở recall khoảng 0.96, HNSW tính 579 khoảng cách mỗi câu (35
  lần ít hơn exact), IVF cần 5 153 (gần 9 lần HNSW). Đồ thị đi thẳng tới vùng của query; IVF phải quét trọn các ô, và láng
  giềng ở biên ô kéo `nprobe` lên.
- **Cùng thuật toán, cùng recall**: HNSW tự viết và FAISS chênh 0.005 ở ef = 40. Chênh lệch thời gian (dựng 120 lần, tìm vài
  chục lần, một phần vì FAISS đo cả lô) là do Python: mỗi bước của beam search là thao tác heap, `set`, `dict` của Python,
  trong khi phép tính khoảng cách đã là numpy. Đây là lý do không ai dùng HNSW Python ở production, và cũng là lý do số khoảng
  cách tự đo trong bài là con số đáng tin để so thuật toán.
- **ms/câu tự viết của HNSW thấp hơn exact chỉ ở ef nhỏ**: exact cả lô 1.40 ms/câu là một phép nhân ma trận BLAS rất hiệu quả,
  còn HNSW Python ef = 40 mất 1.30 ms. Với 20 000 vector, exact là lựa chọn đúng. ANN chỉ thắng rõ khi $$N$$ lớn hơn nhiều.
- **Heuristic**: trên dữ liệu sinh 20 cụm tách biệt, chọn m gần nhất làm mọi cạnh nằm trong cụm, đồ thị rời thành đảo và
  recall chững ở 0.884 dù tăng ef; heuristic giữ cạnh nối các cụm, đạt 1.0. Trên vector thật (cụm không tách rời như vậy)
  heuristic chỉ hơn 0.025 ở ef = 40. Không nên ngoại suy độ lớn của hiệu ứng từ dữ liệu sinh sang dữ liệu thật.
- Tầng: 1 235 trên 20 000 nút ở tầng 1, khớp $$N/M = 1\,250$$.

## Bẫy thường gặp

- So điều kiện dừng với `ef` thay vì với phần tử xa nhất của `best`.
- Quên đánh dấu đã thăm, hoặc tính khoảng cách từng nút một ngoài `dist` (đúng nhưng chậm, và `n_dist` sai).
- Tỉa láng giềng theo khoảng cách tới nút **mới** thay vì tới chính láng giềng đó: đồ thị vẫn chạy, recall tụt ít, test dựng
  tay mới bắt được.
- Cho nút cùng tầng cao nhất thay entry point (`>=`): vô hại về recall nhưng sai đặc tả và khó tái lập.
- Bỏ bước đi xuống ở các tầng trên: trên đồ thị có thành phần rời ở tầng 0, không bao giờ tới được vùng của query.
