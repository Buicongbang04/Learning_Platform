# Lời giải: bốn SLI, error budget và burn rate

`slo.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Mỗi SLI là một tỉ lệ sự kiện tốt trên sự kiện hợp lệ.** Khác nhau ở mẫu số: khả dụng xét mọi yêu cầu; độ trễ chỉ xét yêu
  cầu đã được phục vụ (một lỗi 503 trả trong 5 ms không phải "nhanh", nó đã bị khả dụng tính rồi); chất lượng chỉ xét dự đoán đã
  có nhãn; freshness xét mọi yêu cầu vì yêu cầu nào cũng dùng feature.
- **`None` khác 1.0.** Không có nhãn nghĩa là chưa biết chất lượng. Trả 1.0 sẽ làm dashboard xanh đúng lúc job join nhãn chết,
  đó là cách SLO nói dối (bài Intermediate 01 viết alert riêng cho trường hợp này).
- **Budget là `(1 - SLO) x cửa sổ`.** 99.5% trong 30 ngày là 216 phút; 99.9% là 43.2 phút. Mỗi chữ số 9 thêm vào chia budget cho 10.
- **Burn rate tách "nặng bao nhiêu" khỏi tỉ lệ lỗi tuyệt đối.** Burn rate 1 là hết budget đúng cuối cửa sổ; 14.4 trong 1 giờ là
  `14.4 x 1 / 720 = 2%` budget 30 ngày. Trên log mẫu, giờ cuối có 10% lỗi nên burn rate 1h khoảng 20, trong khi cửa sổ 6h pha loãng
  sự cố với 5 giờ bình thường và cho số nhỏ hơn nhiều: đó là lý do cần nhiều cửa sổ.
- **Cửa sổ nửa mở `[now - w, now)`.** Tránh đếm một sự kiện hai lần khi trượt cửa sổ liên tiếp.

## Lỗi hay gặp

- Tính latency SLI trên mọi yêu cầu: lỗi nhanh làm latency đẹp lên đúng lúc service hỏng.
- Coi `abs_error_min = None` là 0 (đúng tuyệt đối): quality SLI đi lên khi nhãn về chậm.
- `remaining` bị kẹp về 0 khi tiêu quá budget: mất thông tin "đã vượt bao nhiêu", thứ chính sách freeze cần.
