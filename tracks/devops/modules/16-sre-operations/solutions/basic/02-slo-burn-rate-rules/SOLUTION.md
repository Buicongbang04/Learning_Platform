# Lời giải: SLO as code và burn-rate alert

## Cách làm

- `slo.yaml`: availability lấy 5xx trên route `/orders/{order_id}` (`status=~"5.."`), latency lấy `_count` trừ bucket `le="0.25"`. Cả tử
  và mẫu phải lọc cùng `job` và `path`, nếu không thì tỉ lệ trộn route khác vào.
- `load_spec` kiểm sớm mọi thứ có thể sai khi người khác sửa tệp: tên dùng làm nhãn và tên group, `objective` kiểu số (YAML đọc
  `99.9%` thành chuỗi, `true` thành bool, mà bool là con của int trong Python), cửa sổ cố định 30 ngày vì bảng `ALERTS` được tính cho
  30 ngày.
- Recording rule cho từng cửa sổ: alert chỉ đọc lại series đã tính sẵn, Prometheus không phải tính `rate` trên 3 ngày dữ liệu mỗi lần
  đánh giá, và dashboard dùng chung số với alert.
- Alert: `slo:sli_error:ratio_rate1h{slo="x"} > (14.4 * 0.005) and slo:sli_error:ratio_rate5m{slo="x"} > (14.4 * 0.005)`. Nhãn `slo` đi
  theo series nên mỗi SLO một alert riêng. Không đặt `for`: cửa sổ ngắn đã là độ trễ, và `for` chỉ làm alert tới muộn hơn mà không
  bớt nhiễu.

## Bảng burn rate (SLO 30 ngày)

| Mức | Burn rate | Cửa sổ dài | Cửa sổ ngắn | Budget tiêu khi bắn |
| --- | --- | --- | --- | --- |
| page | 14,4 | 1h | 5m | 2% |
| page | 6 | 6h | 30m | 5% |
| ticket | 3 | 1d | 2h | 10% |
| ticket | 1 | 3d | 6h | 10% |

Budget tiêu bằng burn rate nhân độ dài cửa sổ dài chia 720 giờ: 14,4 nhân 1 chia 720 là 2%. Cửa sổ ngắn khoảng 1/12 cửa sổ dài để
alert tắt nhanh khi sự cố đã hết (cửa sổ dài còn nhớ lỗi cũ thêm cả giờ).

## Vì sao một phút lỗi 100% không page

Sau một ngày 100 request mỗi phút, một phút lỗi hoàn toàn cho 100 request xấu. Cửa sổ 5 phút thấy 20% lỗi (burn rate 40), nhưng cửa
sổ 1 giờ chỉ thấy 100 trên 6000, tức 1,7% (burn rate 3,3, dưới 14,4). Điều kiện `and` không thoả nên không ai bị đánh thức. Alert
một cửa sổ 5 phút sẽ page mỗi lần như vậy.

## Mở rộng

- Công cụ làm đúng việc này: Sloth, Pyrra (đọc `PrometheusServiceLevel`/`ServiceLevelObjective`), spec OpenSLO. Bài viết tay để thấy bên
  trong.
- Traffic thấp (vài request mỗi phút, ví dụ ban đêm) làm tỉ lệ nhảy mạnh. Cách xử lý: thêm điều kiện số request tối thiểu, gộp nhiều
  route vào một SLO, hay dùng probe tổng hợp.
