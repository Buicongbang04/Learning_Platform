# Lời giải: availability và error budget từ danh sách incident

Code đầy đủ ở `availability.py` cạnh tệp này.

## Cách làm

1. **`allowed_downtime`**: error budget là phần không đạt SLO, nên `window * (1 - slo)`. Chặn SLO ngoài `(0, 1)` vì
   lỗi hay gặp nhất là truyền `99.9` thay vì `0.999`: không chặn thì hàm trả một khoảng âm và mọi phép tính sau đều
   sai mà không ai biết.
2. **`merge_outages`**: sắp theo điểm đầu, đi một lượt, nới khoảng cuối khi khoảng mới bắt đầu không muộn hơn điểm
   cuối của nó (dùng `<=` để gộp cả hai khoảng nối liền). Độ phức tạp là của bước sắp.
3. **`downtime`**: lọc `impact == "outage"`, đọc thời điểm có múi giờ, cắt theo cửa sổ, **rồi** mới gộp. Cắt trước
   giúp incident nằm ngoài cửa sổ biến mất tự nhiên (sau khi cắt, `begin >= finish`). Incident chưa đóng tính tới
   `end`; kiểm "đóng trước khi mở" chỉ khi có `resolved_at`, để incident chưa đóng nhưng mở sau cửa sổ không báo
   lỗi oan.
4. **`availability`** và **`budget_remaining`** là phép tính trên kết quả trên. Ngân sách được phép âm: số âm là
   thông tin quan trọng (đã tiêu quá bao nhiêu) cho error budget policy.

## Bảng tham khảo

$$
\text{allowed downtime} = (1 - \text{SLO}) \times \text{window}
$$

| SLO | 30 ngày | 1 năm |
| --- | --- | --- |
| 99% | 7 giờ 12 phút | 3 ngày 15 giờ 36 phút |
| 99,5% | 3 giờ 36 phút | 1 ngày 19 giờ 48 phút |
| 99,9% | 43 phút 12 giây | 8 giờ 45 phút 36 giây |
| 99,95% | 21 phút 36 giây | 4 giờ 22 phút 48 giây |
| 99,99% | 4 phút 19,2 giây | 52 phút 33,6 giây |

Mỗi số 9 thêm vào cắt budget còn một phần mười. Với 99,99%, một lần deploy lỗi cần 5 phút để phát hiện và rollback
đã tiêu hết budget cả tháng: đó là lý do SLO cao bắt buộc phải có canary và rollback tự động, không chỉ "cẩn thận hơn".

## Những chỗ test bắt

- **Hai alert cùng một lần sập**: API và worker cùng kêu, 10:00–10:30 và 10:10–10:40. Cộng thẳng ra 60 phút, thực
  tế người dùng mất 40 phút. Trên hệ thống thật, mỗi lần sập Postgres sinh ra hàng chục alert từ mọi service phụ
  thuộc; không gộp thì availability tụt vô lý và team mất niềm tin vào con số.
- **Qua nửa đêm, lệch offset**: `23:30+07:00` tới `17:15Z` là 45 phút. Ai so giờ trong ngày mà bỏ ngày, hay bỏ
  offset, sẽ ra số âm hoặc gần 24 giờ.
- **Cắt theo cửa sổ**: incident 23:00 ngày 30/9 tới 00:20 ngày 1/10 chỉ tính 20 phút cho tháng 10; phần còn lại
  thuộc báo cáo tháng 9. Không cắt thì cùng một phút bị tính vào hai tháng.
- **`degraded` không phải downtime**: với availability nhị phân (sập/không sập). Senior nên nói thêm: chậm nặng vẫn
  là hỏng với người dùng, nên SLO tốt đo theo request (tỉ lệ request thành công và đủ nhanh), không đo theo phút.
  Module 16 đi sâu phần này.

## Đánh đổi khi đo reliability

- **Theo thời gian hay theo request**: đếm phút sập dễ hiểu nhưng bỏ qua lỗi một phần (3% request lỗi trong 2 giờ
  vẫn tính là "chạy"). SLO theo request (`good / total`) chính xác hơn nhưng cần metrics ứng dụng, như
  `http_requests_total` của Olist Shop.
- **Đo từ đâu**: ping từ bên ngoài thấy cái người dùng thấy nhưng bỏ sót lỗi logic; metric nội bộ thấy chi tiết
  nhưng bỏ sót lỗi DNS, TLS, load balancer. Hệ thống trưởng thành dùng cả hai.
- **Ai mở và đóng incident**: nếu incident đóng khi người trực nhớ ra bấm nút, `resolved_at` muộn hơn thực tế. Gắn
  thời điểm đóng vào lúc metric hồi phục, không vào lúc con người bấm.
