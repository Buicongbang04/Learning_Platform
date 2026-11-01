# Lời giải: làm sạch, khử trùng lặp và chia bộ instruction tiếng Việt

## Cách làm

- **`normalize_text`**: NFC trước mọi thứ (tách từ, hash, n-gram đều so byte), rồi xuống dòng thống nhất, gộp khoảng trắng
  ngang trong từng dòng bằng `[ \t ]+`, gộp dòng trống thừa. Không gộp `\n`: xuống dòng mang cấu trúc (danh sách
  lựa chọn, đoạn văn), model cần thấy nó.
- **`to_messages`**: system prompt hỏng thì **bỏ hẳn** thay vì giữ chuỗi `"`; khi bỏ, chat template của Qwen2.5 tự chèn
  system mặc định, đúng với cách model được dùng khi người dùng không gửi system.
- **`dedup_key`**: chuẩn hoá từng phần **rồi** mới nối bằng `\x1f`. `\x1f` (unit separator) là khoảng trắng đối với
  `str.split()`, nên nối trước rồi `split()` sẽ xoá luôn dấu phân cách và làm "ab" + "c" trùng với "a" + "bc". Test kiểm
  đúng SHA-1 để bắt lỗi này.
- **`minhash_signature`**: tập shingle 5 ký tự, hash nền là 8 byte đầu của BLAKE2b, họ hàm $$h_k(x) = (a_k x + b_k) \bmod P$$
  với $$P = 2^{31} - 1$$, tính cả ma trận bằng `np.outer`. Với hai tập $$S, T$$, $$\Pr[\min h_k(S) = \min h_k(T)] \approx J(S, T)$$,
  nên tỉ lệ thành phần bằng nhau của hai chữ ký ước lượng Jaccard. Hash nền phải "đủ ngẫu nhiên": thử với `zlib.crc32` (tuyến
  tính trên GF(2)) cho ước lượng lệch hơn 0.1 so với Jaccard thật trên ví dụ của test, BLAKE2b thì không.
- **`near_duplicate_groups`**: 16 band × 4 hàng. Hai văn bản Jaccard $$s$$ thành ứng viên với xác suất $$1 - (1 - s^4)^{16}$$:
  khoảng 0.12 ở $$s = 0.3$$, 0.89 ở $$s = 0.6$$, gần 1 từ 0.8. Ứng viên chỉ được nối khi ước lượng Jaccard đạt ngưỡng. Lần
  thử đầu không kiểm ngưỡng (nối mọi cặp trùng một band) gộp 90 680 trên khoảng 121 nghìn mẫu vào **một** nhóm: văn bản
  ngắn cùng khuôn chạm nhau ở một band, và union-find bắc cầu hết. Bước kiểm ngưỡng là bắt buộc.
- **`group_split`**: hash của mã nhóm, không dùng `random`: cùng nhóm luôn cùng phía, thêm dữ liệu mới không xáo lại phép
  chia cũ, chạy lại ở máy khác cho cùng kết quả.
- **`contamination`**: tập n-gram của mọi văn bản train (từng văn bản riêng), tỉ lệ n-gram của mẫu đánh giá nằm trong đó.
  13-gram là ngưỡng của báo cáo GPT-3 cho tiếng Anh; với tiếng Việt (âm tiết ngắn) 13 âm tiết ngắn hơn 13 từ tiếng Anh.

## Kết quả trên OpenOrca-Viet (PC của track, CPU 4 luồng, 7 phút cả notebook)

| Bước | Số mẫu |
| --- | --- |
| Tải về | 121 178 (23 system prompt khác nhau, 589 mẫu không ở dạng NFC) |
| System prompt hỏng, bị bỏ | 10 537 (10 536 mẫu chỉ là `"`) |
| Sau khử trùng chính xác | 121 026 (bỏ 152) |
| Nhóm MinHash (ngưỡng 0.8) | 112 273 nhóm; 13 508 mẫu nằm trong nhóm có từ 2 mẫu; nhóm lớn nhất 67 |
| Một mẫu mỗi nhóm | 112 273 |
| Lọc 16 tới 512 token | 72 453 |
| Ghi ra | 10 000 train (ngẫu nhiên, seed 0), 3 689 validation |

Độ dài theo chat template của Qwen2.5 (p10/p50/p90/p99/max): 155 / 412 / 918 / 2 735 / 12 382 token; 73 976 mẫu (61%)
nằm trong [16, 512] trước khi khử gần trùng.

| | Chia ngẫu nhiên 5% | Chia theo nhóm 5% |
| --- | --- | --- |
| Mẫu validation | 6 071 | 6 178 |
| Mẫu validation có bản gần trùng trong train | 624 | 0 |
| Trong 500 mẫu val: có ≥ 50% 13-gram nằm trong train | 87 | 82 |
| Tỉ lệ 13-gram trùng trung bình | 0.199 | 0.183 |

Đọc bảng:

- **Khử trùng chính xác gần như không làm gì** (152 mẫu), còn MinHash tìm ra hơn 13 nghìn mẫu nằm trong nhóm gần trùng.
  Nhóm lớn nhất (67 mẫu) không phải một câu dịch lại nhiều lần mà là **một khuôn câu hỏi** của FLAN (phân loại DBpedia:
  "... đưa ra một danh sách các danh mục: công ty, cơ sở giáo dục, nghệ sĩ...") với tên thực thể khác nhau: phần khuôn dài
  hơn phần khác nhau nên Jaccard vượt 0.8. Giữ một mẫu mỗi nhóm là quyết định có chủ đích: ít lặp khuôn, đa dạng hơn.
  Muốn giữ chúng thì nâng ngưỡng hoặc chỉ băm phần câu trả lời.
- **Chia ngẫu nhiên để lọt 624 mẫu validation** (khoảng 10%) có bản gần trùng trong train; chia theo nhóm đưa về 0 theo
  định nghĩa. Loss validation đo trên tập lọt sẽ thấp hơn thực tế.
- **13-gram vẫn trùng ở cả hai cách chia** (87 so với 82 trên 500 mẫu): FLAN dùng chung các khuôn dài ("Dựa vào ngữ cảnh
  trên, hãy chọn phương án đúng..."), nên n-gram trùng không có nghĩa nội dung bị lộ. Kiểm nhiễm bẩn bằng n-gram phải
  đi kèm đọc **cái gì** trùng; với benchmark thật, chỉ tính n-gram của phần nội dung (câu hỏi, đáp án), không tính khuôn.
- **Lọc độ dài bỏ khoảng 39%** dữ liệu ở ngưỡng 512 token. Bỏ chứ không cắt: cắt cụt mất đuôi câu trả lời và token
  `<|im_end|>`, model học trả lời dở dang và không biết dừng.

## Giấy phép

Registry ghi: Apache-2.0 (thẻ Hugging Face), dữ liệu sinh bởi GPT-4/PaLM-2/Claude từ vi-FLAN. Nghĩa là: dùng để học
và nghiên cứu được; dùng thương mại (nhất là train model cạnh tranh với nhà cung cấp) còn phụ thuộc điều khoản sử dụng
của các nhà cung cấp model đã sinh câu trả lời, và của các bộ gốc trong FLAN. Ghi điều này vào model card của model bạn
fine-tune.

## Bẫy thường gặp

- Chuẩn hoá NFC **sau** khi dedup hoặc hash: hai bản NFC/NFD của cùng văn bản thành hai khoá.
- Dùng `random.random() < 0.05` cho từng mẫu: bản gần trùng rơi vào hai phía (bảng trên).
- Đưa system prompt vào khoá dedup: cùng câu hỏi, cùng đáp án lặp lại với 16 system prompt khác nhau vẫn bị giữ cả 16.
- LSH không kiểm ngưỡng, hoặc ngưỡng quá thấp với văn bản ngắn: nhóm khổng lồ, mất gần hết dữ liệu khi giữ một mẫu mỗi nhóm.
