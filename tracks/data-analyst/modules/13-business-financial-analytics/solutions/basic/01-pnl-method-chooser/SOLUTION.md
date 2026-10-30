# Lời giải: đọc P&L và chọn phương pháp, công cụ

## P&L thu nhỏ (ví dụ giả định)

| Dòng | Nghìn GBP | % doanh thu thuần |
| --- | --- | --- |
| Doanh thu gộp | 1 000 | |
| Hàng trả lại và huỷ | −50 | |
| **Doanh thu thuần** | **950** | 100% |
| Giá vốn | −570 | |
| **Gross profit** | **380** | **40.0%** |
| Giao hàng, phí thanh toán (biến đổi) | −79 | |
| **Contribution** | **301** | **31.7%** |
| Marketing | −120 | |
| Lương văn phòng, thuê kho (cố định) | −100 | |
| **Operating profit** | **81** | **8.5%** |

## Đáp án từng câu

| Câu | Đáp án | Lý do ngắn |
| --- | --- | --- |
| `gross-margin` | b. 40.0% | 380 / 950 |
| `contribution-lines` | c. Giao hàng và phí thanh toán | Chi phí biến đổi theo đơn / theo tiền |
| `operating-margin` | d. 8.5% | 81 / 950 |
| `markup-margin` | a. Khoảng 33% | 50 / 150 |
| `price-breakeven` | c. Khoảng 11.1% | 0.05 / (0.40 + 0.05) |
| `why-revenue-up` | a. PVM bridge | Giải thích thay đổi đã xảy ra |
| `mix-rate` | b. Hiệu ứng mix | Simpson: tỉ trọng nhóm đổi |
| `forecast-method` | d. Seasonal naive + backtest | Baseline trước, phức tạp sau |
| `whatif-tool` | a. Spreadsheet có ô giả định | Người dùng tự đổi số, ngay trong họp |
| `alert-method` | c. Median cùng thứ + ngưỡng robust | Trừ mùa vụ tuần và năm |
| `alert-tool` | b. Truy vấn lên lịch có runbook | Tự động, nhiều KPI, có người chịu trách nhiệm |
| `promo-eval` | d. So cùng thứ, kéo cầu, đối chứng | Lift quan sát không phải tác động tăng thêm |

### P&L

- `gross-margin` **b**: margin chia cho doanh thu thuần 950, không phải doanh thu gộp. 38.0% (a) là 380 / 1 000, lỗi
  hay gặp nhất; 43.0% (c) là quên trừ hàng trả lại khỏi doanh thu ((1 000 − 570) / 1 000); 31.7% (d) là contribution
  margin.
- `contribution-lines` **c**: contribution = doanh thu trừ mọi chi phí **biến đổi** (đi theo đơn, theo số lượng,
  theo tiền thu). Giao hàng tính theo đơn, phí thanh toán theo tiền thu. Marketing (a) thường xếp riêng vì không tỉ lệ
  với từng đơn; lương, thuê kho là cố định; giá vốn đã trừ ở gross profit.
- `operating-margin` **d**: 301 − 120 − 100 = 81, chia 950. 8.1% là chia cho doanh thu gộp; 21.1% là quên trừ
  marketing ((301 − 100) / 950).
- `markup-margin` **a**: giá vốn 100 thì giá bán 150, margin = 50 / 150 = 33.3%. Nhầm markup với margin là nguồn lệch
  số hay gặp giữa phòng mua hàng và tài chính.
- `price-breakeven` **c**: mỗi đơn vị lời thêm 5 (trên giá 100) ngoài 40 hiện tại; số lượng mới q' thoả
  45q' = 40q nên q' = 0.889q, giảm 11.1%. Công thức −p / (m + p). 12.5% là 0.05 / 0.40 (quên cộng p ở mẫu); 4.5%
  là 0.05 × (1 − 0.1) không có cơ sở. Bài Basic 02 làm phép tính này trên dữ liệu thật.

### Phương pháp và công cụ

- `why-revenue-up` **a**: câu hỏi chẩn đoán (diagnostic) về thay đổi đã xảy ra, tách thành giá, lượng, mix: đúng là
  PVM bridge. Dự báo (b) trả lời "sẽ bao nhiêu"; hồi quy theo nhiệt độ (c) không tách giá và mix; cảnh báo (d) là
  giám sát.
- `mix-rate` **b**: trung bình toàn chuỗi = tổng (tỉ trọng nhóm × trung bình nhóm). Mọi nhóm tăng (rate dương)
  nhưng tỉ trọng dồn về nhóm có trung bình thấp (mix âm) thì tổng vẫn giảm: Simpson's paradox. Phân rã mix và rate
  (README phần 2) cho ra hai con số này. Dữ liệu không sai (a).
- `forecast-method` **d**: bắt đầu bằng baseline đơn giản (cùng tuần năm trước) và backtest nhiều điểm cắt, rồi mới
  thử phương pháp phức tạp hơn nếu thắng được baseline. Trung bình 4 tuần (b) bỏ mùa vụ; (a) nhảy thẳng vào model
  không có thước đo; (c) không phải dự báo.
- `whatif-tool` **a**: người ra quyết định cần tự đổi giả định và thấy kết quả ngay: spreadsheet với ô giả định tách
  riêng, công thức tham chiếu ô, bảng kịch bản (Data Table, Scenario Manager, Goal Seek). Notebook (b) không dành cho
  CFO; BI (c) hiện thực tế, không giả lập; ảnh (d) không đổi được.
- `alert-method` **c**: baseline cùng thứ các tuần trước trừ mùa vụ tuần, so tỉ lệ và ngưỡng robust (MAD) chịu được
  ngoại lệ (bài Basic 03). Ngưỡng cố định (a) báo cả mùa thấp điểm; so với hôm qua (b) bỏ qua chu kỳ tuần.
- `alert-tool` **b**: 20 KPI, hằng ngày, nhiều team: cần truy vấn lên lịch trên warehouse (alert của Metabase,
  Superset, Looker, hoặc job SQL trong orchestrator) gửi vào kênh chat, kèm runbook ai xử lý gì. Notebook chạy tay
  (a) phụ thuộc một người; email cuối tuần (c) quá chậm; tự mở dashboard (d) không phải cảnh báo.
- `promo-eval` **d**: chênh lệch giữa ngày có và không có khuyến mãi là quan sát, chưa phải tác động tăng thêm: phải
  so cùng thứ và điều kiện, xét khách mua trữ (kéo cầu từ ngày khác), và đo bằng nhóm đối chứng nếu có thể. Doanh thu
  tăng không có nghĩa lợi nhuận tăng (b) vì còn tiền giảm giá (bài Advanced 02).
