# Lời giải: LightGBM với lag feature cho Rossmann

Notebook lời giải: `lgbm_lags.ipynb` (chạy được toàn bộ khi đã tải `store-sales`).

## Dữ liệu

50 cửa hàng (id 1 tới 60, bỏ các cửa hàng thiếu dữ liệu 2014-07-01 tới 2014-12-31), 942 ngày mỗi
cửa hàng, 47 100 dòng. Ngày mở cửa có khuyến mãi bán trung bình 8 228 €, không khuyến mãi 5 929 €
(toàn bộ dữ liệu). Khuyến mãi chạy xen kẽ: tuần có, tuần không.

## Kết quả (origin 2015-06-20, 42 ngày, ngày mở cửa có doanh thu)

| Cách | MAE (€) | RMSPE |
| --- | --- | --- |
| Seasonal naive (cùng thứ tuần trước) | 1 501 | 0.350 |
| LightGBM, feature lùi ≥ 42 ngày | 665 | 0.138 |
| LightGBM có `lag_1`, `lag_7` (leakage) | 575 | 0.114 |

Hai origin trước: 2015-03-28 LightGBM 785 so với 2 181; 2015-05-09 LightGBM 641 so với 1 360.

## Vì sao như vậy

- Baseline "tuần trước" thua vì tuần trước có trạng thái khuyến mãi **ngược** với tuần cần dự báo
  ở một nửa số ngày. LightGBM nhận `Promo` của chính ngày cần dự báo: lịch khuyến mãi được lên trước,
  nên là biến **biết trước** hợp lệ.
- Theo split importance, `lag_364` (cùng thứ năm trước), `day`, `month` và `roll_mean_28` được dùng
  để chia nhiều nhất: mùa vụ năm, mùa vụ trong tháng (ngày nhận lương) và mức gần nhất được phép
  thấy. `Promo` ít lần chia nhưng mỗi lần chia tách hai nhóm chênh nhau khoảng 39%; split importance
  đếm số lần chia, không đo đóng góp vào độ chính xác (dùng SHAP hoặc permutation importance, module 11).
- Bản có leakage đẹp hơn khoảng 13% MAE, nhưng không thể đạt được: để dự báo ngày thứ 30 của
  horizon, ta không có doanh thu của ngày thứ 29. Leakage kiểu này rất hay gặp khi dựng feature trên
  toàn bộ bảng rồi chia train/test **sau đó**.

## Chọn chiến lược đa bước

| Chiến lược | Cách làm | Đánh đổi |
| --- | --- | --- |
| Direct, một model, lag ≥ H (bài này) | Mọi lag lùi ít nhất H | Đơn giản; bỏ phí thông tin gần nhất cho các bước gần |
| Direct, một model mỗi horizon (hoặc mỗi tuần) | Model k dùng lag ≥ k | Chính xác hơn ở bước gần; H model để huấn luyện và theo dõi |
| Recursive | Một model lag 1, dự báo dần và đưa dự báo vào làm lag | Một model; sai số tích luỹ, khó song song |

## Rubric cho phần nhận xét

| Tiêu chí | Đạt khi |
| --- | --- |
| Con số | So LightGBM với baseline bằng cùng metric, trên hơn một origin |
| Cơ chế | Giải thích vai trò của `Promo` và feature mùa vụ năm |
| Leakage | Nói được vì sao bản có `lag_1` không dùng được, ước lượng mức "đẹp giả" |
| Horizon ngắn hơn | Đề xuất lag/rolling phù hợp hoặc chiến lược direct nhiều model |

## Sai lầm hay gặp

- `df.Sales.shift(42)` không `groupby` Store: dòng đầu của cửa hàng 2 nhận doanh thu cửa hàng 1.
- Coi ngày đóng cửa là doanh thu 0 trong rolling mean: mức trung bình bị kéo xuống theo số Chủ nhật.
- Dùng `Customers` làm feature: tương quan rất cao với `Sales` nhưng chỉ biết sau khi ngày kết thúc.
- Đánh giá RMSPE trên cả ngày đóng cửa: chia cho 0.
