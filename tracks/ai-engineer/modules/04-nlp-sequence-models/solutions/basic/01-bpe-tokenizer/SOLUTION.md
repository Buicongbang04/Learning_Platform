# Lời giải: BPE tokenizer byte-level

## Cách làm

**Chuẩn hoá và pretokenize.** `unicodedata.normalize("NFC", text)` rồi `PRETOKEN_RE.findall`. Regex có dạng của GPT-2:
từ kèm **một** dấu cách đứng trước (`" chào"`), cụm dấu câu kèm dấu cách, và hai nhánh khoảng trắng; nhánh
`\s+(?!\S)` giữ lại dấu cách cuối cùng của một cụm để nó dính vào từ sau. Vì mọi ký tự đều thuộc đúng một pretoken,
`"".join(pretokenize(x)) == normalize(x)`, và `decode` chỉ cần nối lại.

**Train.** Ba bước:

| Bước | Làm gì | Vì sao |
| --- | --- | --- |
| Đếm pretoken | `Counter` trên mọi pretoken của mọi câu | 3 000 câu UIT-VSFC chỉ có vài nghìn pretoken khác nhau |
| Mỗi vòng | đếm cặp trong từng pretoken, nhân tần suất; chọn `max` theo `(count, -a, -b)` | luật hoà cố định cho kết quả tái lập, đúng tới từng merge |
| Áp merge | thay cặp bằng `256 + i` trong mọi pretoken | merge sau dùng được token của merge trước |

Dừng khi cặp tốt nhất có count dưới 2: gộp một cặp chỉ xuất hiện một lần không nén được gì, chỉ làm vocab phình ra.
Không có bước này, test `train_bpe(["abcdefg"], 300)` sẽ trả 6 merge vô nghĩa.

**Encode.** Không đi tham lam từ trái sang phải. Mỗi vòng tìm, trong các cặp liền nhau hiện có, cặp có thứ hạng merge
thấp nhất rồi gộp **mọi** lần xuất hiện của nó. Lý do: lúc train, merge `(b, c)` được áp lên toàn bộ dữ liệu trước khi
`(a, b)` được học, nên encode phải lặp lại đúng thứ tự đó thì một từ đã thấy lúc train mới ra đúng một token như lúc
train. Cache theo pretoken làm encode 3 166 câu test nhanh hơn vài lần.

**Decode.** Dựng bảng id → `bytes` theo thứ tự merge, nối bytes của cả chuỗi rồi giải mã một lần với
`errors="replace"`. Giải mã từng token riêng sẽ hỏng, vì token có thể là nửa chữ (`0xE1` là byte đầu của `ạ`, `ế`...).

## Kết quả thật

Trên 11 426 câu train UIT-VSFC, đo trên 3 166 câu test (bảng ở mục 2 lý thuyết):

| vocab_size | Token mỗi âm tiết | Thời gian train |
| --- | --- | --- |
| 256 | 5.43 | 0 |
| 512 | 1.63 | 1.4 s |
| 1 000 | 1.16 | 4.4 s |
| 2 000 | 1.03 | 10 s |

Test thật dùng 3 000 câu đầu, vocab 600 (344 merge): 1.468 token mỗi âm tiết, train khoảng 2 giây. So với tokenizer
của LLM trên văn bản tiếng Việt tổng quát (mục 1): `cl100k_base` 2.00, `o200k_base` 1.16 token mỗi âm tiết. Một BPE
nhỏ train đúng miền nén tốt hơn tokenizer lớn train sai miền.

Mười merge đầu trên UIT-VSFC lộ rõ byte-level: hai merge đầu là hai nửa của chữ có dấu (in ra thành `�`), rồi
`' t'`, `'ng'`, `'nh'`, `' c'`... Chữ thường không dấu được gộp trước vì xuất hiện nhiều nhất; chữ có dấu phải ghép 2-3
byte mới thành một ký tự.

## Bẫy thường gặp

- Quên NFC: input gõ từ bộ gõ "Unicode tổ hợp" ra chuỗi byte khác, merge học trên NFC không khớp, số token tăng vọt.
- Đếm cặp mà không nhân tần suất pretoken (đếm trên tập pretoken khác nhau): merge ưu tiên chuỗi hiếm, test đồ chơi sai
  ngay merge thứ hai.
- Merge trên cả văn bản không pretokenize: token chứa dấu cách ở giữa (`"h ."`), tokenizer học cụm từ thay vì subword.
- Encode tham lam từ trái: cùng một từ ra id khác lúc train, model nhận chuỗi chưa từng thấy.
- `decode` từng token rồi nối chuỗi: ký tự có dấu bị vỡ thành `��`.
