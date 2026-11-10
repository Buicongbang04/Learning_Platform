# Lời giải: BM25 cho tiếng Việt

## Cách làm

**`tokenize_vi`** là một dòng: `re.findall(r"\w+", unicodedata.normalize("NFC", text).lower())`. NFC phải đi trước
`\w+`: trên bản NFD, "luật" là `l u a ̣ ̂ t` với hai dấu rời không phải ký tự chữ, nên `\w+` cắt thành `lua`, `t`. Tách
theo `\w+` thay cho `split()` để "Điều 21," và "Điều 21" cho cùng token `21`, và "100/2019/NĐ-CP" tách thành số hiệu
tìm được từng phần.

**`BM25.__init__`** làm mọi việc không phụ thuộc câu hỏi:

- Mảng mẫu số theo tài liệu $$k_1\left(1 - b + b\,\frac{|d|}{\mathrm{avgdl}}\right)$$ (bỏ phần $$f$$, cộng sau).
- **Inverted index**: với mỗi term, mảng chỉ số tài liệu chứa nó và mảng tần suất tương ứng (đếm bằng `Counter`).
- IDF dạng Lucene cho mỗi term, $$n_t$$ là độ dài danh sách tài liệu của term.

**`scores`** khởi tạo mảng 0 và với mỗi token của câu hỏi cộng
`idf * tf * (k1 + 1) / (tf + norm[ids])` vào `out[ids]`. Chỉ tài liệu chứa term mới bị đụng tới, nên một câu hỏi 10
token trên 3 541 điều tốn dưới 1 ms thay vì duyệt 35 000 cặp. Token không có trong index bị bỏ qua (đóng góp 0).

**`top_k`** dùng `np.argsort(-scores, kind="stable")`: sort ổn định giữ chỉ số nhỏ trước khi bằng điểm, nên kết quả
tái lập được. `argsort(scores)[::-1]` thì ngược lại: bằng điểm, chỉ số **lớn** đứng trước.

## Vì sao IDF dạng Lucene

Dạng gốc của Robertson $$\ln\frac{N - n_t + 0.5}{n_t + 0.5}$$ âm khi term có ở hơn nửa corpus. Với Zalo, "định" có trong
85% số điều: dạng gốc cho IDF âm, nghĩa là tài liệu **chứa** "định" bị trừ điểm, càng chứa nhiều càng bị trừ. Thêm
"1 +" giữ IDF dương và đơn điệu (term càng hiếm càng nặng), term phổ biến tiến về 0 thay vì âm. Trên corpus 3 tài liệu
của test, term có ở cả 3 tài liệu có IDF $$\ln(8/7) = 0.134$$ thay vì $$\ln(1/7) = -1.95$$.

## Hai tham số

- $$k_1$$ điều khiển bão hoà: phân số $$\frac{f (k_1 + 1)}{f + k_1}$$ (khi $$b = 0$$) bằng 1 tại $$f = 1$$ và tiến tới
  $$k_1 + 1$$ khi $$f$$ lớn. Một điều lặp "xử phạt" 30 lần không hơn gấp 30 lần điều nhắc một lần.
- $$b$$ điều khiển chuẩn hoá độ dài: $$b = 0$$ tắt hẳn, $$b = 1$$ chia hoàn toàn theo $$|d| / \mathrm{avgdl}$$. Văn bản luật
  dài ngắn rất lệch (trung vị 829 ký tự, dài nhất 252 881), nên $$b$$ có tác dụng thật: điều dài chứa mọi từ nhưng
  thường không phải đáp án.

Trên lát cắt của lý thuyết, cài đặt này cho R@1 0.540, R@10 0.930, MRR@10 0.6861 với tài liệu là `title + " " + text`.
Chỉ dùng `text` (bỏ tiêu đề Điều) thì R@10 tụt còn 0.910, MRR@10 còn 0.629: tiêu đề mang nhiều từ khoá nhất.

## Bẫy thường gặp

- Tokenizer lúc index và lúc query khác nhau (một bên NFC, một bên không; một bên `split`, một bên `\w+`).
- Quên `(k1 + 1)` ở tử số: thứ hạng không đổi khi $$k_1$$ cố định, nhưng điểm sai và so với thư viện khác lệch.
- Đảo vai trò của $$b$$ và $$1 - b$$: $$b = 0$$ khi đó lại chuẩn hoá độ dài hoàn toàn.
- Gộp token trùng của câu hỏi bằng `set(query)`: Lucene và `rank_bm25` đều cộng mỗi lần token xuất hiện.
- Tính lại `avgdl` và độ dài trong mỗi lần `scores`: đúng nhưng chậm, mọi thứ không phụ thuộc câu hỏi nên ở `__init__`.
