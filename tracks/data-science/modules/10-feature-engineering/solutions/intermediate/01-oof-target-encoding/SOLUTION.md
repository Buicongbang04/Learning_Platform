# Lời giải: target encoding out-of-fold

Tệp lời giải: `target_encoding.py`.

## Cách làm

- `fit_target_encoding`: `groupby` theo category để lấy tổng và số dòng, rồi m-estimate. Đặt `y`
  cùng index với `categories` trước khi `groupby`. Prior tính trên mọi dòng (kể cả dòng có category
  NaN), vì đó là xác suất nền thật của dữ liệu train.
- `transform_target_encoding`: `map` rồi `fillna(prior)`; category lạ và NaN cùng nhận prior.
- `oof_target_encoding`: mỗi fold dùng bảng **và prior** học từ các fold khác. Fold chia bằng
  `KFold(shuffle=True)` độc lập với nhãn, nên đổi nhãn của một dòng không đổi cách chia fold; đó là
  điều test kiểm.

## Vì sao mã hoá ngây thơ là leakage

Với category có ít dòng, trung bình nhãn của category chứa phần lớn là nhãn của chính dòng đang
được mã hoá. Ví dụ cực đoan: category chỉ có một dòng, smoothing 0, mã chính là nhãn. Model học được
"feature này gần bằng nhãn" trên train và áp dụng cho validation, nơi điều đó không còn đúng.

Trên Olist (`customer_zip_code_prefix`, 12 036 giá trị trong train, phần lớn chỉ vài đơn):

| Mã hoá | AUC trên train | AUC trên validation |
| --- | --- | --- |
| Ngây thơ (smoothing 20) | 0.856 | 0.536 |
| Out-of-fold (smoothing 20) | 0.538 | (val dùng bảng học trên toàn train) |

Smoothing 20 không đủ để chặn rò rỉ: smoothing chỉ giảm độ lớn, OOF mới cắt đường đi của nhãn.

Với `seller_id` đưa vào model logistic cùng các feature của Intermediate 02 (mã hoá trước, rồi làm một cột số): mã ngây thơ
nhận hệ số 0.482 và AUC validation 0.797; mã OOF nhận hệ số 0.199 và AUC 0.803. Model tin feature
rò rỉ quá mức và trả giá trên dữ liệu mới.

## AUC dưới 0.5 trên nhiễu

Trên nhãn ngẫu nhiên, mã OOF thường cho AUC hơi dưới 0.5 (0.44–0.51 qua 12 seed). Trong một category,
các dòng nhãn 1 bị loại khỏi bảng của chính chúng, nên thấy tỉ lệ thấp hơn các dòng nhãn 0. Hiệu ứng
này nhỏ với category lớn và là cái giá chấp nhận được; có thể giảm bằng nhiều fold hơn.

## So với sklearn

`sklearn.preprocessing.TargetEncoder` làm đúng ý tưởng này: `fit_transform` trên train dùng cross
fitting, `transform` trên dữ liệu mới dùng bảng học trên toàn train. Smoothing mặc định là
empirical Bayes (`smooth="auto"`), tự chọn mức co theo phương sai trong và giữa category. Trong
pipeline nên dùng nó; tự cài một lần để hiểu nó chặn leakage ở đâu.

## Khi nào dùng target encoding

| Tình huống | Nên dùng |
| --- | --- |
| Vài chục giá trị trở xuống | One-hot (dễ hiểu, không cần nhãn) |
| Hàng nghìn giá trị, có tín hiệu (seller, sản phẩm, zip) | Target encoding OOF, hoặc feature tổng hợp point-in-time |
| Hàng triệu giá trị, luồng dữ liệu liên tục | Hashing, embedding |
| Category gắn với thời gian (seller tốt lên/xấu đi) | Lịch sử point-in-time (bài Advanced 01) thay vì một con số tĩnh |
