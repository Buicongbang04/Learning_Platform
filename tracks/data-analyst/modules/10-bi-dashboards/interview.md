# Câu hỏi phỏng vấn: BI & Dashboard

## Bạn bắt đầu thiết kế một dashboard mới thế nào?

Từ người dùng và quyết định, không từ dữ liệu có sẵn. Trình tự:

1. **Ai dùng, khi nào, trong cuộc họp nào**: Head of Sales sáng thứ Hai trước họp 9h, mười phút.
2. **Quyết định nào sẽ thay đổi**: dồn chiết khấu cho thị trường nào, gọi lại khách lớn nào. Nếu không nêu được
   quyết định, đó là báo cáo "để biết", nên là email tóm tắt, không phải dashboard.
3. **3-5 câu hỏi** viết thành câu có động từ so sánh ("tuần trước bán cao hơn hay thấp hơn cùng kỳ, vì số đơn hay
   giá trị đơn?").
4. **KPI có định nghĩa**: công thức, grain, kỳ, so với gì, owner. Ví dụ doanh thu = doanh thu gộp dòng hợp lệ.
5. **Wireframe**: KPI tile trên cùng, trend, breakdown, bảng chi tiết; bộ lọc có mặc định; drill-down.
6. **Refresh, cache, kỳ chưa đủ**; dựng; đối chiếu ba con số với SQL; ra mắt cùng người dùng; sau hai tuần xem
   lượt xem và các câu hỏi vẫn đến qua Slack để sửa.

Ứng viên senior nói thêm phần cuối: dashboard là sản phẩm, có vòng đời; dashboard không ai mở sau một tháng nên
được archive, không phải giữ cho đẹp danh mục.

## Self-serve và ad-hoc khác nhau thế nào? Khi nào không nên làm self-serve?

- **Ad-hoc**: DA trả lời một câu hỏi một lần, thường là "vì sao", bằng SQL/notebook và memo có kết luận.
- **Self-serve**: người dùng business tự kéo thả trên dataset/model chuẩn để tự trả lời câu "bao nhiêu, ở đâu".

Self-serve giảm hàng đợi ticket nhưng cần ba điều kiện: model đã chuẩn hoá (đã bỏ đơn huỷ, đã join đúng grain),
metric định nghĩa sẵn ở lớp ngữ nghĩa, và người dùng được hướng dẫn đọc số. Không nên mở self-serve khi dữ liệu
còn bẩn hoặc metric còn tranh cãi: mười người tự tính "doanh thu" theo mười cách, rồi cuộc họp tốn thời gian cãi
số thay vì quyết định. Khi đó DA làm ad-hoc và dashboard chuẩn trước, mở self-serve sau.

## Measure và calculated column trong Power BI khác nhau thế nào? Filter context là gì?

- **Calculated column** tính lúc refresh, cho từng dòng, lưu trong model như một cột: hợp với thuộc tính để nhóm/lọc
  (nhóm tuổi, nhãn mùa).
- **Measure** tính lúc xem, trong **filter context** của ô đang hiển thị: các slicer, bộ lọc trang, hàng/cột của
  matrix. Cùng measure `SUM(Sales[Revenue])` cho ra số khác nhau ở mỗi ô.
- `CALCULATE(<biểu thức>, <bộ lọc>...)` đổi filter context: `CALCULATE([Revenue], ALL('Product'))` bỏ lọc sản
  phẩm để làm mẫu số cho % of total; `CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[Date]))` cho cùng kỳ năm trước
  (cần bảng Date liên tục).

Lỗi hay gặp: tính tỉ lệ thành calculated column rồi để visual lấy trung bình. Trên Bike Sharing, tỉ trọng khách
vãng lai đúng (tổng/tổng) là 18.8%, trung bình tỉ lệ từng ngày là 17.6%; tỉ lệ phải là measure.

## LOD expression của Tableau giải quyết vấn đề gì?

Tableau tổng hợp theo các dimension đang có trong view. LOD cho phép tính ở mức chi tiết khác view:

- `{FIXED [Customer ID] : MIN([Order Date])}`: ngày mua đầu của mỗi khách, dùng để dựng cohort dù view đang nhóm
  theo tháng.
- `{INCLUDE [Invoice] : SUM([Sales])}` rồi lấy trung bình: giá trị trung bình mỗi hoá đơn khi view chỉ có quốc gia.
- `{EXCLUDE [Region] : SUM([Sales])}`: tổng không phụ thuộc region, làm mẫu số.

Phân biệt với **table calculation** (running total, rank, % of total) tính trên bảng kết quả đã tổng hợp của
view, và thứ tự áp dụng bộ lọc: FIXED tính trước dimension filter (trừ khi filter được đưa vào context), nên một
bộ lọc quốc gia có thể không ảnh hưởng LOD FIXED. Đó là nguồn của nhiều con số "không đổi khi lọc".

## LookML là gì? Looker và Looker Studio khác nhau thế nào?

LookML là ngôn ngữ mô tả semantic layer của Looker, lưu trong git: `view` (dimension, measure như `type: sum`,
`type: count_distinct`), `explore` (các view join sẵn kèm quan hệ `many_to_one` để tránh fan-out), `model`. Người
dùng kéo field trong Explore, Looker sinh SQL chạy trên warehouse. Lợi ích chính: một định nghĩa metric, review
bằng pull request, mọi dashboard dùng chung.

Looker Studio (trước là Google Data Studio) là công cụ dashboard kéo thả miễn phí, nối Sheets, GA4, BigQuery,
không có LookML. Hai sản phẩm cùng thương hiệu nhưng khác hẳn về quản trị metric; nhà tuyển dụng hỏi "biết Looker"
thường là hỏi LookML.

## Vì sao bạn chọn Metabase (hoặc Superset) thay vì Power BI cho một startup 50 người?

Câu trả lời đi theo bốn câu hỏi chọn công cụ:

- **Ai dùng**: marketing, ops, CEO, phần lớn không viết SQL. Metabase có query builder và drill-through dễ nhất;
  nếu người dùng chủ yếu biết SQL và cần nhiều loại chart, Superset hợp hơn.
- **Dữ liệu**: Postgres/BigQuery sẵn có; Metabase query trực tiếp, không cần lịch refresh như Import của Power BI.
- **Hệ sinh thái và ngân sách**: công ty dùng Google Workspace, Mac; Power BI Desktop chỉ chạy Windows và cần
  license mỗi người xem. Metabase mã nguồn mở chạy một container.
- **Ai duy trì**: một DA + một DE kiêm; Metabase gần như không cần vận hành.

Đánh đổi phải nói ra: Metabase bản mở không có collection official, verified question, sandboxing (RLS); khi công
ty lớn lên, cần quản trị metric và phân quyền theo dòng thì xem lại (Metabase trả phí, Superset với RLS, hoặc
Power BI nếu chuyển sang Microsoft 365). Chọn công cụ là quyết định có thời hạn.

## Field filter trong SQL của Metabase là gì, khác biến text thế nào?

- **Biến text/number** `{{min_qty}}`: Metabase chỉ thay giá trị vào chỗ biến; bạn tự viết điều kiện và tự xử lý
  khi trống bằng `[[AND quantity >= {{min_qty}}]]`.
- **Field filter** `{{country}}` (tag kiểu dimension trỏ vào một cột): viết `WHERE {{country}}`. Metabase sinh cả
  điều kiện, nhận nhiều giá trị (`... = 'Germany' OR ... = 'France'`), thành `1 = 1` khi trống, và widget có danh
  sách giá trị của cột.

Hai bẫy: field filter tham chiếu cột bằng tên bảng đầy đủ nên bảng trong `FROM` không được đặt alias; và nơi đặt
`{{country}}` quyết định cái gì bị lọc. Trong bài Intermediate 02, mốc "tháng đủ gần nhất" tính trên toàn bộ dữ
liệu (CTE không có `{{country}}`), còn doanh thu tính trên nước đang lọc.

## Hai dashboard báo hai con số doanh thu tháng khác nhau. Bạn xử lý thế nào?

1. **Tái hiện**: cùng kỳ, cùng bộ lọc, cùng thời điểm xem; chụp SQL thật của từng card (Metabase có "View the
   SQL", Superset có "View query").
2. **So định nghĩa theo checklist**: có bỏ đơn huỷ không; doanh thu gộp hay ròng; ngày đặt hay ngày giao; múi giờ;
   bộ lọc ẩn (chỉ khách có mã, bỏ UK); grain và join (fan-out); kỳ chưa đủ; cache cũ.
3. **Reconcile bằng SQL** trên bảng nguồn: con số nào đúng với định nghĩa đã thống nhất.
4. **Sửa gốc, không sửa ngọn**: đưa định nghĩa về một chỗ (model/semantic layer/dbt), cho cả hai dashboard đọc từ
   đó, archive card sai, ghi định nghĩa vào mô tả card.

Trên Online Retail II, "doanh thu 11/2011" có thể là 1 509 496.33 GBP (doanh thu gộp, dòng hợp lệ) hoặc nhỏ hơn
nếu trừ hoá đơn huỷ trong tháng. Cả hai đều "đúng" theo định nghĩa của nó; lỗi là không ghi định nghĩa nào.

## Case: dashboard doanh số mất 40 giây để mở, sales không dùng nữa. Bạn làm gì?

Đo trước, sửa sau:

1. **Card nào chậm**: xem thời gian từng query (log của BI, `pg_stat_statements`, query history của warehouse).
   Thường một hai card chiếm phần lớn thời gian.
2. **Vì sao chậm**: quét toàn bảng dòng hàng cho mỗi lần mở; join lớn; `COUNT(DISTINCT)` trên hàng triệu dòng;
   bộ lọc không đẩy xuống được; mười card cùng chạy đồng thời.
3. **Sửa theo thứ tự rẻ tới đắt**: bớt card (dashboard 25 card thường chỉ cần 8); bảng tổng hợp sẵn theo ngày ×
   nước × sản phẩm do pipeline build (DE module 09); materialized view; cache với TTL khớp chu kỳ nạp và xoá cache
   sau mỗi lần nạp; index/partition ở nguồn.
4. **Đo lại và báo**: mục tiêu cụ thể (dưới 5 giây), và lượt xem sau hai tuần.

Không sửa bằng cách bỏ bộ lọc hay rút ngắn kỳ mà không hỏi người dùng: dashboard nhanh mà không trả lời câu hỏi
cũng không ai mở.

## Case: CEO muốn "một dashboard có tất cả mọi thứ". Bạn trả lời thế nào?

Không từ chối, mà đổi câu hỏi: "Sáng thứ Hai anh cần biết gì để quyết định khác đi?". Sau đó:

- Đề xuất **một dashboard điều hành** 5-7 KPI có so cùng kỳ, mỗi KPI có link drill xuống dashboard chuyên đề
  (sales, marketing, vận hành) do team tương ứng sở hữu.
- Giải thích đánh đổi bằng chi phí của người xem: 30 tile nghĩa là không tile nào được nhìn; dashboard chậm; mỗi
  tile là một định nghĩa cần duy trì.
- Cho thấy bản nháp (wireframe) trong một ngày, thay vì tranh luận trừu tượng; hẹn xem lại sau hai tuần dựa trên
  câu hỏi thật của CEO.

## Case: bạn ra mắt dashboard cho team marketing, một tháng sau lượt xem gần bằng 0. Bạn làm gì?

Coi đó là tín hiệu sản phẩm, không phải lỗi người dùng:

1. **Dữ liệu dùng**: lượt xem theo người, card nào được click, bộ lọc nào được dùng (Metabase/Superset có log).
2. **Phỏng vấn 3-4 người**: họ trả lời câu hỏi của mình bằng gì (Excel tự kéo, nhắn DA, GA4)? Dashboard thiếu
   gì: số không khớp với GA4, không có chiều kênh, chậm, không nằm trong quy trình họp.
3. **Sửa đúng nguyên nhân**: định nghĩa khác công cụ họ tin → reconcile và ghi chú; thiếu chiều → thêm; không nằm
   trong quy trình → gửi bản chụp tự động (subscription/alert) vào kênh Slack của team trước họp.
4. Nếu câu hỏi thật là ad-hoc theo chiến dịch, dashboard có thể không cần thiết: archive và thay bằng một model
   self-serve tốt.

## Làm sao xử lý kỳ chưa đủ dữ liệu (tháng hiện tại) trên dashboard?

- KPI tile dùng **kỳ đủ gần nhất**, mốc lấy từ dữ liệu (`max(timestamp)`), không gõ cứng.
- Trend: bỏ kỳ dở dang hoặc vẽ khác (nét đứt, màu nhạt) kèm chú thích "tới ngày 9".
- Nếu cần xem kỳ đang chạy: so **cùng số ngày** (1-9/12/2011 so với 1-9/11/2011 và 1-9/12/2010), không so tháng dở
  dang với tháng đủ. Online Retail II kết thúc 09/12/2011: tháng 12 ngây thơ "giảm 58%" so với tháng 11.
- Hiện "dữ liệu tới lúc ..." trên đầu dashboard.

Trên Bike Sharing, tuần cuối chỉ có ngày 31/12/2012; tile tuần ngây thơ báo -74.5% so với tuần trước.

## Refresh và cache: bạn đặt thế nào cho một dashboard?

Theo nhịp quyết định và chu kỳ nạp dữ liệu:

- Họp tuần, dữ liệu nạp 5h sáng hằng ngày: query trực tiếp với cache 12-24 giờ, **xoá cache sau mỗi lần nạp**
  để số mới xuất hiện ngay.
- Vận hành theo giờ: nạp mỗi 15 phút, cache ngắn hơn chu kỳ nạp, cảnh báo khi số vượt ngưỡng.
- Import/Extract (Power BI, Tableau): lịch refresh sau khi pipeline xong, không trước; theo dõi refresh thất bại.

Hai lỗi hay gặp: cache dài hơn chu kỳ nạp (dashboard luôn chậm một ngày) và không hiện thời điểm dữ liệu (pipeline
chết từ hôm qua mà không ai biết). Cache cũng che lỗi: sau khi sửa định nghĩa metric, nhớ xoá cache.

## Row-level security là gì? Khi nào cần?

RLS giới hạn mỗi người chỉ thấy các dòng của mình: quản lý cửa hàng chỉ thấy cửa hàng mình, đối tác chỉ thấy dữ
liệu của họ. Cách làm: Power BI định nghĩa role bằng biểu thức DAX trên bảng dimension; Tableau dùng user filter
hoặc entitlement table; Superset có Row Level Security filter gắn vào dataset theo role; Metabase gọi là data
sandboxing (bản trả phí); Looker dùng `access_filter`.

Nguyên tắc: RLS đặt ở lớp dữ liệu/model, không bằng cách tạo một dashboard riêng cho mỗi người (không duy trì
nổi, dễ lộ). Kiểm RLS bằng cách đăng nhập (hoặc "view as") đúng vai trò trước khi ra mắt, và nhớ rằng tổng trên
dashboard của một người không bằng tổng công ty: ghi rõ trên tile.

## Khi nào bạn chọn Streamlit thay cho Metabase/Superset?

Khi logic vượt khả năng BI: mô phỏng kịch bản (what-if về giá, tồn kho), gọi model dự báo, form nhập liệu, quy
trình nhiều bước, hoặc layout rất riêng. Người dùng ít, nội bộ, và có người Python duy trì.

Không chọn Streamlit khi: nhiều người dùng business cần tự cắt lát (self-serve), cần RLS và phân quyền theo nhóm,
hoặc không ai sẵn sàng duy trì code. Nếu chọn, viết logic KPI thành hàm thuần có unit test, UI test bằng
`AppTest`, `@st.cache_data` cho phần đọc dữ liệu (mỗi tương tác chạy lại cả script), và để app trong git như mọi
code khác.

## Bạn kiểm một dashboard trước khi ra mắt thế nào?

- **Số**: đối chiếu ít nhất ba con số với SQL/pandas độc lập trên bảng nguồn (tổng kỳ, một breakdown, một ô có
  bộ lọc); tổng các phần bằng tổng chung.
- **Bộ lọc**: mỗi bộ lọc có nối vào mọi card; chọn một giá trị và kiểm từng card đổi đúng; giá trị mặc định.
- **Kỳ**: kỳ chưa đủ xử lý đúng; múi giờ.
- **Quyền**: xem dưới vai trò người dùng thật (RLS, collection).
- **Tốc độ**: thời gian mở với cache trống.
- **Đọc hiểu**: một người dùng thật đọc dashboard và nói lại kết luận trong một phút; nếu họ hiểu sai, sửa tiêu
  đề, nhãn, thứ tự trước khi sửa thêm số.

## Dashboard as code là gì, vì sao DA nên quan tâm?

Định nghĩa question, chart, dashboard bằng code hoặc tệp khai báo (gọi API Metabase/Superset từ script, export
YAML của Superset, LookML, Power BI project `.pbip`), lưu trong git. Lợi ích: review thay đổi như code, tái tạo
dashboard trên môi trường khác, khôi phục khi ai đó lỡ xoá, biết ai đổi định nghĩa lúc nào. Script phải
**idempotent**: chạy lại không tạo bản trùng (tìm theo tên rồi cập nhật), như các bài trong module này.

Đánh đổi: thêm một bước cho thay đổi nhỏ, và người dùng business sửa trên giao diện sẽ bị ghi đè ở lần deploy
sau; cần quy ước dashboard nào "do code quản lý" (thường là dashboard chính thức), dashboard nào cho tự do.
