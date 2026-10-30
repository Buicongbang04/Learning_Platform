# Lời giải: recall@k, MRR@k, nDCG@k

## Cách làm

Một hàm phụ `_check` kiểm đầu vào cho cả ba thước đo: `k >= 1`, số danh sách bằng số tập đúng, có ít nhất một truy vấn,
và không truy vấn nào có tập đúng rỗng. Sau đó mỗi thước đo tính cho từng truy vấn trên `ret[:k]` rồi chia cho số truy vấn:

- **Recall**: `len(rel & set(ret[:k])) / len(rel)`.
- **MRR**: `next((1 / rank for rank, doc in enumerate(ret[:k], start=1) if doc in rel), 0.0)`: dừng ở tài liệu đúng đầu tiên.
- **nDCG**: DCG cộng $$\frac{1}{\log_2(\mathrm{rank} + 1)}$$ ở các hạng có tài liệu đúng; IDCG cộng cùng đại lượng cho các
  hạng $$1..\min(|\mathrm{Rel}_q|, k)$$.

Tính tay ba truy vấn của test (Rel lần lượt {A, B}, {Z}, {S, T}):

| Truy vấn | Trả về | R@3 | RR@3 | nDCG@3 | R@5 | RR@5 | nDCG@5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | C, A, D, B, E | 1/2 | 1/2 | 0.3869 | 1 | 1/2 | 0.6509 |
| 2 | X, Y, Z | 1 | 1/3 | 0.5 | 1 | 1/3 | 0.5 |
| 3 | P, Q, R, S | 0 | 0 | 0 | 1/2 | 1/4 | 0.2641 |
| Trung bình | | 0.5 | 0.2778 | 0.2956 | 0.8333 | 0.3611 | 0.4717 |

Truy vấn 3 ở `k = 5`: S ở hạng 4 cho DCG $$\frac{1}{\log_2 5} = 0.4307$$; IDCG tính cả T (không được trả về) nên là
$$1 + \frac{1}{\log_2 3} = 1.6309$$, cho 0.2641. Nếu IDCG chỉ đếm tài liệu đúng đã tìm được thì ra 0.4307: hệ thống bỏ
sót T lại được thưởng.

## Vì sao các lựa chọn này

- **Ném lỗi với tập đúng rỗng** thay vì cho 0 hay bỏ qua: recall là $$\frac{0}{0}$$, và cả hai cách "chữa" đều làm con số
  trung bình lệch im lặng. Lỗi buộc người gọi lọc truy vấn không có nhãn **trước**, một cách có chủ ý.
- **IDCG cắt ở k**: với 3 tài liệu đúng và `k = 1`, cách tốt nhất có thể chỉ đặt được 1 tài liệu đúng vào top 1; hệ thống
  làm đúng như vậy phải được 1.0. Không cắt thì nDCG@1 tối đa chỉ còn 0.47 và các `k` không so được với nhau.
- **Cơ số log không quan trọng** cho nDCG (tỉ số DCG/IDCG triệt tiêu hằng số), nhưng **vị trí** thì có: hạng 1 chia cho
  $$\log_2 2 = 1$$. Viết $$\log_2 i$$ thì chia cho 0, viết $$\log_2(i + 2)$$ thì sai nhẹ mà khó thấy; test so với
  `sklearn.metrics.ndcg_score` để bắt.

## Đọc các thước đo

Recall@k trả lời "đoạn đúng có lọt vào k đoạn đưa cho LLM không", là trần của rerank. MRR nhạy với hạng 1 và hợp khi
mỗi câu có một đáp án (Zalo: trung bình 1.01 điều một câu). nDCG dùng khi có nhiều tài liệu đúng hoặc nhiều mức liên
quan. Báo cáo cả ba, kèm `k`, và luôn trên cùng một tập truy vấn: MRR 0.78 trên lát cắt 3 541 điều không so được với
MRR trên toàn bộ 61 425 điều.

## Bẫy thường gặp

- MRR cộng mà không chia số truy vấn (0.83 thay vì 0.28 ở `k = 3`), hoặc cộng $$\frac{1}{\mathrm{rank}}$$ của mọi tài liệu đúng.
- MRR tìm trên cả danh sách thay vì top-$$k$$.
- Recall chia cho $$k$$ (đó là precision) hoặc cho $$\min(k, |\mathrm{Rel}|)$$ (một biến thể có tên riêng, không phải định nghĩa
  của module).
- IDCG từ số tài liệu đúng tìm được, hoặc không cắt ở $$k$$.
