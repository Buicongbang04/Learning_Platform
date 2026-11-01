# M01: Dữ liệu, chuẩn hoá văn bản luật và baseline BM25

## Mục tiêu

Dựng nền cho mọi milestone sau: đọc Zalo Legal đúng cách, chuẩn hoá văn bản luật, chốt **tập đánh giá ghim** và dựng
baseline BM25 với bảng recall@k. Mọi cải tiến ở M02, M03, M05 sẽ được so với bảng này, trên đúng 300 câu này, nên làm
nó cẩn thận quan trọng hơn làm nó nhanh.

Milestone này dùng lại định nghĩa của [module 13](../../modules/13-rag/README.md) (NFC, tokenizer âm tiết, BM25 kiểu
Lucene ở mục 3; recall@k, MRR, nDCG ở mục 6) và cách đo của [module 12](../../modules/12-embeddings-vector-db/README.md).
Bạn đã viết BM25 và các thước đo ở bài Basic 02, 03 module 13: ở đây chúng thành code dùng chung có test.

**Phần cứng:** CPU, khoảng 4 tới 6 giờ làm. Dựng index BM25 trên toàn corpus mất khoảng 10 tới 30 giây.

## Việc cần làm

1. **Đọc dữ liệu** (`legal_assistant/data.py`): `load_corpus`, `load_questions`. Tập ghim là
   `load_questions(root, "test", 300)`: 300 `query-id` đầu tiên theo thứ tự xuất hiện trong `qrels/test.jsonl`. Kiểm
   các con số: 61 425 điều; 300 câu ghim với 301 cặp (câu, điều đúng), đáp án nằm trong 144 văn bản; split train có
   2 432 câu. Split train để dành cho M05 và để tune tham số; **không** tune gì trên 300 câu ghim.
2. **Kiểm toán dữ liệu** trước khi viết code index, ghi vào `reports/RETRIEVAL.md`:
   - phân phối độ dài điều (module 13 mục 2 đã đo: trung vị 829 ký tự, đuôi rất dài) và hệ quả cho M02, M03;
   - số điều không ở dạng NFC, số điều mà `normalize` làm thay đổi (khoảng trắng thừa, dòng trống) và vì sao vẫn phải
     chuẩn hoá dù corpus này sạch: câu hỏi người dùng thật thì không sạch;
   - **giao giữa tập ghim và split train**: đếm số `query-id` của tập ghim cũng có trong `qrels/train.jsonl`, và số câu
     ghim trùng chữ với một câu train. Con số này không bằng 0. Đọc nhãn của chúng ở hai split và ghi lại bạn xử lý
     thế nào; M05 cần câu trả lời.
3. **Chuẩn hoá và tokenizer** (`text.py`): `normalize`, `tokenize` (âm tiết; `bigrams=True` thêm bigram âm tiết liền
   kề), `split_uid` để đọc số hiệu văn bản và số điều từ uid.
4. **BM25 và thước đo** (`bm25.py`, `metrics.py`). Chép lời giải module 13 của bạn được, miễn test của capstone qua.
5. **Script baseline** `scripts/m01_bm25.py`: index trên `title + "\n" + text` đã chuẩn hoá, `k1 = 1.5`, `b = 0.75`;
   in bảng R@1, R@5, R@10, R@20, R@100, MRR@10, nDCG@10 cho hai tokenizer (âm tiết; âm tiết + bigram), kèm thời gian
   dựng index, thời gian mỗi truy vấn, kích thước từ vựng. Ghi log (lệnh, commit, ngày, máy).
6. **Phân tích lỗi**: với tokenizer âm tiết, liệt kê các câu **không** có điều đúng trong top-10. Đọc ít nhất 15 câu,
   xếp loại (ví dụ: diễn đạt khác chữ với điều luật; đúng văn bản sai điều; bị từ vựng hành chính chung như "hồ sơ",
   "thủ tục" kéo sang văn bản khác; nhãn đáng ngờ), có đếm. Bigram cứu được nhóm nào, không cứu được nhóm nào?

## Kết quả nộp

- `legal_assistant/{data,text,bm25,metrics}.py`, test M01 pass.
- `scripts/m01_bm25.py` và log của lần chạy.
- `reports/RETRIEVAL.md`: kiểm toán dữ liệu, bảng baseline, phân tích lỗi.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/ai-engineer/capstone/project/tests -q -rs` không còn test M01 nào skip vì "Chưa làm",
      kể cả `test_pinned_set_on_real_data` (300 câu, 301 cặp, 144 văn bản, 2 432 câu train).
- [ ] Bảng có đủ k = 1, 5, 10, 20 (và R@100, MRR@10, nDCG@10) cho cả hai tokenizer, trên đúng 300 câu ghim.
- [ ] BM25 âm tiết cho R@10 trong khoảng 0.827 tới 0.847 (bản tham chiếu 0.837). BM25 là tất định: lệch hơn 0.01 nghĩa
      là tokenizer, văn bản index hay tập câu hỏi khác định nghĩa, hãy tìm ra chỗ khác trước khi đi tiếp.
- [ ] Số câu ghim trùng với split train được đếm và có quyết định xử lý ghi trong báo cáo.
- [ ] Ít nhất 15 câu hỏng được đọc tận mắt, xếp loại, có đếm; mỗi nhận xét về bigram có số câu đi kèm.
- [ ] Mọi chênh lệch được đọc kèm cỡ mẫu: 300 câu nên một câu là 0.0033 recall; chênh dưới khoảng 0.01 (3 câu) chưa
      nói được gì.

### Số tham chiếu

Bản cài đặt của người soạn, 300 câu ghim, toàn corpus 61 425 điều, PC của track (CPU, 4 luồng, máy dùng chung):

| Tokenizer | R@1 | R@5 | R@10 | R@20 | R@100 | MRR@10 | nDCG@10 | Từ vựng | Dựng index | Mỗi truy vấn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Âm tiết | 0.433 | 0.767 | 0.837 | 0.867 | 0.965 | 0.574 | 0.638 | 11 620 | 11.6 s | 8 ms |
| Âm tiết + bigram | 0.523 | 0.837 | 0.882 | 0.922 | 0.972 | 0.658 | 0.714 | 447 735 | 31.1 s | 9 ms |

BM25 âm tiết không có điều đúng trong top-10 ở 49 câu; thêm bigram còn 35 câu. Bigram tăng R@1 thêm 0.09 (khoảng 27 câu), lớn
hơn nhiều mức nhiễu, đổi lại từ vựng lớn gần 40 lần và dựng index lâu gần 3 lần. Con số R@1 của BM25 âm tiết (0.433) khớp
cột "BM25 top-1" của bài Advanced 02 module 14 trên cùng tập: đó là baseline mà fine-tune closed-book không vượt được.

## Gợi ý

- Thứ tự "xuất hiện đầu tiên" trong qrels quan trọng: đọc vào `set` hay sort theo `query-id` sẽ ra một tập 300 câu
  khác, và mọi con số sau đó không so được với bảng tham chiếu hay với module 13, 14, 17.
- Một câu có thể có nhiều dòng qrels không liền nhau. Test có một ca như vậy.
- Cache danh sách top-100 của mỗi phương pháp ra đĩa (JSON theo `query-id`): M02 cần chúng cho RRF và phân tích "nhánh
  nào cứu câu nào", M05 cần chúng để lấy hard negative.
- Đặt `OMP_NUM_THREADS` và chạy việc nặng với `nice` nếu máy đang dùng cho việc khác; ghi điều kiện máy cạnh số đo thời
  gian.
