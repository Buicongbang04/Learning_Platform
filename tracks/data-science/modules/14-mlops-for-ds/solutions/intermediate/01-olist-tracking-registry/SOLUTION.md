# Lời giải: tracking và registry cho model review xấu

Notebook lời giải: `registry.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Kết quả trên Olist thật

| C | `val_auc` |
| --- | --- |
| 0.01 | 0.7998 |
| 0.1 | 0.7996 |
| 1.0 | 0.7987 |
| 10.0 | 0.7983 |

Champion là `C = 0.01`; AUC trên test là **0.693**. Hai nhận xét quan trọng hơn con số:

1. **Chênh lệch giữa các C là nhiễu.** 0.0015 AUC trên 20 nghìn đơn validation nhỏ hơn nhiều so với
   sai số của chính AUC. Tracking giúp bạn thấy điều đó bằng bảng, thay vì nhớ mang máng "C nhỏ
   tốt hơn". Chọn theo nguyên tắc định trước (metric validation cao nhất, hoà thì chọn model đơn
   giản hơn) và đừng kể chuyện về một khác biệt không có thật.
2. **Test thấp hơn validation 0.1 AUC, nhưng model không "tệ đi".** Validation (quý 1/2018) có
   14.4% đơn trễ, test chỉ 5.9%. `delay_days` là feature mạnh nhất: tập có nhiều đơn trễ thì dễ
   phân biệt hơn. AUC tính riêng trong nhóm đơn đúng hẹn và nhóm đơn trễ gần như không đổi giữa hai
   giai đoạn (README module, mục monitoring). Đây là **mix shift**, và là lý do metric monitoring
   phải được cắt theo segment.

## Các quyết định trong lời giải

- **Signature suy trên cả tập train, cột số ép float.** Suy trên 50 dòng đầu thì `approve_hours`
  (có 14 giá trị thiếu trong cả bảng) bị đánh dấu *required*: request có `null` bị từ chối ở
  production dù pipeline xử lý NaN được. Ép float vì schema enforcement của MLflow không tự đổi
  `int64` sang `float64`.
- **`pyfunc_predict_fn="predict_proba"`.** Mặc định pyfunc của một classifier gọi `predict`, trả
  nhãn 0/1 với ngưỡng 0.5. Ngưỡng là quyết định kinh doanh và review xấu chỉ chiếm khoảng 12%:
  gần như không đơn nào vượt 0.5, service sẽ trả toàn số 0.
- **Định dạng skops.** MLflow 3 mặc định không dùng pickle cho scikit-learn vì nạp pickle là chạy
  code tuỳ ý. Cái giá là phải khai báo kiểu tin cậy (`numpy.dtype` cho OneHotEncoder).
- **Đăng ký từ `model_uri`.** Ở MLflow 3, `log_model` tạo một LoggedModel có URI riêng; đăng ký từ
  `runs:/<id>/model` vẫn chạy nhưng MLflow phải tự tra ngược và in cảnh báo.
- **Alias thay cho stage.** Các stage cố định `Staging`/`Production` đã bị bỏ; alias (`champion`,
  `challenger`) là con trỏ đặt tên tự do tới một version. Rollback là trỏ alias về version cũ.

## Câu hỏi cuối notebook

1. Không đáng: xem nhận xét 1.
2. Tập test khác: xem nhận xét 2.
3. Thường **có** fit lại trên train + validation với C đã chọn (dữ liệu gần nhất là quý giá nhất),
   nhưng phải ghi thành **một run mới** có tag nói rõ khoảng dữ liệu, và metric đi kèm là AUC
   test của model đó. Đăng ký run này, không phải run dùng để chọn C. Lỗi hay gặp: đăng ký run chọn
   C rồi deploy một model khác được train lại ngoài MLflow, làm mất dấu vết.

## Sai lầm hay gặp

- Chọn champion theo AUC test: test bị "dùng" và không còn là ước lượng khách quan.
- Service nạp theo số version (`models:/x/3`): mỗi lần đổi model phải sửa cấu hình và deploy lại.
- Quên ghi khoảng dữ liệu train: hai run cùng params khác dữ liệu trông như kết quả không ổn định.
