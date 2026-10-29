# Lời giải: bốn baseline

## Khi nào mỗi baseline mạnh

| Baseline | Giả định ngầm | Mạnh khi |
| --- | --- | --- |
| Naive | Chuỗi là random walk: tương lai giống hiện tại nhất | Giá cổ phiếu, tỉ giá, chuỗi không có mùa vụ |
| Mean | Chuỗi dừng quanh một mức | Nhiễu trắng quanh mức ổn định |
| Drift | Random walk có xu hướng | Chuỗi tăng đều (số khách lũy kế) |
| Seasonal naive | Mùa vụ lặp lại y hệt | Chuỗi bán lẻ theo ngày (mùa vụ tuần), điện năng theo giờ |

Trên số đơn Olist theo ngày, seasonal naive (m = 7) là baseline đúng: thứ Bảy, Chủ nhật luôn ít đơn
hơn thứ Hai. Backtest 12 origin của bài Intermediate 02 cho thấy SARIMA chỉ thắng nó khoảng 5% MASE.

## Đúng pha của seasonal naive

Công thức của Hyndman & Athanasopoulos:

$$
\hat y_{T+h} = y_{T + h - m(k+1)}, \qquad k = \lfloor (h - 1)/m \rfloor
$$

Cài đặt gọn nhất: `y[-m:][np.arange(h) % m]`. Bước 1 lấy phần tử đầu của mùa vụ cuối, tức là
`y[T - m + 1]` (cùng thứ trong tuần với ngày `T + 1`), bất kể chuỗi kết thúc vào thứ mấy.

## Drift

Độ dốc là `(y_T − y_1)/(T − 1)`: tương đương trung bình của các sai phân bậc 1. Nó chỉ dùng hai
điểm đầu và cuối, nên rất nhạy nếu điểm đầu là bất thường (Olist tháng 1/2017 mới khởi động). Khi
dùng drift trên dữ liệu thật, cắt bỏ giai đoạn khởi động.

## Trong thực tế

Baseline không phải bài tập cho người mới: nó là bước đầu tiên của **mọi** dự án dự báo. Báo cáo
"model của tôi đạt MAPE 12%" vô nghĩa nếu seasonal naive đạt 13%. Ghi baseline vào cùng bảng kết quả,
cùng backtest, cùng metric.
