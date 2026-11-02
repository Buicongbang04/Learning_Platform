# Lời giải: chuẩn hoá NFC và chunk văn bản luật

## Cách làm

**`normalize`** chuẩn hoá NFC trước mọi bước khác, rồi xử lý từng dòng: `" ".join(line.split())` vừa gộp mọi
loại khoảng trắng (tab, `\u00a0`) vừa bỏ hai đầu; dòng rỗng bị lọc. NFC phải đi trước: trên bản NFD, chữ "ậ"
là ba code point, mọi phép đếm ký tự, regex `\w` và so khớp với câu hỏi gõ NFC đều lệch (mục 2 lý thuyết).

**`chunk_fixed`** kiểm tham số trước tiên: với `overlap >= size` bước nhảy `size - overlap` bằng 0 hoặc âm và
vòng lặp không bao giờ tiến. Sau đó lấy `text[start:start + size]`, dừng ngay khi chunk vừa lấy đã chạm cuối
(`start + size >= len(text)`), nếu không thì `start += size - overlap`. Điều kiện dừng này cho đúng
$$\left\lceil \frac{L - O}{S - O} \right\rceil$$ chunk. Cách viết chỉ dừng khi `start >= len(text)` sinh thêm chunk thừa
mỗi khi chunk trước đã chạm cuối mà bước nhảy chưa vượt qua cuối: với $$L = 90, S = 50, O = 10$$, chunk ở 40 đã lấy tới
ký tự 90, nhưng vòng lặp vẫn tạo `text[80:90]`, nằm trọn trong chunk trước. Chunk trùng này chiếm một chỗ trong top-k mà
không thêm thông tin; test đếm số chunk để bắt lỗi đó.

**`chunk_legal`** dùng một hàm phụ `_split_at(lines, pattern)`: dòng khớp mẫu mở nhóm mới, dòng khác vào nhóm
đang mở, hoặc vào phần "trước nhóm đầu". Gọi hai lần:

1. Thân Điều với mẫu khoản `\d+\.\s` (bắt buộc khoảng trắng sau dấu chấm, nên `150.000 đồng` không thành khoản).
   Phần trước khoản đầu, nếu có, là một đơn vị riêng; không có khoản thì cả thân là một đơn vị.
2. Đơn vị dài hơn `max_chars` với mẫu điểm `[a-zđ]\)\s`. Phần trước điểm đầu là **phần dẫn** của khoản.

Mỗi chunk là `tiêu đề + phần dẫn (nếu tách theo điểm) + nội dung`. Khoản dài mà không có điểm giữ nguyên.

## Vì sao giữ tiêu đề và phần dẫn

Một điểm như `b) Buông cả hai tay hoặc dùng chân điều khiển xe;` đứng một mình không nói được là luật nào và phạt bao
nhiêu. Mức phạt nằm ở phần dẫn của khoản (`2. Phạt tiền từ 300.000 đồng đến 500.000 đồng ... sau đây:`), loại phương
tiện nằm ở tiêu đề Điều. Ghép cả hai vào chunk làm câu hỏi "buông hai tay khi đi xe đạp điện bị phạt bao nhiêu" khớp
được cả BM25 lẫn embedding, và chunk có địa chỉ trích dẫn "điểm b khoản 2 Điều 5". Trên lát cắt Zalo ở mục 2 lý
thuyết, chunk theo khoản có tiêu đề thắng chunk cố định cùng cỡ 18 điểm MRR@10 (0.809 so với 0.628).

Cái giá: phần dẫn bị lặp ở mỗi điểm, nên tổng số ký tự phải embed tăng. Với ngưỡng 1 500 ký tự, chỉ khoản thật sự
dài mới bị tách, nên phần lặp nhỏ.

## Bẫy thường gặp

- Quên `đ)`: bảng chữ cái tiếng Việt có `đ` giữa `d` và `e`, mà `[a-z]` không chứa nó. Điểm `đ)` khi đó bị dính vào
  điểm `d)`.
- Mẫu khoản thiếu `\s` (`\d+\.`): dòng bắt đầu bằng số tiền `150.000 đồng` hoặc năm thành khoản mới.
- So ngưỡng có cộng độ dài tiêu đề, hoặc dùng `<` thay `<=`: lệch số chunk ở biên.
- Chunk trước, chuẩn hoá sau: offset và độ dài tính trên NFD không khớp văn bản lưu NFC.
- Chặn `overlap > size` mà quên `overlap == size`: bước nhảy 0, vòng lặp vô hạn.
