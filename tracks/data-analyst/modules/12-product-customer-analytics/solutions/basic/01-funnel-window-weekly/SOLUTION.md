# Lời giải: funnel theo tuần có cửa sổ chuyển đổi

## Cách làm

1. **`to_events`**: dựng `DataFrame` mới với bốn cột; `pd.to_datetime(raw["timestamp"], unit="ms")` vì Retailrocket
   ghi epoch **mili giây** (đọc nhầm là giây cho năm 47000).
2. **`ordered_first_times`**: `t_view` là `min` của `view` theo visitor. Ghép `t_view` vào các dòng `addtocart`
   (`join(..., how="inner")`), giữ dòng `event_time >= t_view`, lấy `min` → `t_cart`. Làm y hệt cho `transaction`
   với `t_cart`. `pd.concat([t_view, t_cart, t_buy], axis=1)`: index là mọi visitor có `view`, hai cột sau `NaT`
   khi chưa tới bước đó. Đây là funnel **có thứ tự**: 2 129 visitor thêm giỏ trước lần xem đầu (module 03) không được
   tính ở bước giỏ.
3. **`conversion_within`**: `(t_buy - t_view).dropna()` đổi ra giờ, rồi `(waited <= h).mean()` cho từng `h`. Mẫu số
   là **người mua**, không phải mọi visitor: câu hỏi là "cửa sổ giữ lại bao nhiêu phần người mua".
4. **`weekly_funnel`**: tuần là `t_view.dt.to_period("W-SUN").dt.start_time`; hai cột cờ
   `(t_cart - t_view) <= window` và `(t_buy - t_view) <= window` (`NaT` cho `False`), `groupby(tuần).agg(...)`.
   `mature = tuần + 7 ngày + window <= data_end`: visitor vào phút cuối của Chủ nhật cũng cần đủ `window`.

## Số liệu trên log thật

| Chỉ số | Giá trị |
| --- | --- |
| Funnel có thứ tự | 1 404 179 → 32 934 → 9 952 visitor |
| Thời gian xem → mua (người mua) | phân vị 25: 0.1 giờ; trung vị **0.4 giờ**; phân vị 75: 9.9 giờ; phân vị 90: 219.7 giờ; mean 101.5 giờ |
| Mua trong 1 giờ / 1 ngày / 7 ngày / 30 ngày | 62.8% / 79.6% / **88.6%** / 95.3% |
| Tuần (cửa sổ 7 ngày) | 21 tuần, **19 đã chín**; cửa sổ 1 ngày: 20 tuần chín; 30 ngày: 16 |
| Buy rate 7 ngày, tuần đã chín | 0.48% (tuần 10/08) tới 0.79% (tuần 27/04, chỉ có 03/05) |
| Tuần chưa chín | 07/09: 0.58%; 14/09: **0.49%** (32 823 visitor, 4 ngày dữ liệu) |
| Không cửa sổ | tuần 27/04: 1.07%, 04/05: 1.01%, ... 14/09: 0.49%: giảm dần vì visitor vào sớm có nhiều thời gian hơn |
| Theo sản phẩm | 73 sản phẩm có ≥ 500 người xem, 23 không có lượt thêm giỏ; sản phẩm xem nhiều nhất 2 911 người xem, 2 lượt thêm giỏ; 565 sản phẩm có người mua nhiều hơn người thêm giỏ |

**Đọc số**:

- Phân phối thời gian tới khi mua lệch rất mạnh: trung vị 23 phút nhưng mean 101 giờ. Báo "trung bình 4 ngày để
  mua" là sai câu chuyện; báo "phần lớn mua trong phiên đầu, 1/10 mua sau hơn 9 ngày".
- Cửa sổ 7 ngày là đánh đổi hợp lý cho báo cáo tuần: giữ 88.6% người mua, và con số một tuần chín sau 14 ngày tính
  từ đầu tuần. Cửa sổ 30 ngày giữ 95.3% nhưng chỉ còn 16 tuần chín và phải chờ hơn một tháng.
- Trong 19 tuần chín, buy rate 0.48-0.79%. Bỏ tuần đầu (một ngày, cắt trái) thì dải là 0.48-0.76%. Một tuần 0.5%
  nằm trong dao động bình thường; muốn nói "giảm" phải vượt dải này, hoặc tách tiếp theo bước và phân khúc.
- Headline mẫu cho PM: "Tuần 31/08: 1.9% người xem thêm giỏ, 0.53% mua trong 7 ngày, trong dải 19 tuần (0.48-0.79%);
  hai tuần gần nhất chưa đủ 7 ngày quan sát".

## Đáp án trắc nghiệm

- `median-wait` (a) **khoảng 23 phút**. (b) là phân vị 75, (c) là mean (bị đuôi kéo), (d) là phân vị 90.
- `window-7d` (c) **88.6%**. (a), (b), (d) là cửa sổ 1 giờ, 1 ngày, 30 ngày.
- `mature-weeks` (b) **19 tuần**: hai tuần 07/09 và 14/09 chưa chín. (a) là số tuần chín với cửa sổ 30 ngày.
- `best-week` (a): dữ liệu bắt đầu 03:00 Chủ nhật 03/05 nên "tuần" 27/04 chỉ có một ngày (7 845 visitor), và lần xem
  đầu trong dữ liệu chưa chắc là lần xem đầu thật (cắt trái): người quay lại mua bị coi là người mới. (c) sai vì tuần
  đó đã chín.
- `no-window` (d): không có cửa sổ, tỉ lệ của tuần đầu là "mua trong hơn 4 tháng", của tuần cuối là "mua trong vài
  ngày". Đường giảm dần là do cách đo, không phải hành vi.
- `monday-report` (c) **tuần 24/08**: 24/08 + 7 + 7 = 07/09, trước 11/09. Tuần 31/08 cần tới 14/09.
- `last-week` (b): tuần 14/09 chưa đủ cửa sổ (và chỉ có 4 ngày); để nó cạnh tuần khác là báo một cú giảm không có
  thật. (c) vẫn đặt con số lên chart; (d) che mất dữ liệu bằng một số không phải của tuần đó.
- `popular-no-cart` (d) **23 sản phẩm**. Trước khi nói "trang sản phẩm tệ", kiểm hết hàng / ngừng bán (bản gốc
  Retailrocket có thuộc tính `available`, bản làm sạch đã bỏ) và sự kiện giỏ có được gửi từ trang đó không.
