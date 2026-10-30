# Lời giải: chọn công cụ BI và cách định nghĩa metric

## Cách làm

Mỗi câu chọn công cụ đi qua bốn câu hỏi của phần 7 lý thuyết: **ai dùng** (biết SQL không, bao nhiêu người, cần
RLS không), **dữ liệu ở đâu**, **hệ sinh thái công ty**, **ai duy trì và ngân sách**. Thường có một chữ trong tình
huống quyết định đáp án ("mỗi người chỉ thấy chi nhánh mình", "không có ngân sách", "gọi model Python"). Câu khái
niệm hỏi **logic tính toán nằm ở đâu** trong từng công cụ.

## Đáp án từng câu

| Câu | Đáp án | Tiêu chí quyết định |
| --- | --- | --- |
| `bank-branch-managers` | b. Power BI + RLS | Hệ Microsoft, 300 người xem, phân quyền theo dòng |
| `startup-selfserve` | d. Metabase tự host, model chuẩn | Không license, người dùng không viết SQL |
| `sql-team-rls` | a. Apache Superset | Người dùng biết SQL, nhiều loại chart, RLS miễn phí, có DE vận hành |
| `what-if-inventory` | c. Streamlit gọi model | Logic tuỳ biến (model Python), ít người dùng |
| `governed-active-user` | b. Semantic layer trong git (LookML) | Vấn đề là định nghĩa metric, không phải hình vẽ |
| `ga4-free-share` | a. Looker Studio | Nguồn Google, miễn phí, chia sẻ ra ngoài |
| `share-as-measure` | d. Measure `DIVIDE(SUM(casual), SUM(cnt))` | Tỉ lệ tính sau khi lọc |
| `tableau-first-purchase` | b. `{FIXED [Customer ID] : MIN([Order Date])}` | Tính ở mức chi tiết riêng, không theo view |
| `one-off-why` | c. Ad-hoc SQL + memo | Câu "vì sao", hỏi một lần |
| `metabase-drill` | a. Query builder trên model | Drill-through chỉ có trên question query builder |
| `looker-vs-studio` | d. Looker có LookML trong git | Hai sản phẩm khác nhau |

### `bank-branch-managers`: Power BI với row-level security

Ba tín hiệu cùng chỉ về Power BI: công ty đã có Microsoft 365/Azure (license thường đã gồm hoặc rẻ), 300 người
xem hằng ngày cần một data model chung, và mỗi giám đốc **chỉ thấy chi nhánh mình**, tức RLS định nghĩa bằng role
DAX trên bảng dimension chi nhánh. (a) Metabase bản mã nguồn mở không có sandboxing; 300 dashboard riêng thì
không duy trì nổi và một lỗi chia sẻ là lộ số chi nhánh khác. (c) Tự kiểm tên đăng nhập trong code Streamlit là
tự viết hệ phân quyền cho dữ liệu ngân hàng. (d) Chia sẻ link Looker Studio không phải phân quyền theo dòng.

### `startup-selfserve`: Metabase tự host, model chuẩn cho marketing

Không ngân sách loại (a) Tableau Cloud. Marketing **không viết SQL** nên (c) Superset kèm SQL Lab sai người dùng;
Superset vẫn có giao diện kéo thả nhưng khó hơn Metabase với người business. (b) file HTML mỗi tuần không cho họ
tự cắt lát theo kênh, theo tuần. Metabase có query builder dễ nhất; điều kiện để self-serve an toàn là DA dựng
**model** chuẩn (đã bỏ đơn huỷ, metric định nghĩa sẵn) để marketing bắt đầu từ đó, không từ bảng thô.

### `sql-team-rls`: Apache Superset

Analyst đều viết SQL (SQL Lab), cần heatmap, sankey (thư viện chart ECharts của Superset rộng hơn Metabase), cần
RLS cho đối tác (Superset có Row Level Security trong bản mã nguồn mở), không muốn trả license, và **có DE vận
hành server** (Superset cần Celery, cache, nâng cấp). (b) Metabase bản mở thiếu RLS và ít loại chart. (c) Looker
Studio không có RLS đúng nghĩa và không hợp dữ liệu nội bộ trên Postgres. (d) Excel qua OneDrive không phải BI.

### `what-if-inventory`: Streamlit gọi model, có test cho logic

"Kéo thanh trượt, xem ngay dự báo từ **model Python**" là logic BI không chạy được: BI gửi SQL tới database, không
gọi model. Ba người dùng nội bộ nên thiếu self-serve và RLS không thành vấn đề. (a) Biến số trong SQL Metabase chỉ
lọc, không chạy model. (b) Parameter what-if của Power BI làm được phép tính DAX đơn giản (giá × số lượng), không
gọi model Python của team DS (và công ty chưa chắc có Power BI). (d) Jinja trong Superset chỉ sinh SQL.

### `governed-active-user`: semantic layer quản trị bằng git (LookML)

Ba định nghĩa "active user" là vấn đề **định nghĩa metric**, không phải vấn đề hình vẽ. Cần một chỗ định nghĩa
duy nhất, review như code, mọi dashboard dùng chung: LookML trên BigQuery là ví dụ điển hình (dbt metrics, Cube
cũng là semantic layer). (a) Đồng bộ màu không thống nhất con số. (c) Dashboard tổng hợp ba định nghĩa hợp thức
hoá sự lộn xộn. (d) DA tự tính lại mọi số thì thành nút cổ chai và vẫn không có định nghĩa chung.

### `ga4-free-share`: Looker Studio

Nguồn là GA4 và Google Sheet (connector có sẵn), team dùng Google Workspace, **miễn phí**, chia sẻ cho agency như
chia sẻ Google Docs. (b) Looker (LookML) đắt và quá nặng cho 5 người. (c) Power BI Premium tốn tiền và lệch hệ
sinh thái. (d) Superset tự host cần người vận hành và không có connector GA4 sẵn.

### `share-as-measure`: measure `DIVIDE(SUM(casual), SUM(cnt))`

Tỉ lệ phải tính **sau** khi lọc, trong filter context của từng ô: đó là measure. (a) Calculated column rồi lấy
Average là "trung bình của tỉ lệ": mỗi ngày nặng như nhau dù ít hay đông khách. Trên Bike Sharing cách này cho
17.6% thay vì 18.8% (phần 2 lý thuyết). (b) Cộng tỉ lệ từng ngày thì vô nghĩa (ra số lớn hơn 1). (c) Tính sẵn trong
Excel đóng băng tỉ lệ ở một mức chi tiết, lọc theo mùa hay loại ngày sẽ sai.

### `tableau-first-purchase`: `{FIXED [Customer ID] : MIN([Order Date])}`

LOD `FIXED` tính ở mức chi tiết bạn chỉ định (mỗi khách), không phụ thuộc dimension của view (tháng). Đó chính
là "tháng mua đầu" để dựng cohort. (a) Table calculation chạy trên bảng kết quả đã tổng hợp theo tháng của view,
không biết từng khách. (c) Top N chọn khách, không tính ngày. (d) Bộ lọc Minimum trên Order Date lọc cả view về
một ngày, không cho mỗi khách một ngày.

### `one-off-why`: phân tích ad-hoc bằng SQL, trả lời bằng memo

Câu "vì sao" hỏi **một lần** cần kiểm giả thuyết (sản phẩm nào, khách nào, giá hay lượng, kỳ có đủ ngày không),
kết thúc bằng kết luận, không phải bằng hình để tự xem. (a) Dashboard 12 card cho một câu hỏi một lần là lãng phí
và CEO vẫn phải tự suy ra "vì sao". (b) Self-serve trên bảng thô cho CEO là rủi ro định nghĩa. (d) Thêm bộ lọc
Germany vào mọi dashboard không trả lời câu hỏi.

### `metabase-drill`: query builder trên model

Metabase biết ngữ nghĩa từng cột của question dựng bằng query builder, nên có drill-through (click cột → xem chi
tiết, nhóm theo chiều khác). (b) Question native SQL không có drill-through dù có bao nhiêu biến. (c) Alias không
liên quan tới drill-through, và làm **field filter** hỏng (field filter tham chiếu tên bảng đầy đủ). (d) Ảnh chụp
thì không tương tác.

### `looker-vs-studio`: Looker có semantic layer LookML trong git

Looker (Google Cloud) là nền tảng BI có LookML: view, measure, explore, review bằng pull request. Looker Studio
(trước là Data Studio) là công cụ dashboard kéo thả miễn phí, không có LookML. (a) sai: cả hai chạy trên trình
duyệt. (b) sai: Looker nối BigQuery rất tốt. (c) sai: hai sản phẩm khác nhau, không chỉ khác giá. Trong phỏng vấn,
nói rõ mình đã dùng sản phẩm nào.
