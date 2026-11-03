# Tự dựng hay dịch vụ cloud ML

## 1. Bối cảnh và giả định

Startup logistics có 4 người ML, 2 model đang chạy và dự kiến 10 model trong 12 tháng. Dữ liệu đã nằm trên một cloud lớn; một kỹ sư nền tảng dành khoảng 50% thời gian cho ML. Tải đỉnh 30 request/giây với p95 dưới 200 ms, không có yêu cầu pháp lý đặc biệt nhưng khách doanh nghiệp hỏi về nơi lưu dữ liệu. Giả định giá: giờ kỹ sư nền tảng 75 USD; tự dựng gồm MLflow, orchestrator và serving trên Kubernetes đã có; cloud là dịch vụ ML quản lý của chính cloud đang chứa dữ liệu, có endpoint tính theo giờ; lai là MLflow tự host cộng serving trên dịch vụ quản lý. Mọi con số là ước tính để so sánh, kiểm lại với bảng giá hiện hành trước khi cam kết.

## 2. Ma trận tiêu chí

| Tiêu chí | Trọng số | Tự dựng | Cloud | Lai |
| --- | --- | --- | --- | --- |
| Chi phí 24 tháng | 20 | 4 | 2 | 3 |
| Công sức vận hành | 20 | 2 | 5 | 3 |
| Tốc độ ra production | 15 | 2 | 5 | 3 |
| Khả năng tuỳ biến | 10 | 5 | 3 | 4 |
| Tuân thủ và nơi lưu dữ liệu | 10 | 4 | 4 | 4 |
| Lock-in và khả năng rời | 10 | 5 | 2 | 4 |
| Mở rộng tới 10 model | 15 | 3 | 4 | 4 |
| Tổng có trọng số | 100 | 3.35 | 3.65 | 3.45 |

## 3. Chi phí 24 tháng

| Hạng mục | Tự dựng | Cloud | Lai |
| --- | --- | --- | --- |
| Chi phí một lần | 18000 | 6000 | 12000 |
| Chi phí mỗi tháng | 1900 | 3100 | 2400 |
| Tổng 24 tháng | 63600 | 80400 | 69600 |

Điểm hoà vốn: tháng 10, từ đó Tự dựng rẻ hơn Cloud ((18000 - 6000) / (3100 - 1900) = 10). Chi phí mỗi tháng của Tự dựng gồm khoảng 700 USD hạ tầng và 16 giờ vận hành (1200 USD); của Cloud chủ yếu là endpoint chạy liên tục. Chi phí một lần của Cloud nhỏ vì dữ liệu đã nằm cùng cloud, còn Tự dựng mất khoảng hai tháng của kỹ sư nền tảng.

## 4. Khuyến nghị

**Khuyến nghị:** Cloud

Điểm cao nhất (3.65) và là phương án duy nhất khớp với việc chỉ có 0.5 kỹ sư nền tảng khi số model tăng từ 2 lên 10. Chênh lệch chi phí 24 tháng là khoảng 16800 USD, thấp hơn giá trị của 4 tháng đến sớm hơn thị trường và của khối lượng vận hành không phải làm. Nên bắt đầu bằng Cloud, giữ model và pipeline ở định dạng mở (artifact MLflow, container chuẩn) để đường rút lui rẻ.

## 5. Điều kiện đổi hướng

- Số model production vượt 12 hoặc hoá đơn endpoint vượt 4500 USD mỗi tháng trong 2 tháng liên tiếp: đánh giá lại chuyển sang Lai hoặc Tự dựng, vì điểm hoà vốn đã đến gần.
- Nếu độ trễ p95 trên dịch vụ quản lý vượt 200 ms trong 3 tuần liên tiếp dù đã thử cấu hình: chuyển phần serving sang Tự dựng, giữ phần train.
- Nếu tuyển được thêm 1 kỹ sư nền tảng toàn thời gian: chạy lại ma trận, vì trọng số "công sức vận hành" giảm.
- Nếu một khách doanh nghiệp yêu cầu dữ liệu ở vùng mà dịch vụ chưa có trong 6 tháng tới: Lai hoặc Tự dựng ở vùng đó.

## 6. Rủi ro

- Lock-in: pipeline viết theo SDK riêng của dịch vụ cloud tốn khoảng một tháng để chuyển đi; giảm bằng cách giữ artifact và serving container theo chuẩn mở và đo chi phí rời ngay từ bây giờ.
- Chi phí endpoint nhàn rỗi tăng âm thầm khi số model tăng; cần budget alarm, tag chủ sở hữu và rà soát endpoint mỗi tuần (alarm chỉ báo, không dừng chi tiêu).
- Ước tính vận hành 16 giờ mỗi tháng của Tự dựng thường thấp hơn thực tế khi có sự cố; so sánh nên đưa vào độ nhạy (nếu 32 giờ thì điểm hoà vốn dịch sang tháng nào).
