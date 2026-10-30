# Lời giải: chọn công cụ theo tình huống

## Cách làm

Mỗi câu trả lời bốn câu hỏi ở phần 6 lý thuyết:

1. Ai dùng kết quả và bao lâu một lần?
2. Dữ liệu ở đâu và lớn cỡ nào?
3. Có cần tái lập và review không?
4. Công ty đang dùng gì?

Phương án sai trong bài đều "chạy được"; chúng sai vì bỏ qua một trong bốn câu đó, hoặc vì giải quyết triệu
chứng thay cho vấn đề.

## Đáp án từng câu

| Câu | Đáp án | Câu hỏi quyết định |
| --- | --- | --- |
| `finance-scenarios` | b. Excel / Google Sheets | Người nhận tự sửa giả định, dữ liệu nhỏ, dùng một lần |
| `warehouse-mau` | c. SQL tổng hợp trên BigQuery | Dữ liệu ở đâu, lớn cỡ nào |
| `messy-monthly` | a. Python trong git | Lặp lại hằng tháng, cần review, làm sạch phức tạp |
| `store-managers` | d. Power BI có row-level security | Nhiều người, hằng ngày, phân quyền, hệ sinh thái Microsoft |
| `startup-selfserve` | b. Metabase tự host | Self-serve, không ngân sách, SQL database sẵn |
| `two-revenue-numbers` | c. dbt / semantic layer | Vấn đề là định nghĩa metric, không phải công cụ |
| `ops-allocation-tool` | a. Streamlit | Logic Python tuỳ biến, ít người dùng nội bộ, cần tương tác |
| `app-funnel` | b. Amplitude | Dữ liệu và chức năng đã có sẵn ở công cụ product analytics |
| `r-research-team` | d. R theo codebase | Công ty (nhóm) đang dùng gì, chi phí chuyển đổi |
| `laptop-csv` | c. DuckDB trên file | File cỡ vừa trên máy, ad-hoc, quen SQL |
| `llm-customer-data` | b. Chỉ gửi schema | Không gửi dữ liệu cá nhân ra dịch vụ ngoài |

### `finance-scenarios`: spreadsheet

Kế toán trưởng **tự sửa giả định** và thấy kết quả ngay, 150 dòng, dùng trong một buổi họp: đúng vùng mạnh
nhất của spreadsheet. Streamlit (a) và Power BI có tham số (c) làm được nhưng tốn công dựng và người nhận
không tự sửa công thức được. Notebook gửi ảnh (d) mất đúng thứ người dùng cần: tương tác với giả định.

### `warehouse-mau`: SQL ngay trên warehouse

2 tỉ dòng không thể kéo về máy (a) hay vào Excel (b, giới hạn khoảng 1 triệu dòng; lấy mẫu còn làm sai số
người dùng duy nhất). Tổng hợp ở warehouse rồi chỉ kéo về bảng nhỏ (quốc gia × tháng). Dashboard (d) là thừa
cho câu hỏi một lần.

### `messy-monthly`: Python trong git

Ba dấu hiệu: **lặp lại hằng tháng**, **làm sạch phức tạp** (encoding, cột đổi tên), **cần review**. Excel
copy-paste (b) là nguồn lỗi âm thầm kinh điển và không review được. Metabase (c) không làm sạch dữ liệu.
Chatbot (d) không tái lập được và có thể sai mà không ai biết.

### `store-managers`: Power BI có row-level security

40 người, mỗi sáng, tự lọc, **mỗi người chỉ thấy cửa hàng mình**, đã có license Microsoft 365. Row-level
security là tính năng có sẵn của BI doanh nghiệp. Email Excel (a) vỡ khi có 40 file mỗi ngày; Streamlit tự
viết đăng nhập (b) là tự làm lại phân quyền, rủi ro bảo mật; ảnh chart (c) không lọc được.

### `startup-selfserve`: Metabase tự host

Không ngân sách loại Tableau (a). Cấp quyền SQL cho PM (c) chỉ hợp khi họ biết SQL và vẫn để mỗi người tự định
nghĩa metric. DA trả số qua Slack (d) là đúng thứ cần thoát ra: DA thành nút cổ chai cho câu hỏi đơn giản.
Metabase có giao diện hỏi không cần SQL, miễn phí, nối thẳng Postgres.

### `two-revenue-numbers`: định nghĩa metric một chỗ

Hai con số lệch vì hai định nghĩa (có trừ đơn huỷ không, thuế, ngày ghi nhận). Chuyển cùng công cụ (a) không
sửa được: hai người vẫn viết hai SQL. Ghi chú "có thể lệch" (b) là bỏ cuộc. Chọn một bên (d) không giải thích
vì sao lệch và không ngăn lần sau. Định nghĩa doanh thu một lần (dbt model, semantic layer), mọi báo cáo đọc từ
đó, là sửa ở gốc. Module 09 làm việc này.

### `ops-allocation-tool`: Streamlit

Logic điều xe là code Python **có tham số**, người dùng **tải file lên** và xem kết quả tương tác, chỉ 6 người.
BI (b) hiển thị dữ liệu đã tổng hợp, không chạy logic tuỳ biến trên file người dùng tải lên. Excel macro (c)
phải viết lại logic bằng VBA. Gửi notebook (d) bắt người vận hành chạy code.

### `app-funnel`: Amplitude

Event đã nằm ở Amplitude và nó có sẵn funnel, retention, tách theo phiên bản app; PM tự dùng hằng ngày. Viết SQL
mỗi lần (a) biến DA thành nút cổ chai. Notebook (c) không tự phục vụ. Power BI trên export (d) là dựng lại thứ đã
có. DA vẫn cần SQL cho câu hỏi Amplitude không trả lời được (join với doanh thu, dữ liệu CRM).

### `r-research-team`: R theo codebase

Nhóm đã có pipeline R được kiểm duyệt. Viết lại sang Python (a) là chi phí lớn, rủi ro sai lệch kết quả đã duyệt,
không ai yêu cầu. Excel (b) tách bảng mới khỏi pipeline nên không tái lập. Tableau (c) không phải nhu cầu. "Công
ty đang dùng gì" là câu hỏi chọn công cụ có trọng lượng thật: track này chỉ giới thiệu R (module 04), nhưng đọc
và sửa được R là kỹ năng đáng có.

### `laptop-csv`: DuckDB

DuckDB chạy SQL thẳng trên file CSV/Parquet, không cần cài server, nhanh với vài trăm MB. Dựng Postgres (a) mất
thời gian nạp dữ liệu cho câu hỏi một buổi chiều. Excel (b) chậm và vượt giới hạn dòng với file 400 MB. Tải lên
warehouse (d) tốn thời gian, có thể vi phạm quy định dữ liệu, và vô ích cho việc một lần.

### `llm-customer-data`: chỉ gửi schema

Tên, email, số điện thoại là dữ liệu cá nhân; gửi chúng lên dịch vụ công cộng có thể vi phạm quy định bảo vệ dữ
liệu và chính sách công ty. LLM viết SQL chỉ cần **schema** (tên bảng, cột, kiểu, vài giá trị giả làm ví dụ). Xoá
cột tên (c) vẫn để lộ email, số điện thoại. Cấm hẳn (d) bỏ lỡ một công cụ có ích; điều cần là dùng an toàn và
**kiểm lại** câu SQL nó viết (module 15).
