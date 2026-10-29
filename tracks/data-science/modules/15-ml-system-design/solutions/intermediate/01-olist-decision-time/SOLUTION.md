# Lời giải: chọn thời điểm dự đoán và đổi metric ra tiền

Notebook lời giải: `decision.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Cách làm

- `build_orders` gộp item **sau khi** gắn bang khách, để `same_state` là "mọi seller cùng bang với khách"
  (`agg(... , ("same", "all"))`). Một đơn nhiều seller mà chỉ một seller cùng bang thì vẫn có chặng
  liên bang, nên không tính là cùng bang.
- `features_at` là **hợp đồng** giữa đóng khung bài toán và dữ liệu: viết danh sách feature theo thời
  điểm thành code để không ai vô tình đưa `handling_days` vào model lúc đặt hàng.
- `fit_predict` dùng LightGBM vì nó nhận NaN và cột `category`; mã category dựng từ train. Logistic
  regression trong `Pipeline` cũng đạt test (PR-AUC thấp hơn một chút).

## Kết quả trên Olist thật

96 470 đơn, 8.1% trễ; train / validation / test là 43 693 / 20 627 / 32 150 đơn, tỉ lệ trễ 6.6% /
14.6% / 6.0%.

| Thời điểm | ROC-AUC test | PR-AUC test | precision@500 |
| --- | --- | --- | --- |
| purchase | 0.707 | 0.120 | 0.146 |
| carrier | 0.807 | 0.378 | 0.744 |

Giá trị (tin nhắn 0.5 R$, V = 30 R$, Δ = 0.15, 23 tuần test):

| Chính sách | k | Precision | R$/tuần |
| --- | --- | --- | --- |
| carrier, top 5% | 1 607 | 0.391 | 87.9 |
| carrier, top 10% | 3 215 | 0.264 | 96.2 |
| purchase, top 10% | 3 215 | 0.137 | 16.4 |
| Luật còn dưới 5 ngày | 1 596 | 0.427 | 98.5 |

## Những điều người chấm muốn thấy trong câu trả lời

- PR-AUC giảm từ validation sang test là do prevalence (14.6% → 6.0%), không phải model hỏng.
- `precision@100` gần 1 vì 226 đơn trên test giao cho vận chuyển **sau** ngày hẹn: luật hiển nhiên.
  Báo cáo trung thực tách phần "dễ" này ra.
- Trên số gộp, luật một dòng ngang model về tiền. Nhưng 1 195 trong 1 596 đơn luật chọn là đơn mua
  08/2018 (ngày hẹn giao rút ngắn từ 06/2018, nguyên nhân chưa rõ), nên phải so tách giai đoạn ở cùng k:
  04–07/2018 luật 401 đơn, precision 0.494, model 0.564; 08/2018 luật 1 195 đơn, precision 0.404, model
  0.305. Hai giai đoạn cho kết luận ngược nhau. Ra mắt luật trước, model phải thắng luật trong từng
  giai đoạn trên holdout mới được thay.
- Khoảng 100 R$ mỗi tuần không đủ trả chi phí một hệ thống ML. Kết luận đúng là đi kiểm chứng V và Δ
  (thí nghiệm nhỏ, bài Advanced 02), không phải tuning thêm.

## Bẫy thường gặp

- Dùng `handling_days` cho model lúc đặt hàng: leak, PR-AUC đẹp giả.
- Mã hoá `customer_state` riêng cho train và test (`astype("category")` hai lần): cùng bang thành hai
  mã khác nhau, model đoán sai im lặng.
- Chọn tỉ lệ top k tốt nhất trên test rồi báo cáo giá trị trên chính test: lạc quan. Chọn trên
  validation.
