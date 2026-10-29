# Lời giải: profiling một bảng dữ liệu

Code: `profile.py`.

## Cách làm

- `profile`: một vòng qua các cột; `value_counts(dropna=True)` cho cả `top_value` lẫn mẫu số của
  `top_share`. Đặt index là tên cột để tra `out.loc["price", "missing_rate"]`.
- `duplicate_report`: `drop_duplicates(subset=key)` đếm key khác nhau; `duplicated(subset=key,
  keep=False)` đánh dấu **mọi** dòng thuộc key lặp (con số người phân tích cần: bao nhiêu dòng bị
  ảnh hưởng nếu join theo key này); `duplicated()` không subset đếm bản sao hoàn toàn.
- `iqr_outliers`: quantile mặc định của pandas, so sánh hai đuôi, NaN thành False.

## Kết quả trên Olist thật

| Kiểm tra | Kết quả | Đọc thế nào |
| --- | --- | --- |
| `review_id` | 98 410 key / 99 224 dòng, 1 603 dòng có key lặp, 0 dòng trùng hoàn toàn | Một review gắn với nhiều đơn: không phải khoá |
| `order_id` trong reviews | 98 673 key, 1 098 dòng có key lặp | Một đơn có thể có nhiều review: phải dedupe (giữ review mới nhất) |
| `(review_id, order_id)` | 0 dòng lặp | Đây mới là khoá của bảng |
| `review_comment_message` | thiếu 58.7% | Thiếu không ngẫu nhiên: khách hài lòng thường chỉ chấm sao |
| `price` theo IQR | 8 427 item (7.5%) | Q1 = 39.9, Q3 = 134.9: mọi item trên 277.4 BRL là "outlier" |

7.5% giá item bị đánh dấu không phải vì dữ liệu sai mà vì phân phối lệch phải: quy tắc IQR được
thiết kế cho phân phối gần đối xứng (trên phân phối chuẩn nó đánh dấu 0.7%). Với dữ liệu lệch phải,
áp IQR trên `log(price)`, hoặc dùng quy tắc nghiệp vụ (giá âm, giá 0, giá lớn hơn mức trần của sàn)
để tìm lỗi thật. **Outlier là câu hỏi, không phải lệnh xoá**: một chiếc tủ lạnh 6 735 BRL là đơn
hàng thật và đóng góp đáng kể vào doanh thu.

## Sai lầm hay gặp

- `nunique()` rồi so với `len(df)` để kết luận "không có khoá lặp" mà quên NaN (NaN không được
  `nunique` đếm).
- `top_share` chia cho tổng số dòng: cột thiếu 90% sẽ có `top_share` nhỏ một cách giả tạo.
- Đếm `duplicated()` (mặc định `keep="first"`) rồi báo "có 814 dòng review bị lặp": thật ra 1 603
  dòng thuộc nhóm lặp. Hai con số trả lời hai câu hỏi khác nhau; nói rõ bạn đang báo cái nào.
