# Lời giải: hybrid retrieval trên toàn bộ Zalo Legal

## Cách làm

**`load_corpus`, `load_questions`.** Đọc JSONL từng dòng bằng `json.loads`. Với qrels, một `dict` từ query-id tới
`set` corpus-id vừa gom được các dòng không liền nhau của cùng câu vừa giữ thứ tự xuất hiện đầu tiên (dict của
Python giữ thứ tự chèn), rồi lấy `n` khoá đầu. Text câu hỏi tra trong một `dict` dựng từ `queries.jsonl`. Tập ghim
`load_questions(root, 300)` có 299 câu một điều đúng và 1 câu hai điều đúng (301 cặp), đáp án nằm trong 144 văn bản.

**`embed_corpus`.** Một list comprehension gọi `embed_fn(texts[i:i + batch_size])` với `i` bước `batch_size`, ghép
bằng `np.concatenate`, rồi chia cho chuẩn L2 của từng dòng, thay chuẩn 0 bằng 1 để dòng toàn 0 (embed lỗi) không thành
`NaN`. Dòng `NaN` làm mọi tích vô hướng với nó thành `NaN`, và `argsort` luôn xếp `NaN` xuống **cuối**: điều luật đó
không bao giờ được tìm thấy, mà không có lỗi nào báo. Vector 0 cũng không bao giờ thắng (cosine 0), nhưng đếm được và
in ra được.

**`dense_search`.** `matrix @ q_vec` rồi `np.argsort(-scores, kind="stable")[:k]`. Các dòng đã chuẩn hoá nên tích vô
hướng là cosine nhân với một hằng số dương (độ dài `q_vec`), không đổi thứ hạng. Với 61 425 × 1 024 float32 (250 MB),
một câu mất khoảng 20 ms, phần lớn là `argsort` toàn bộ; `np.argpartition` lấy top-k rồi mới sort sẽ nhanh hơn, nhưng
phải tự giữ quy tắc bằng điểm.

**`rrf_fuse`.** Cộng `1 / (k + rank)` (hạng từ 1) vào một `defaultdict(float)` qua mọi danh sách, rồi
`sorted(scores, key=lambda d: (-scores[d], d))`. Khoá có chỉ số để kết quả không phụ thuộc thứ tự chèn vào dict.

**Embed một lần, cache có kiểm.** `safe_embed` trong cell `explore` bọc `llmkit.embed`: `bge-m3` qua Ollama đôi khi
trả `NaN` cho một văn bản và server báo HTTP 500 cho **cả lô**. `llmkit` tự gửi lại từng văn bản của lô lỗi và chỉ báo
lỗi cho văn bản thật sự hỏng; `safe_embed` thử sửa nhẹ văn bản, cuối cùng cho vector 0 và in ra. Ma trận lưu cùng danh
sách id, và chỉ dùng lại khi danh sách id khớp đúng corpus: đổi corpus mà quên embed lại thì dòng i không còn là điều i,
retrieval sai im lặng.

## Kết quả thật

Laptop của track (RTX 3050 4GB, Ollama `bge-m3`), corpus 61 425 điều (văn bản embed = `title + "\n" + text`), 300 câu ghim:

| Bước | Thời gian |
| --- | --- |
| Đọc corpus và qrels | 0.7 s |
| Dựng index BM25 âm tiết (11 620 âm tiết khác nhau) | 6.4 s |
| Truy vấn BM25 | 6 ms/câu |
| Embed corpus bằng `bge-m3` (lô 32) | 2 715 s = 45 phút (22.6 điều/giây), 0 văn bản lỗi |
| Embed 300 câu hỏi | 3.5 s |
| Dense search trên 61 425 vector | 20 ms/câu |
| Cả notebook khi đã có cache | khoảng 25 s |

| Phương pháp | R@1 | R@5 | R@10 | R@100 | MRR@10 |
| --- | --- | --- | --- | --- | --- |
| BM25 âm tiết | 0.433 | 0.767 | 0.837 | 0.965 | 0.574 |
| Dense `bge-m3` | **0.600** | **0.862** | 0.905 | **0.978** | **0.706** |
| Hybrid RRF (BM25 + dense), k = 60 | 0.573 | 0.848 | **0.915** | 0.975 | 0.695 |

Top-10 có điều đúng: cả hai nhánh 244 câu, chỉ BM25 7, chỉ dense 28, không nhánh nào 21; hybrid 275/300. Cosine cao
nhất mỗi câu (dense, cả điều): trung vị 0.707, thấp nhất 0.517. 131 điều dài hơn 16 000 ký tự nên bị Ollama cắt ở
4 096 token khi embed.

## Đọc kết quả

- **Corpus lớn hơn, BM25 tụt mạnh hơn dense.** Trên lát cắt của phần lý thuyết (3 541 điều cùng văn bản với đáp án),
  BM25 có MRR@10 0.686 và dense 0.751. Ở đây BM25 còn 0.574 (giảm 0.11), dense 0.706 (giảm 0.05). Lát cắt chỉ có nhiễu
  "cùng văn bản"; corpus đầy đủ thêm hàng chục nghìn điều của văn bản khác dùng cùng từ vựng hành chính ("phạt tiền",
  "hồ sơ", "thủ tục"), và BM25 âm tiết không phân biệt được ngữ cảnh của chúng. Dense chịu nhiễu đó tốt hơn.
- **Hybrid không thắng dense ở đây**, khác bảng lát cắt. RRF với k = 60 cho hai nhánh phiếu gần như ngang nhau; khi
  nhánh BM25 yếu hơn hẳn, điều đúng mà dense đặt hạng 1 thường bị một điều BM25 xếp cao vượt lên, nên R@1 tụt từ 0.600
  xuống 0.573. Hybrid vẫn nhỉnh ở R@10 (0.915 so với 0.905) vì 7 câu chỉ BM25 tìm được. Đây chính là ý "nhánh yếu kéo
  thứ hạng xuống" ở mục 3 lý thuyết (BM25 âm tiết + dense theo khoản): fusion không bù được cho một nhánh kém. Hướng sửa
  là làm nhánh BM25 tốt hơn (bigram âm tiết, tách từ) hoặc cho dense trọng số lớn hơn trong RRF, và đo lại.
- **Câu chỉ BM25 cứu được** là câu chứa chi tiết khớp chính xác: "không thực hiện đúng quy trình để thời gian đi qua trạm
  thu phí ... lớn hơn 10 phút đến 20 phút" (BM25 hạng 1, dense trượt top-10). **Câu chỉ dense cứu được** diễn đạt khác
  chữ của điều luật ("Định nghĩa thu nhập từ hoạt động kinh doanh theo Hiệp định tránh đánh thuế hai lần").
- **R@100 0.975 nhưng R@1 0.57**: điều đúng gần như luôn có trong top-100, chỉ không đứng đầu. Đó là trần và là chỗ của
  reranker ở bài 03.
- 300 câu nên mỗi câu đóng góp 0.0033 vào R@1: chênh 0.027 giữa dense và hybrid ở R@1 là 8 câu, vượt nhiễu; chênh 0.01
  ở R@10 (3 câu) thì không.
