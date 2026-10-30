---
title: BPE tokenizer byte-level tự viết, chuẩn hoá tiếng Việt
level: basic
services: []
files:
  - path: starter/bpe.py
    note: 5 hàm TODO
  - path: tests/test_bpe.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/basic/01-bpe-tokenizer -q
---

## Mục tiêu

Tự viết một tokenizer BPE byte-level kiểu GPT-2 (chuẩn hoá NFC, pretokenize, train, encode theo thứ hạng merge,
decode) và khớp từng merge với lời giải. Làm xong bạn hiểu vì sao `len(tokenizer.encode(...))` khác số từ, vì sao
input NFD làm hỏng tokenizer, và token "nửa chữ" từ đâu ra.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Trong `starter/bpe.py` (chỉ dùng thư viện chuẩn), quy ước như mục 2 phần lý thuyết: token cơ sở là 256 byte (id 0
tới 255), merge thứ `i` tạo token id `256 + i`. Viết:

1. `normalize(text)`: chuẩn hoá Unicode về **NFC**.
2. `pretokenize(text)`: `normalize` rồi tách bằng `PRETOKEN_RE` (cho sẵn). Ghép các pretoken lại phải ra đúng văn bản
   đã chuẩn hoá. Ví dụ `"Xin chào,  thế"` thành `["Xin", " chào", ",", " ", " thế"]`.
3. `train_bpe(texts, vocab_size) -> list[tuple[int, int]]`: danh sách merge theo thứ tự học được.
   - Mỗi vòng đếm mọi cặp token liền nhau **bên trong từng pretoken**, nhân với số lần pretoken đó xuất hiện.
   - Chọn cặp nhiều nhất; hoà thì chọn cặp có `(id trái, id phải)` nhỏ nhất (so như tuple).
   - Dừng khi đủ `vocab_size` token (tức `vocab_size - 256` merge) hoặc khi cặp tốt nhất xuất hiện dưới 2 lần.
4. `encode(text, merges) -> list[int]`: với từng pretoken, bắt đầu từ các byte UTF-8 của nó, lặp lại: trong các cặp
   liền nhau hiện có, gộp cặp có **thứ hạng merge thấp nhất** (học sớm nhất); dừng khi không còn cặp nào nằm trong
   `merges`. Nối id của mọi pretoken.
5. `decode(ids, merges) -> str`: nối bytes của các token rồi giải mã UTF-8 **một lần**, byte không hợp lệ thành `U+FFFD`
   (`errors="replace"`).

## Tiêu chí đạt

- `normalize` đưa chuỗi NFD (24 code point) về NFC (17 code point); input NFD và NFC cho cùng id.
- `pretokenize` đúng ví dụ trong test và ghép lại ra văn bản gốc.
- Trên corpus đồ chơi `"low "*5 + "lower "*2 + "newest "*6 + "widest "*3`, 10 merge đầu khớp đúng thứ tự (cặp đầu là
  `('e', 's')`, không phải `('s', 't')`).
- Không merge nào chứa dấu cách ở giữa (không vượt ranh giới pretoken); dừng sớm khi không còn cặp lặp lại.
- `encode` áp merge theo thứ hạng: với `merges = [(b, c), (a, b)]`, `"abc"` thành `[97, 256]`.
- `decode(encode(x)) == normalize(x)` cho tiếng Việt, emoji, chữ Hán, khoảng trắng lạ, chuỗi rỗng.
- UIT-VSFC thật: 344 merge học từ 3 000 câu train trong dưới 20 giây, đo được 1.468 token mỗi âm tiết trên 500 câu
  test.

## Gợi ý

### Gợi ý 1

Đừng quét lại toàn bộ văn bản mỗi vòng merge. Đếm tần suất từng pretoken khác nhau một lần bằng `Counter`, giữ mỗi
pretoken là `[list id, tần suất]`; mỗi vòng chỉ đếm cặp trên danh sách đó. Viết một hàm phụ `_merge(ids, pair, new_id)`
thay mọi lần xuất hiện của `pair` trong `ids` (đi từ trái, không chồng lấn) và dùng nó cho cả train lẫn encode.

### Gợi ý 2

Chọn cặp tốt nhất với luật hoà: `max(counts, key=lambda p: (counts[p], -p[0], -p[1]))`. Trong `encode`, dựng
`ranks = {pair: 256 + i}` rồi mỗi vòng lấy `min(các cặp liền nhau, key=lambda p: ranks.get(p, inf))`; nếu cặp đó không
có trong `ranks` thì dừng. Cache kết quả theo pretoken (văn bản thật lặp lại rất nhiều từ). Trong `decode`, bảng
`vocab[256 + i] = vocab[a] + vocab[b]` dựng theo đúng thứ tự merge vì merge sau có thể dùng token của merge trước.
