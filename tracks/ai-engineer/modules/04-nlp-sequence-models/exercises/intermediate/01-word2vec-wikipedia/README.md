---
title: word2vec trên Wikipedia tiếng Việt, ghép âm tiết thành từ
level: intermediate
services: []
files:
  - path: starter/word2vec_wiki.ipynb
    note: 13 hàm/lớp TODO
  - path: tests/test_word2vec_wiki.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/01-word2vec-wikipedia/starter/word2vec_wiki.ipynb
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/01-word2vec-wikipedia -q
---

## Mục tiêu

Train word2vec skip-gram negative sampling trên khoảng 6 triệu âm tiết Wikipedia tiếng Việt với code của chính bạn
(subsampling, cửa sổ động, lấy mẫu âm, loss), tự phát hiện cụm âm tiết thành từ, rồi đánh giá bằng láng giềng và
analogy. Làm xong bạn biết word2vec cần gì để chạy trên dữ liệu thật, và vì sao tiếng Việt cần thêm một bước mà tiếng Anh
không cần.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Chạy cả notebook lời giải: khoảng 5 phút trên CPU 4 luồng khi máy rảnh (mỗi lần train
3 epoch khoảng 2 phút), tới 25 phút khi CPU đang bị việc khác chiếm.

Mở `starter/word2vec_wiki.ipynb`, làm theo thứ tự các mục (đặc tả chi tiết từng hàm nằm ngay trên cell của nó):

1. `load_articles`, `tokenize`: 5 000 bài dài ít nhất 2 000 ký tự lấy ngẫu nhiên (seed 0), chuẩn hoá NFC, chữ thường,
   cắt câu, chỉ giữ chữ cái.
2. `find_phrases`, `apply_phrases`: điểm cụm kiểu PMI ở mục 3 lý thuyết, ghép tham lam từ trái.
3. `build_vocab`, `flatten`, `keep_probs`, `make_pairs`: corpus thành mảng id, subsampling và cửa sổ động **vectorized**
   bằng numpy (không lặp Python từng token), theo đúng thứ tự gọi `rng` trong đặc tả.
4. `SGNS`, `train_sgns`: hai `nn.Embedding(sparse=True)`, loss SGNS trung bình, SGD sparse với lr giảm tuyến tính.
5. `most_similar`, `analogy`, `analogy_accuracy`.

Rồi chạy các cell `explore`: train hai lần (trên âm tiết và sau khi ghép cụm), so láng giềng, đo analogy trên 20 cặp
nước–thủ đô và 12 cặp giới tính, vẽ PCA. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `tokenize` đúng NFC, chữ thường, cắt câu, bỏ số và câu dưới 2 âm tiết; `find_phrases` đúng điểm, `delta`,
  `min_count` (giữ cặp có count bằng đúng `min_count`), không đếm qua ranh giới câu; `apply_phrases` ghép tham lam.
- `make_pairs`: không ghép qua ranh giới câu, khoảng cách trong `[1, window]`, cửa sổ động cho trung bình 2.5 cặp mỗi
  phía khi `window = 4`, subsample với `keep = 0.5` giữ khoảng một nửa, cùng `rng` cho cùng kết quả.
- `SGNS` khởi tạo đúng, loss khớp công thức, gradient sparse; `train_sgns` học được hai chủ đề trên dữ liệu sinh và tái
  lập theo seed.
- `most_similar` dùng cosine; `analogy` bỏ `a`, `b`, `c`; `analogy_accuracy` chỉ đếm cặp có trong vocab.
- Wikipedia thật: 200 bài đầu của mẫu (seed 0) cho đúng 17 613 câu và 270 597 âm tiết; `việt nam` là cụm, `của các` thì
  không.
- Cell `explore` in ra số giống bảng mục 3 lý thuyết (13 077 cụm; analogy nước–thủ đô 31/272, giới tính 13/72; máy khác
  có thể lệch nhẹ).

## Gợi ý

### Gợi ý 1

Với `make_pairs`, nghĩ theo **khoảng cách** chứ không theo vị trí: với mỗi `d` từ 1 tới `window`, mọi cặp cách nhau `d`
lấy được bằng hai lát cắt lệch nhau `d` phần tử của mảng id sau subsample. Điều kiện "cùng câu" và điều kiện cửa sổ động
đều là mask boolean trên đúng hai lát cắt đó. Cửa sổ động thuộc về **center**: với mỗi hướng (context ở bên phải hay bên
trái), bán kính `b` của phần tử nào quyết định cặp được giữ? Một vòng lặp theo `d` là đủ nhanh cho 6 triệu token.

### Gợi ý 2

Điểm âm của cả batch là một phép nhân ma trận theo batch giữa `(B, K, d)` và `(B, d, 1)`. `torch.optim.SGD` nhận được
gradient sparse; loss là **trung bình** theo batch, nên nghĩ xem lr của optimizer phải bằng bao nhiêu để mỗi cặp nhận bước
như word2vec gốc. lr đổi mỗi bước bằng cách sửa `param_groups`. Muốn khớp số của lời giải: tạo `SGNS` ngay sau
`torch.manual_seed(seed)`, lấy cặp và hoán vị từ cùng một `rng`, mẫu âm bằng `torch.multinomial` trên tensor `float64`.
