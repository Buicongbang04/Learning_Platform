# Lời giải: KFold, GroupKFold và chia theo thời gian

Notebook lời giải: `validation.ipynb` (chạy được toàn bộ khi đã tải Olist, khoảng 30 giây).

## Cách làm

- `time_cv_splits`: `np.argsort(dates, kind="stable")` cho thứ tự thời gian; chạy `TimeSeriesSplit`
  trên thứ tự đó rồi đổi vị trí về vị trí gốc bằng `order[idx]`. Không cần sắp xếp lại DataFrame.
- `cv_auc`: gọi `make_model()` mỗi fold. Dùng lại một model đã fit cũng chạy được với sklearn (vì
  `fit` học lại từ đầu), nhưng truyền một factory thì không phụ thuộc vào hành vi đó, và đúng với
  model có trạng thái (warm start, mạng nơ-ron).
- `compare_schemes`: ba danh sách split cùng chạy qua `cv_auc`.

## Kết quả trên Olist (dev = train + val, 63 830 đơn)

| Cách chia | AUC trung bình | Std giữa các fold |
| --- | --- | --- |
| KFold ngẫu nhiên | 0.7539 | 0.0048 |
| GroupKFold theo khách | 0.7538 | 0.0082 |
| Theo thời gian (5 fold) | 0.7433 | 0.0589 |

AUC từng fold thời gian: 0.668, 0.687, 0.783, 0.754, 0.825 (tháng 6/2017 → tháng 3/2018). AUC test
thật (tháng 4–8/2018): **0.6949**.

Chia thời gian trung bình chỉ thấp hơn KFold 0.01, nhưng nó cho thấy điều KFold che mất: hiệu năng
phụ thuộc giai đoạn, từ 0.67 tới 0.83. KFold nói "0.754 ± 0.005"; test cho 0.695, nằm ngoài xa khoảng
đó nhưng trong khoảng của chia thời gian.

## Feature cấp khách

Chỉ 5.9% đơn trong dev thuộc khách có từ 2 đơn trở lên. Thêm target encoding của
`customer_unique_id`: KFold tăng lên 0.7595, GroupKFold vẫn 0.7536. Phần tăng 0.006 ở KFold là ảo:
đơn khác của cùng khách (thường mua cùng lúc, cùng một trải nghiệm giao hàng) nằm ở fold train.

Trên dữ liệu mô phỏng mỗi khách 10 dòng, cùng hiện tượng lớn hơn nhiều: KFold khoảng 0.89, GroupKFold
khoảng 0.5 (qua 12 seed). Chia theo thời gian vẫn cho khoảng 0.85: mỗi khách có dòng ở mọi giai đoạn
nên chia thời gian không tách được khách. Hai loại phụ thuộc cần hai công cụ khác nhau.

## Trả lời bốn câu hỏi

Xem cell cuối của notebook lời giải. Ý chính: báo cáo theo chia thời gian, nêu cả khoảng giữa các
giai đoạn; GroupKFold khi sản phẩm phục vụ khách mới; AUC test thấp hơn không phải lỗi của CV mà là
thế giới thay đổi, và chia thời gian là cách duy nhất cho thấy trước điều đó có thể xảy ra.

## Sai lầm hay gặp

- `TimeSeriesSplit` trên DataFrame chưa sắp theo thời gian: nó chỉ chia theo thứ tự dòng.
- Chia theo thời gian nhưng feature tổng hợp (tỉ lệ seller, target encoding) tính trên toàn bộ dữ
  liệu trước khi chia: cách chia đúng không cứu được feature rò rỉ (bài Advanced 01).
- Thiếu `gap` khi nhãn cần thời gian để "chín": review được trả lời trung vị 1.9 ngày sau khi giao
  (90% trong 5.3 ngày), nên các đơn cuối fold train có thể chưa có nhãn ở thời điểm thật. Với nhãn
  trễ dài (churn 90 ngày) gap là bắt buộc.
