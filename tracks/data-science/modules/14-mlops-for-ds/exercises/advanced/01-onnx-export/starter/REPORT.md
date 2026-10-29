# Báo cáo: đưa model review xấu sang ONNX

Xoá mọi dòng TODO khi viết xong. Mọi con số phải lấy từ code bạn chạy (model Olist thật của module,
xem bài Intermediate 01).

## 1. Kết quả parity

TODO: model nào, bao nhiêu dòng, sai lệch lớn nhất, tỉ lệ khớp. Với model cây, giải thích chênh
lệch nếu có.

## 2. Độ trễ

TODO: so độ trễ chấm 1 dòng và cả tập test giữa scikit-learn và onnxruntime (cách đo, số lần lặp,
máy). Con số này có ý nghĩa gì cho một service cần p99 dưới 10 ms?

## 3. Những gì không chuyển được

TODO: các bước trong pipeline mà converter không hỗ trợ hoặc hỗ trợ khác (gặp gì khi thử
SimpleImputer cho cột chuỗi, TargetEncoder, hàm tự viết). Bạn đã xử lý thế nào?

## 4. Hợp đồng với service gọi model

TODO: service Go/Rust/C++ cần biết gì để gọi model đúng (tên input, kiểu, thứ tự, cách điền giá
trị thiếu, output nào là xác suất). Bạn version hợp đồng đó ra sao và kiểm nó trong CI thế nào?

## 5. Khuyến nghị

TODO: nên dùng ONNX cho model này không, hay giữ Python service? Đánh đổi.
