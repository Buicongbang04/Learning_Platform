# Câu hỏi phỏng vấn: Data modeling cho analytics

## Grain của một bảng là gì? Vì sao DA phải hỏi grain trước khi viết truy vấn?

Grain là câu trả lời cho "một dòng của bảng này là gì", viết thành một câu có danh từ cụ thể: "một dòng = một
mặt hàng trên một hoá đơn bán hợp lệ", "một dòng = một khách × một tháng". Mọi phép tổng hợp đúng hay sai theo
câu đó:

- `SUM(revenue)` chỉ đúng nếu mỗi dòng là một phần doanh thu không trùng.
- `AVG` cho ra trung bình **theo grain của bảng**: trên bảng dòng hàng của Online Retail II, trung bình
  doanh thu mỗi dòng là 20.12 GBP, còn giá trị đơn trung bình (AOV) là 534.40 GBP.
- Join chỉ an toàn khi khoá bên kia là duy nhất ở grain của nó.

Ứng viên tốt nói thêm: grain khai báo là giả thuyết, phải kiểm bằng truy vấn đếm khoá. Trên Online Retail II,
nhiều người đoán khoá là `(Invoice, StockCode)`, nhưng 9 566 cặp lặp lại vì cùng mặt hàng được ghi nhiều dòng
trên một hoá đơn; khoá duy nhất đáng tin là số thứ tự dòng của hệ thống nguồn.

## Phân biệt fact và dimension. Cho ví dụ một cột khó xếp.

**Fact** ghi nhận sự kiện đo được (dòng bán, lượt xem, giao dịch thanh toán), chứa **measure** số và khoá
ngoại; thường dài và chỉ thêm dòng. **Dimension** mô tả ngữ cảnh (sản phẩm, khách, ngày, cửa hàng), chứa
thuộc tính dạng chữ để lọc và nhóm; ngắn hơn, thay đổi chậm.

Cột khó xếp hay gặp:

| Cột | Xếp vào | Vì sao |
| --- | --- | --- |
| Đơn giá | Fact | 3 366 / 3 922 mã hàng của Online Retail II có nhiều mức giá trong năm; đặt ở dimension là chọn bừa một giá |
| Mã hoá đơn | Fact (degenerate dimension) | Là ngữ cảnh nhưng không có thuộc tính riêng nào đáng một bảng |
| Quốc gia giao hàng | Fact hoặc dimension riêng | Thuộc từng đơn, không thuộc khách (khách vãng lai vẫn có quốc gia) |
| Giá niêm yết hiện tại | Dimension sản phẩm | Thuộc tính mô tả, không phải số đo của giao dịch |
| Tồn kho cuối ngày | Fact snapshot (semi-additive) | Là số đo, nhưng không cộng theo thời gian |

## Additive, semi-additive và non-additive measure khác nhau thế nào? Vì sao DA phải quan tâm?

- **Additive**: cộng đúng theo mọi chiều (`revenue`, `quantity`).
- **Semi-additive**: cộng theo một số chiều nhưng không theo thời gian (số dư, tồn kho: cộng các cửa hàng được,
  cộng các ngày thì vô nghĩa; lấy giá trị cuối kỳ).
- **Non-additive**: không cộng được (tỉ lệ, trung bình, `count distinct`, median).

DA quan tâm vì BI tool mặc định `SUM` khi kéo cột vào. Trên Online Retail II, cộng số khách hoạt động của 13
tháng ra 13 054, gấp ba số khách thật của năm (4 338); lấy trung bình 13 AOV tháng ra 541.11 trong khi AOV cả
năm là 534.40 GBP. Cách đúng: lưu tử số và mẫu số (doanh thu, số đơn) rồi chia sau khi tổng hợp; với
`count distinct` thì tính lại ở grain được hỏi.

## Fan-out là gì? Bạn phát hiện và sửa nó thế nào?

Fan-out xảy ra khi join với một bảng mà khoá join **không duy nhất** ở bên kia: mỗi dòng bên trái nhân lên
theo số dòng khớp, và mọi `SUM` sau đó bị đếm thừa. Hai dạng hay gặp:

1. **Dimension không unique**: `dim_product` dựng bằng `SELECT DISTINCT StockCode, Description` trên Online
   Retail II có 4 161 dòng cho 3 922 mã (220 mã có nhiều mô tả). Join theo `StockCode` làm doanh thu phình 12.3%.
2. **Join hai bảng khác grain**: gắn tổng hoá đơn vào từng dòng hàng rồi `SUM` tổng hoá đơn, kết quả gấp 68 lần
   vì hoá đơn trung bình có 26.6 dòng.

Phát hiện: đếm dòng và tổng measure trước và sau join (phải bằng nhau với join many-to-one); test `unique` trên
khoá dimension. Sửa: dedupe dimension về một dòng mỗi khoá theo quy tắc ghi rõ, hoặc tổng hợp từng bảng về
cùng grain trước rồi mới join.

## Khi nào dùng SCD type 1, khi nào type 2? Cho ví dụ quyết định thật.

- **Type 1** (ghi đè): khi lịch sử không có ý nghĩa nghiệp vụ hoặc chỉ là sửa lỗi (lỗi chính tả tên sản phẩm),
  hoặc khi câu hỏi là "hiện tại" (khách đang ở đâu để gửi thư).
- **Type 2** (thêm phiên bản có `valid_from`, `valid_to`): khi báo cáo phải phản ánh thuộc tính **tại thời
  điểm giao dịch**, như doanh thu theo vùng của nhân viên bán hàng trước và sau khi chuyển vùng, để số quý
  trước không đổi khi xem lại.

Ví dụ trên Online Retail II: 8 khách có hoá đơn ở hai quốc gia. Nếu quốc gia chỉ nằm ở `dim_customer` type 1,
toàn bộ lịch sử của 8 khách "chuyển nước" khi họ đổi. Với bộ này quốc gia là thuộc tính của từng hoá đơn (khách
vãng lai cũng có), nên tôi đặt `country` ở fact và giữ `current_country` type 1 ở dimension cho nhu cầu CRM.
Điểm then chốt: chọn SCD theo câu hỏi business, không theo thói quen "cái gì cũng type 2".

## Unknown member là gì? Nếu không có nó thì chuyện gì xảy ra?

Unknown member là một dòng đặc biệt trong dimension (thường `key = 0` hoặc `-1`, tên "Không xác định" hoặc
"Khách vãng lai") để mọi dòng fact thiếu khoá vẫn có chỗ trỏ tới. Không có nó, có hai kết cục xấu:

- Khoá ngoại để `NULL`, và mọi dashboard dùng inner join âm thầm mất các dòng đó. Trên Online Retail II là 16.5%
  doanh thu (1 755 277 GBP của khách không có mã).
- Người viết pipeline xoá dòng thiếu khoá cho "sạch", làm lệch tổng với số Finance.

Có unknown member, tổng theo khách luôn bằng tổng fact, và nhóm "khách vãng lai" hiện ra như một dòng để người
đọc thấy và hỏi.

## Star schema hay bảng phẳng (one big table)? Bạn chọn thế nào?

| | Star schema | Bảng phẳng rộng (OBT) |
| --- | --- | --- |
| Người dùng | Analyst viết SQL, BI tool có semantic model | Người dùng kéo thả, notebook, ML feature |
| Ưu | Mỗi thuộc tính một chỗ; đổi tên sản phẩm sửa một dòng; dimension dùng chung nhiều fact | Không cần join, nhanh trên warehouse dạng cột, dễ hiểu |
| Nhược | Phải join; người dùng có thể join sai | Lặp thuộc tính; đổi định nghĩa phải build lại cả bảng; dễ trộn grain |

Thực tế thường làm cả hai: star schema là tầng lõi có test (fact, dimension), và vài bảng rộng hoặc mart tổng
hợp dựng **từ** star cho từng nhóm người dùng. Điều không thương lượng là bảng nào cũng có grain khai báo và
khoá được test.

## dbt giải quyết vấn đề gì cho một team DA? Bạn tổ chức project thế nào?

Vấn đề: cùng một logic ("bỏ hoá đơn C...") được chép vào hàng chục truy vấn của dashboard; mỗi nơi sửa một kiểu,
không ai biết bảng nào phụ thuộc bảng nào, và lỗi chỉ được phát hiện khi CEO hỏi. dbt biến các `SELECT` thành
model có tên, phụ thuộc rõ (`ref()`), chạy theo đúng thứ tự, kèm test, tài liệu, lineage và quy trình review
bằng git.

Tổ chức theo ba tầng: `staging` (một model mỗi bảng nguồn: đổi tên, ép kiểu, gắn cờ; không lọc, không join),
`intermediate` (bước dùng lại), `marts` (fact, dimension, mart cho người dùng). Đặt tên `stg_`, `int_`, `fct_`,
`dim_`, `mart_`; staging là view, marts là table; mọi model mart có mô tả grain và test khoá.

## Bạn viết những data test nào cho một mart doanh thu tháng?

Tối thiểu năm loại, theo thứ tự giá trị:

1. **Khoá của grain**: `unique` + `not_null` trên `month`.
2. **Đối soát**: singular test so tổng doanh thu và số đơn của mart với fact (và nếu có, với con số Finance
   chốt sổ); lệch quá ngưỡng là `error`.
3. **Toàn vẹn tham chiếu** ở tầng dưới: `relationships` từ fact tới dimension.
4. **Độ phủ kỳ**: cờ hoặc test cho tháng chưa đủ ngày (Online Retail II dừng ở 09/12/2011 12:50), để dashboard
   không so MoM tháng 12 với tháng 11.
5. **Khoảng hợp lý** (`warn`): doanh thu tháng không âm, AOV trong khoảng lịch sử; cảnh báo chứ không chặn.

Câu trả lời senior nói thêm về `severity`: test chặn build chỉ dành cho lỗi làm số sai; test cảnh báo có ngưỡng
để một ngày bất thường không làm cả công ty mất dashboard.

## Semantic layer / metric layer là gì? Khi nào một công ty cần nó?

Metric layer là nơi định nghĩa mỗi metric **một lần** (biểu thức, phép tổng hợp, bộ lọc, dimension được phép,
owner) để mọi công cụ hỏi metric theo tên thay vì tự viết SQL. Ví dụ: dbt Semantic Layer (MetricFlow), LookML,
semantic model của Power BI, Cube, model/metric của Metabase.

Dấu hiệu cần nó: hai dashboard ra hai số cho cùng tên metric; câu hỏi "số này tính thế nào" mất nửa ngày để trả
lời; nhiều công cụ (BI, notebook, app) cùng tiêu thụ một metric. Công ty nhỏ có thể bắt đầu bằng một tệp YAML
có review và một hàm đọc nó, hoặc một mart có cột đã định nghĩa; công cụ chuyên dụng chỉ đáng khi số người và
số công cụ tiêu thụ metric tăng.

## Case: CFO thấy doanh thu tháng 11 trên dashboard Finance là 1.46 triệu, trên dashboard Marketing là 1.16 triệu GBP. Bạn xử lý thế nào?

1. **Không chọn phe ngay.** Lấy SQL (hoặc định nghĩa) của cả hai, đối chiếu từng bước: bảng nguồn, bộ lọc, cột
   ngày, cách xử lý đơn huỷ, khách vãng lai.
2. Trên Online Retail II, hai con số tách được: Finance cộng **mọi dòng kể cả hoá đơn huỷ** (số âm) ra
   1 461 756.25; Marketing lọc dòng hợp lệ nhưng chỉ lấy khách có `Customer ID`, ra 1 161 817.38. Định nghĩa chung (dòng hợp lệ, doanh
   thu gộp) ra 1 509 496.33. Viết bảng cầu nối: gộp 1 509 496 − hoá đơn huỷ 47 740 = 1 461 756 (Finance); gộp
   − khách vãng lai 347 679 = 1 161 817 (Marketing).
3. **Đề xuất một định nghĩa có tên cho từng nhu cầu**: "doanh thu gộp" (vận hành, theo ngày đặt), "doanh thu
   ròng" (Finance, trừ huỷ), "doanh thu từ khách định danh" (CRM). Mỗi cái có owner và mô tả trong metric layer;
   dashboard ghi rõ đang hiện cái nào.
4. Sửa nguồn: kéo logic xuống model chung (mart/semantic layer), thêm test đối soát, và báo lại CFO bằng một
   đoạn ngắn: vì sao lệch, con số nào dùng cho quyết định nào, từ ngày nào dashboard thống nhất.

## Case: Marketing muốn "một bảng để làm mọi phân tích khách hàng". Bạn thiết kế mart thế nào?

Không bắt đầu bằng cột; bắt đầu bằng **câu hỏi**. Hỏi lại ba đến năm quyết định họ sẽ đưa ra: chọn khách cho
email win-back, đo retention theo cohort, so giá trị khách theo kênh/quốc gia. Mỗi câu hỏi quyết định một grain:

| Câu hỏi | Grain phù hợp |
| --- | --- |
| Khách nào đang "ngủ" để gửi win-back | Một dòng mỗi khách tại một ngày chốt (snapshot) |
| Retention theo cohort | Một dòng mỗi khách × tháng hoạt động |
| Giá trị khách theo quốc gia | Tổng hợp từ bảng khách, không phải bảng riêng |

Thường ra hai bảng: `mart_customer` (khách, chốt ở một ngày) và `mart_customer_month`. Mỗi cột có định nghĩa
(recency tính tới ngày chốt nào, đơn có tính đơn huỷ không, khách vãng lai ở đâu), test (unique khách, tổng
doanh thu khớp fact) và lưu ý (dữ liệu bắt đầu từ đâu, nên "khách mới" ở tháng đầu bị thổi phồng). Từ chối
"một bảng cho mọi thứ" vì nó trộn grain, và một cột sai làm sai mọi phân tích dùng nó.

## Case: Sau khi nạp dữ liệu mới, dashboard doanh thu theo danh mục tăng 12% qua đêm nhưng tổng doanh thu không đổi. Bạn điều tra gì?

Tổng không đổi mà tổng theo danh mục tăng là dấu hiệu kinh điển của **fan-out ở dimension**: bảng sản phẩm/danh
mục vừa có khoá lặp, nên join nhân bản dòng ở báo cáo chi tiết, còn báo cáo tổng không join nên đúng.

1. Kiểm `unique` trên khoá của `dim_product` (hoặc bảng map danh mục): đếm khoá có hơn một dòng.
2. So số dòng và tổng doanh thu trước và sau join; chênh lệch là phần nhân bản.
3. Tìm nguồn: mã hàng mới có hai mô tả, bảng map được nạp hai lần, SCD type 2 bị join mà quên lọc `is_current`
   hoặc khoảng hiệu lực.
4. Sửa ở model (dedupe theo quy tắc ghi rõ hoặc join theo khoảng hiệu lực), thêm test `unique` và test đối soát
   "tổng theo danh mục = tổng fact" để lần sau build đỏ trước khi dashboard sai.

Trên Online Retail II, đúng hiện tượng này xảy ra nếu dựng dimension bằng `DISTINCT StockCode, Description`:
doanh thu theo sản phẩm phình 12.3% trong khi tổng doanh thu vẫn 10.67 triệu GBP.

## Vì sao chọn dbt thay vì để logic trong view của BI tool (hoặc ngược lại)?

Chọn **dbt** khi: logic được nhiều công cụ dùng (BI, notebook, reverse ETL), nhiều người cùng sửa, cần test và
review, hoặc bảng nặng cần materialize. dbt mạnh ở phiên bản (git), test, lineage, tài liệu; yếu ở chỗ thêm một
công cụ và một bước CI, và người dùng kéo thả không tương tác trực tiếp với nó.

Để logic ở **BI tool** (LookML, Power BI semantic model, Metabase model) khi: metric chủ yếu dùng trong đúng
một tool, cần self-serve kéo thả với quyền theo dòng, hoặc team nhỏ chưa có hạ tầng. Rủi ro là khoá vào tool và
định nghĩa không dùng lại được ở nơi khác.

Thực tế hay gặp và tôi chọn: làm sạch, grain và bảng fact/dimension trong dbt (gần dữ liệu, có test); định
nghĩa metric một chỗ (semantic layer hoặc mart có cột đã định nghĩa); BI tool chỉ lo trình bày. Với công ty dùng
Power BI làm trung tâm, semantic model của Power BI có thể là metric layer, miễn bảng nó đọc là mart đã test.

## Bạn tài liệu hoá một metric thế nào để người khác không hiểu sai?

Một mục trong metric catalog gồm: tên hiển thị và tên kỹ thuật, định nghĩa một câu cho người không biết SQL,
công thức (tử, mẫu, phép tổng hợp), bộ lọc và bảng nguồn, cột thời gian (ngày đặt hay ngày giao), cộng được qua
kỳ/chiều hay không, owner (người duyệt thay đổi), lưu ý (kỳ chưa đủ, dữ liệu bắt đầu từ đâu, ngoại lệ đã biết),
phiên bản và ngày hiệu lực.

Ví dụ lưu ý thật: "khách mới" của tháng 12/2010 trong Online Retail II là 885, bằng toàn bộ khách hoạt động
tháng đó, vì dữ liệu sheet 2010-2011 bắt đầu từ 01/12/2010; không so tháng này với các tháng sau. Lưu ý kiểu
này phải nằm cạnh định nghĩa, không nằm trong đầu một analyst.

## Bạn nhận một schema 7 bảng chuẩn hoá (bán hàng, sản phẩm, danh mục, khách, thành phố, quốc gia, nhân viên). Bạn chuyển nó thành star schema thế nào?

Theo bốn bước Kimball, nói to từng quyết định:

1. **Quy trình nghiệp vụ**: bán hàng.
2. **Grain**: một dòng `sales` (một sản phẩm trong một giao dịch), khoá `SalesID`; kiểm nó unique.
3. **Dimension**: gộp snowflake thành dimension phẳng: `dim_product` (kèm tên danh mục), `dim_customer` (kèm
   thành phố, quốc gia), `dim_employee` đóng vai nhân viên bán hàng (role-playing nếu sau này có thêm vai khác),
   `dim_date`. Ngày bán thiếu thì gán unknown member, không bỏ dòng.
4. **Fact**: số lượng, chiết khấu, đơn giá tại thời điểm bán, doanh thu tính lại (`quantity × price × (1 −
   discount)`) nếu cột tổng trong nguồn không đáng tin; ghi quyết định này vào tài liệu.

Thêm: test unique cho khoá mỗi bảng, relationships từ fact, đối soát số dòng fact với nguồn. Với bộ Grocery
Sales (sinh giả), cột `TotalPrice` bằng 0 ở mọi dòng và 67 526 dòng thiếu `SalesDate`: đó là quyết định
modeling (tính lại doanh thu, unknown date), còn bộ dữ liệu không dùng để rút insight kinh doanh.
