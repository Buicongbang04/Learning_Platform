# Fine-tune để nhớ luật hay RAG: số đo trên Zalo Legal

TODO: viết theo khung trong README của bài (ít nhất 400 từ). Người đọc là khách hàng muốn "fine-tune model trên văn bản
luật": họ cần thấy bằng số điều gì xảy ra, và bạn khuyên gì thay vào.

## Tóm tắt

TODO: 2–3 câu có số: closed-book fine-tune đạt bao nhiêu trên câu chưa thấy, BM25 đạt bao nhiêu, và khuyến nghị.

## Thiết lập

TODO: định dạng trích dẫn, 300 câu ghim và 300 câu train dùng để đo, các cấu hình (BM25, model gốc, SFT trên câu hỏi
train, SFT thêm tiêu đề mọi điều), siêu tham số, phần cứng, thời gian.

## Kết quả

TODO: bảng `exact`, `law`, `format` cho mọi cấu hình trên cả câu ghim và câu train; thời gian train, VRAM. Đọc bảng:
model học được gì, không học được gì.

## Phân tích lỗi

TODO: đọc tận mắt ít nhất 10 trích dẫn sai của model fine-tune: số hiệu có tồn tại trong corpus không, có phải văn bản
xuất hiện nhiều trong train không, điều số bao nhiêu. Phân loại lỗi.

## Khuyến nghị

TODO: khi nào fine-tune có ích trong hệ thống trả lời luật (và ở thành phần nào), khi nào không; điều gì bảng của bạn
chưa đo.
