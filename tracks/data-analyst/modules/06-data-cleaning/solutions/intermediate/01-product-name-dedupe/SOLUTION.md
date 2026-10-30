# Lời giải: một sản phẩm, nhiều tên

## Cách làm

- **`normalize_description`**: `astype("string")` để ô thiếu thành `<NA>` thay vì chuỗi `"nan"`, rồi `upper`,
  `replace(r"[^A-Z0-9&]+", " ", regex=True)`, `strip`. Một regex thay cả dấu câu lẫn nhiều khoảng trắng liền nhau.
- **`canonical_names`**: đếm dòng theo `(StockCode, mô tả chuẩn hoá)`, sắp `n` giảm dần và tên tăng dần, giữ dòng đầu
  mỗi mã. Đếm theo **dòng**, không theo doanh thu: một dòng nhập sai giá lớn không được quyết định tên.
- **`fuzzy_pairs`**: tên duy nhất, sắp, group theo từ đầu, vòng lặp đôi `i < j` trong từng block. Block lớn nhất vài
  trăm tên nên cả bộ chạy khoảng 5 giây; không blocking thì hơn 7 triệu cặp.
- **`likely_same`**: hiệu túi từ hai chiều; không còn gì là đổi thứ tự; đúng một từ mỗi bên thì kiểm chữ số, độ dài,
  ratio.

## Kết quả trên bộ thật

| Hạng mục | Con số |
| --- | --- |
| Dòng hợp lệ (bỏ mã phí) | 527 789 |
| Mã hàng giữ hoa thường → viết hoa | 3 912 → 3 803 (109 sản phẩm bị tách chỉ vì `85123a` / `85123A`) |
| Mã có hơn một mô tả | 193 (177 mã 2 tên, 14 mã 3 tên, 2 mã 4 tên) |
| Doanh thu trên dòng có mô tả khác tên chuẩn | 213 265 GBP, 2.1% doanh thu hàng hoá 10 272 119 GBP |
| Cặp fuzzy giữa các mã khác nhau, ngưỡng 0.9 | 589; qua `likely_same`: 0 |
| Ngưỡng 0.85 | 1 010 cặp; qua `likely_same`: 1 (`FOLDING UMBRELLA RED WHITE POLKADOT` mã 21706 / `... WHITE RED ...` mã 21711, vẫn là hai mã riêng của nhà cung cấp, không gộp) |

Gom theo mô tả gốc tách một sản phẩm thành nhiều dòng: mã `23203` có `JUMBO BAG VINTAGE DOILY` (24 522 GBP),
`JUMBO BAG DOILEY PATTERNS` (17 273) và lỗi chính tả `JUMBO BAG VINTAGE DOILEY` (273), cùng giá 2.08; gom theo mã thì
là một món 42 068 GBP. Mã `22197` có `POPCORN HOLDER` và `SMALL POPCORN HOLDER` cùng giá 0.85.

Ngược lại, mã `22502` cho thấy "cùng mã" chưa chắc "cùng món": `PICNIC BASKET WICKER SMALL` 467 dòng, giá trung vị
5.95, còn `PICNIC BASKET WICKER 60 PIECES` chỉ 2 dòng, giá 649.50, nhưng mang 39 620 GBP. Gộp theo mã thì giỏ nhỏ
"có" 51 427 GBP và đứng thứ 11. Đây là việc cần hỏi team catalog, ghi chú trong bảng, không tự quyết.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `variant-codes` | c. 193 | Xem bảng trên. 109 là số mã gộp nhờ viết hoa; 19 là số mô tả gốc dùng cho hơn một mã |
| `case-merge` | a | Mã phí đã bị `valid_lines` bỏ trước; viết hoa không bỏ dòng nào |
| `fuzzy-survivors` | d. 0 | 589 cặp đều khác cỡ, màu, chữ cái, số; similarity cao vì tên dài chung phần lớn ký tự |
| `off-canonical-share` | b. khoảng 2.1% | 213 265 / 10 272 119 |
| `high-score-pair` | b | Score chỉ đo ký tự; 1 bấc và 3 bấc là hai món, hai mã |
| `ranking-key` | d | Mã là khoá; tên chuẩn để người đọc hiểu. Gom theo mô tả tách món; gom theo tên fuzzy gộp nhầm món khác nhau; giữ chữ thường tách 109 món |
| `same-code-different-item` | a | Dấu hiệu mã bị dùng cho món khác (hoặc lỗi nhập giá). Ghi chú và hỏi chủ dữ liệu; không tự gộp, không tự bỏ |

## Sai lầm hay gặp

- Gộp mọi cặp có score ≥ 0.9: gộp 26 chữ cái `LETTER A..Z BLING KEY RING` thành một món, cộng nhầm doanh thu.
- Chọn tên chuẩn theo doanh thu thay vì số dòng: mã `22502` sẽ mang tên `60 PIECES` vì hai dòng giá lớn.
- Fuzzy matching không blocking trên laptop 4 GB: chạy hàng chục phút với `difflib`; dùng blocking, hoặc `rapidfuzz`
  (`process.cdist`) khi được phép thêm thư viện.
- Quên rằng blocking theo từ đầu bỏ sót lỗi gõ ở từ đầu (`RETO` / `RETRO`): ghi đánh đổi đó trong ghi chú.
