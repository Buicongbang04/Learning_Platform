# Lời giải: chọn công cụ product analytics, loại retention và đọc nhanh LTV/CAC

## Cách làm

Mỗi câu chọn công cụ đi qua bốn câu hỏi của phần 7 lý thuyết: ai dùng, con số có phải chính thức không, cần nối với
dữ liệu nào, dữ liệu được phép nằm ở đâu. Mỗi câu định nghĩa đi từ câu hỏi business: câu hỏi về **người** hay về
**một lượt dùng**, sản phẩm được dùng hằng ngày hay mua thưa. Câu tính nhẩm: viết công thức ra rồi thay số.

## Đáp án từng câu

| Câu | Đáp án | Tiêu chí quyết định |
| --- | --- | --- |
| `tool-pm-selfserve` | b. Amplitude / Mixpanel | PM tự làm, câu hỏi nhanh, funnel và retention dựng sẵn |
| `tool-official-ltv` | d. Warehouse + SQL/dbt | Số chính thức, phải nối đơn hàng, hoàn tiền, chi phí; kiểm lại được |
| `tool-campaign-traffic` | a. GA4 + UTM | Nguồn traffic, chiến dịch quảng cáo của website |
| `tool-selfhost` | c. PostHog tự host | Dữ liệu ở lại hạ tầng mình, cần feature flag và session replay |
| `tool-cdp` | d. CDP (Segment, RudderStack) | Instrument một lần, nhiều đích, kiểm schema theo tracking plan |
| `retention-wholesale` | a. Unbounded | Mua thưa, câu hỏi "chưa bỏ hẳn" |
| `retention-daily-app` | b. N-day theo cohort cài đặt | Dùng hằng ngày, so hai bản onboarding |
| `funnel-unit` | c. Theo phiên | Câu hỏi về "một lượt ghé" |
| `simple-ltv` | a. 300 USD | 50 × 6 × 0.4 / (1 − 0.6) = 120 / 0.4 |
| `payback` | d. k = 3 | Luỹ kế 30, 45, 60, **70** |
| `rfm-quintile-f` | c. Chia ngẫu nhiên khách cùng giá trị | 34% khách cùng F = 1 không vừa một mức 20% |
| `basket-priority` | b. Luật Y | Quy mô (support) quyết định doanh thu tăng thêm |

## Vì sao các phương án khác sai

- `tool-pm-selfserve`: GA4 mạnh ở nguồn traffic, khó funnel/cohort tuỳ biến theo user; notebook không phải
  self-serve; Segment là đường ống, không vẽ funnel.
- `tool-official-ltv`: Amplitude và GA4 không có hoàn tiền và chi phí của mọi kênh, và định nghĩa nằm trong cấu hình
  của công cụ; Excel tổng hợp tay không tái lập được. Product tool cho câu hỏi nhanh, warehouse cho số chính thức.
- `tool-campaign-traffic`: PostHog và RudderStack không phải chỗ mạnh cho attribution chiến dịch; RFM không trả lời
  câu hỏi về nguồn traffic.
- `tool-selfhost`: Mixpanel cloud và GA4 vẫn đưa dữ liệu ra ngoài dù ẩn IP; Sheets không phải công cụ thu sự kiện.
- `tool-cdp`: Metabase vẽ dữ liệu đã có; công cụ thứ hai chỉ thêm một nguồn lệch; dbt chuẩn hoá sau khi dữ liệu đã về
  warehouse, không sửa được SDK gửi sai tới Amplitude và nền tảng quảng cáo.
- `retention-wholesale`: bracket theo tháng làm khách đặt theo quý trông như rời đi rồi quay lại; N-day là của app
  dùng hằng ngày; revenue retention trả lời câu hỏi tiền, không phải "còn bao nhiêu khách".
- `retention-daily-app`: unbounded theo tháng che mất chuyện người dùng mở app thưa dần; revenue retention không hợp
  app chưa thu tiền theo ngày; MAU toàn app trộn người cũ với người mới, không so được hai bản onboarding.
- `funnel-unit`: theo visitor tính cả người mua ở lượt sau (không phải hiệu quả trong một lượt); theo sản phẩm trả lời
  "trang nào hỏng"; đếm đơn mỗi ngày không có mẫu số.
- `simple-ltv`: 120 là lợi nhuận gộp một năm (chưa chia 1 − r); 500 là chia cho 0.6 thay vì 0.4; 750 là doanh thu một
  năm chia 0.4 (quên biên).
- `payback`: k = 1 là 45, k = 2 là 60, chưa đủ 70. k = 4 là 80, đã quá. Lấy trung bình mỗi tháng rồi chia sẽ ra một
  con số không ứng với tháng nào.
- `rfm-quintile-f`: `pd.qcut` trên giá trị trùng lỗi hoặc phải xếp hạng `method="first"`, và khi đó khách giống hệt
  nhau rơi vào hai mức theo thứ tự dòng; vì thế module dùng ngưỡng nghiệp vụ cho F.
- `basket-priority`: Y xuất hiện trong 4.2% giỏ, gấp 14 lần X. Lift chỉ nói hai món hay đi cùng nhau tới đâu, không
  nói bao nhiêu doanh thu; support thấp là ít giỏ, không phải dư địa. Confidence không cần để so quy mô. Dù chọn luật
  nào, hiệu quả thật đo bằng A/B test.
