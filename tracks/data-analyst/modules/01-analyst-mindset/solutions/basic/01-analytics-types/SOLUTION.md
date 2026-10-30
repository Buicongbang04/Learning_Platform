# Lời giải: phân loại câu hỏi vào bốn loại analytics

## Cách làm

Mỗi câu đi qua cùng một bước: bỏ tên công cụ và chi tiết kỹ thuật, viết lại câu hỏi thành một trong bốn
dạng.

| Dạng câu hỏi | Loại |
| --- | --- |
| Chuyện gì đã xảy ra? Bao nhiêu? Ở đâu? | Descriptive |
| Vì sao? Do đâu? Khác biệt đến từ đâu? | Diagnostic |
| Sẽ thế nào? Bao nhiêu trong tương lai? Ai có khả năng? | Predictive |
| Nên làm gì, với mục tiêu và ràng buộc nào? | Prescriptive |

Với câu Key Concepts, hỏi: việc đang làm thay đổi **dữ liệu** (cleanup), **hiểu dữ liệu** (exploration),
**trình bày** (visualisation) hay **định lượng độ chắc chắn** (statistical analysis)?

## Đáp án từng câu

| Câu | Đáp án | Viết lại thành |
| --- | --- | --- |
| `signups-by-channel` | a. Descriptive | Tháng trước đã có bao nhiêu đăng ký mỗi kênh? |
| `checkout-drop` | b. Diagnostic | Vì sao chuyển đổi giảm? |
| `warehouse-demand` | c. Predictive | Quý tới nhu cầu sẽ là bao nhiêu? |
| `warehouse-order-qty` | d. Prescriptive | Nên đặt bao nhiêu, tối ưu chi phí, trong sức chứa? |
| `churn-risk` | c. Predictive | Ai sẽ có khả năng ngừng mua? |
| `voucher-budget` | d. Prescriptive | Nên gửi cho ai, tối đa khách giữ được, trong ngân sách? |
| `region-split` | b. Diagnostic | Khác biệt đến từ đâu? |
| `delivery-dashboard` | a. Descriptive | Tuần này đã giao mất bao lâu ở mỗi tỉnh? |
| `ml-for-counting` | a. Descriptive | Năm ngoái mỗi tháng đã có bao nhiêu đơn huỷ? |
| `excel-forecast` | c. Predictive | Tháng 12 năm nay sẽ là bao nhiêu? |
| `missing-customer-id` | b. Cleanup | Xử lý dòng thiếu dữ liệu và ghi lại quyết định |
| `ab-noise` | c. Statistical analysis | Chênh lệch có vượt nhiễu ngẫu nhiên không? |

### `signups-by-channel` và `delivery-dashboard`: descriptive

Cả hai hỏi chuyện đã xảy ra, chia theo một chiều (kênh, tỉnh). Dashboard cập nhật mỗi sáng vẫn là
descriptive: "real-time" hay "mỗi ngày" là tần suất, không đổi loại câu hỏi. Diagnostic chỉ bắt đầu khi ai đó
hỏi "vì sao tỉnh X chậm hơn".

### `checkout-drop` và `region-split`: diagnostic

"Do đâu", "khác biệt đến từ giá, cơ cấu hay cửa hàng" là câu hỏi nguyên nhân. Cả hai cần một cây giả thuyết
(phần 4 lý thuyết): với checkout, nhánh dữ liệu (tracking hỏng?) kiểm trước, rồi phân khúc (thiết bị, phương
thức thanh toán), rồi thay đổi sản phẩm. `region-split` đã gợi sẵn ba nhánh (giá, mix, cửa hàng): đó là phân
rã, công cụ chính của diagnostic. Chọn descriptive ở câu này là dừng ở mô tả ("Bắc giảm, Nam tăng") trong
khi câu hỏi là vì sao.

### `warehouse-demand` và `warehouse-order-qty`: cặp predictive / prescriptive

Đây là cặp dễ nhầm nhất. "Quý tới sẽ cần bao nhiêu" là **dự báo**: một con số tương lai, kèm sai số. "Nên
đặt bao nhiêu để tổng chi phí thấp nhất, trong sức chứa" là **đề xuất**: có mục tiêu (chi phí thấp nhất) và
ràng buộc (sức chứa), và dùng dự báo làm đầu vào. Prescriptive thường đứng trên predictive: không biết nhu cầu
thì không tối ưu được lượng đặt hàng.

### `churn-risk` và `voucher-budget`: lại một cặp

"Ai có khả năng ngừng mua" là predictive (xác suất cho từng khách). "Gửi voucher cho ai với 50 triệu" là
prescriptive: cần thêm **tác động** của voucher lên từng nhóm (khách chắc chắn ở lại hoặc chắc chắn đi thì
voucher không đổi gì) và ràng buộc ngân sách. Một lỗi hay gặp là gửi voucher cho nhóm có rủi ro churn cao
nhất: đó là dùng dự báo như thể nó là đề xuất.

### `ml-for-counting`: descriptive, dù dùng machine learning

Dữ liệu đã có đủ trạng thái huỷ; câu hỏi là đếm theo tháng, một phép `groupby`. Dùng model ở đây không biến
câu hỏi thành predictive; nó chỉ làm câu trả lời kém chính xác hơn (model ước lượng thứ có thể đếm thẳng). Loại
analytics do câu hỏi quyết định; chọn công cụ "mạnh" cho câu hỏi đơn giản là lỗi phân tích quá mức.

### `excel-forecast`: predictive, dù làm trong Excel

Ngược lại với câu trên: một phép nhân trong Excel vẫn là dự báo, vì nó trả lời "sẽ là bao nhiêu". Phương pháp
đơn giản không làm câu hỏi đơn giản đi: vẫn phải báo giả định (tăng trưởng giữ nguyên) và kiểm lại sai số.
Trên Bike Sharing, đúng cách này dự báo tháng 12/2012 cao hơn thực tế 17.6% (phần 3 lý thuyết).

### `missing-customer-id`: cleanup

Đếm dòng thiếu, quyết định giữ cho doanh thu nhưng loại khỏi số khách, là xử lý missing data, việc của bước
cleanup. Exploration (c) là gần nhất: phát hiện tỉ lệ thiếu là một quan sát khám phá, nhưng **quyết định xử lý
và ghi lại** là cleanup. Collection (a) là lấy dữ liệu từ nguồn; visualisation (d) không liên quan.

### `ab-noise`: statistical analysis

Hỏi một chênh lệch có vượt nhiễu không là kiểm định giả thuyết, thuộc statistical analysis (module 11).
Exploration chỉ thấy chênh lệch; machine learning không cần cho câu hỏi này; visualisation có thể vẽ khoảng tin
cậy nhưng việc tính nó là thống kê.

## Sai lầm hay gặp

- Xếp loại theo công cụ ("có model nên là predictive", "làm Excel nên là descriptive").
- Gộp predictive và prescriptive: một danh sách khách rủi ro cao chưa phải là quyết định nên làm gì.
- Coi dashboard là "nâng cao" hơn một bảng: tần suất cập nhật không đổi loại câu hỏi.
