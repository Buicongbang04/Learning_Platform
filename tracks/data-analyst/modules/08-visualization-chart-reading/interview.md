# Câu hỏi phỏng vấn: Trực quan hoá & đọc biểu đồ

## Bạn chọn chart thế nào? Cho ví dụ chọn chart cho vài tình huống cụ thể.

Bắt đầu từ câu hỏi, không từ loại chart. Viết câu hỏi thành một câu có động từ so sánh, xác định nó
thuộc loại nào: so sánh, xu hướng, phân phối, thành phần, quan hệ hay luồng; rồi chọn chart mặc
định cho loại đó và chỉ đổi khi có lý do.

| Tình huống | Chart | Lý do |
| --- | --- | --- |
| Doanh thu 10 quốc gia lớn nhất | Bar ngang, sắp giảm dần, gộp "Khác" | So sánh nhóm danh định; nhãn dài đọc được |
| Số đơn hằng ngày 2 năm | Line, có đường cùng kỳ năm trước | Xu hướng + mùa vụ |
| Giá trị đơn hàng | Histogram trục log, báo median | Phân phối đuôi dài |
| Tỉ trọng kênh bán theo quý | Stacked bar 100% | Thành phần thay đổi theo thời gian |
| Chi phí quảng cáo vs doanh thu theo chiến dịch | Scatter, kích thước điểm theo số đơn | Quan hệ hai biến số |
| Lượt dùng theo giờ × thứ | Heatmap | Pattern hai chiều phân loại |
| Xem sản phẩm → giỏ → thanh toán | Funnel (bar ngang có thứ tự) với % so bước trước | Luồng tuần tự |

Một ứng viên senior nói thêm: cùng một dữ liệu có thể trả lời nhiều câu hỏi, và chart sai thường
không phải vì sai loại mà vì trả lời câu hỏi khác câu người xem đang hỏi. Trên Bike Sharing, bar
theo thứ cho thấy các ngày chỉ chênh 11%, còn heatmap giờ × thứ cho thấy hình dạng ngày làm việc và
cuối tuần hoàn toàn khác nhau. Câu hỏi "bố trí xe giờ nào" cần heatmap.

## Vì sao nhiều người khuyên tránh pie chart? Khi nào pie vẫn chấp nhận được?

Pie mã hoá giá trị bằng **góc và diện tích**, hai kênh mắt người so sánh kém chính xác hơn nhiều so
với **độ dài trên trục chung** (Cleveland & McGill, 1984). Hệ quả:

- Với 5+ lát, người xem không xếp hạng được các lát gần nhau (22% và 25% trông như nhau).
- Lát nhỏ không có chỗ ghi nhãn, phải dùng legend, mắt dò qua lại.
- So hai pie (năm nay vs năm ngoái) gần như không thể.
- Pie không thể hiện được tổng thay đổi; hai pie cùng kích thước trong khi tổng tăng gấp đôi.

Pie chấp nhận được khi: 2–3 phần, một thời điểm, thông điệp là "phần lớn" hoặc "khoảng một phần tư"
(ví dụ: khách vãng lai chiếm 18.8% lượt thuê). Ngay cả khi đó, một con số to (big number) thường
truyền đạt tốt hơn. Thay thế mặc định: bar ngang sắp giảm dần; thành phần theo thời gian thì stacked
bar 100%.

## Dual axis chart có vấn đề gì? Khi nào chấp nhận được?

Hai trục y có thang độc lập, mỗi thang người vẽ tự chọn min/max. Bằng cách kéo thang, có thể làm hai
chuỗi trông như đi cùng nhau, ngược nhau hoặc cắt nhau ở bất kỳ điểm nào. "Điểm giao nhau" không có
nghĩa gì. Người xem còn hay đọc nhầm series nào thuộc trục nào.

Chấp nhận được khi:

1. Hai trục là **cùng một đại lượng ở hai đơn vị** có quan hệ cố định (°C/°F, VND/USD theo tỉ giá cố
   định): không có tự do chọn thang.
2. Cột là khối lượng (số đơn), đường là tỉ lệ (conversion rate), cho người đọc nội bộ đã quen dạng
   này; trục trái từ 0, màu trục khớp màu series.

Thay thế tốt hơn: hai panel xếp chồng chung trục x; chỉ số hoá cả hai chuỗi về 100 tại kỳ gốc rồi vẽ
trên một trục; hoặc scatter của chuỗi A theo chuỗi B nếu câu hỏi là quan hệ.

## Khi nào trục y phải bắt đầu từ 0, khi nào không?

- **Bar, area, stacked**: luôn từ 0. Các chart này mã hoá bằng **độ dài/diện tích**; cắt trục làm độ
  dài không tỉ lệ với giá trị. Trên Bike Sharing, thứ Sáu chỉ hơn Chủ nhật 11% lượt thuê/ngày,
  nhưng nếu trục từ 4 200, bar thứ Sáu cao gấp ~17 lần, lie factor khoảng 150.
- **Line, dot plot, scatter**: không bắt buộc. Chúng mã hoá bằng **vị trí và độ dốc**; ép trục từ 0
  có thể làm biến động có ý nghĩa (nhiệt độ cơ thể 36.5 → 39) trông phẳng.

Muốn nhấn một khác biệt nhỏ trên dữ liệu kiểu bar, đừng cắt trục: vẽ **chênh lệch** (Δ hoặc % so
với baseline) bằng bar từ 0, hoặc dùng dot plot. Và khi trục line không từ 0, ghi rõ giá trị trục để
người đọc không đọc độ cao như tỉ lệ.

## Case: CEO nhắn "Chart doanh thu tháng này giảm 40%, chuyện gì vậy?". Bạn xử lý thế nào?

Không trả lời nguyên nhân trước khi kiểm tra chart. Theo thứ tự:

1. **Kỳ chưa đủ dữ liệu?** Phổ biến nhất. Ví dụ thật: Online Retail II kết thúc 9/12/2011; doanh thu
   tháng 12 so với tháng 11 là −57.7%, nhưng tháng 12 mới có 9 ngày lịch (8 ngày có giao dịch). So cùng ngày 1–9: cao hơn cùng
   kỳ năm trước **45.6%** và cao hơn 1–9/11 40.6%. Câu chuyện đổi chiều. Nhưng đó là
   doanh thu gộp: một hoá đơn 168 470 GBP trong 9 ngày này chiếm phần lớn mức chênh, nên trước khi
   báo con số phải kiểm outlier và đơn bị huỷ ngay sau đó (mức tăng thực nhỏ hơn nhiều, xem bước 2).
2. **Định nghĩa và dữ liệu**: pipeline có trễ hoặc lỗi không (số đơn ngày hôm qua bằng 0?), có đổi
   định nghĩa doanh thu (net vs gross, đã trừ hoàn hàng chưa), đổi múi giờ, có nguồn dữ liệu nào
   ngừng đổ về?
3. **Mùa vụ**: so tháng với tháng trước là so hai mùa khác nhau. So cùng kỳ năm trước (YoY), hoặc
   so với forecast có mùa vụ.
4. **Nếu giảm là thật**: breakdown theo các chiều (kênh, quốc gia, nhóm sản phẩm, khách mới/cũ) để
   tìm phần đóng góp; tách số đơn × giá trị mỗi đơn.

Trả lời CEO ngắn, có mốc thời gian: "Tháng 12 mới có 9 ngày nên chart đang so 9 ngày với 30 ngày.
So cùng 9 ngày năm ngoái, doanh thu vẫn cao hơn; em đang kiểm một đơn rất lớn trong 9 ngày đầu tháng 12 trước khi chốt
con số. Em đã sửa chart để đánh dấu kỳ dở dang." Sau đó
sửa nguồn gốc: dashboard nên ẩn hoặc đánh dấu nét đứt kỳ chưa kết thúc, và mặc định so cùng số ngày.

## Case: chart kết quả A/B test trong slide của đồng nghiệp đã cắt trục y. Bạn làm gì?

Kiểm tra trước, góp ý sau, và góp ý riêng chứ không trong họp lớn:

1. Đọc số thật trên chart (ví dụ giả định, không phải dữ liệu thật): conversion A 4.0%, B 4.2%,
   trục từ 3.9% làm B trông gấp ba A. Hiệu ứng thật là +0.2 điểm phần trăm (+5% tương đối).
2. Câu hỏi quan trọng hơn trục: **khoảng tin cậy** của chênh lệch là bao nhiêu, có đủ mẫu chưa,
   test đã chạy đủ chu kỳ tuần chưa, có kiểm sample ratio mismatch chưa. Chart bar của hai tỉ lệ
   không có error bar thì không cho biết khác biệt có thật không.
3. Đề xuất chart thay: một điểm ước lượng chênh lệch (B − A) với khoảng tin cậy 95% và đường 0,
   hoặc bar từ 0 kèm error bar. Headline (tiếp ví dụ giả định): "B tăng conversion 0.2 điểm %
   (CI 95%: −0.1 tới +0.5), chưa đủ bằng chứng để ship".

Lý do phải sửa dù không cố ý: người ra quyết định nhớ **hình**, không nhớ nhãn trục. Một chart phóng
đại có thể dẫn tới ship một thay đổi không có tác dụng.

## Case: bạn trình bày funnel cho PM. Bạn vẽ và nói thế nào?

- **Chart**: bar ngang theo thứ tự các bước, bước đầu trên cùng; mỗi bar ghi số tuyệt đối, % so với
  bước đầu và % so với bước trước. Phân biệt **rơi tuyệt đối** (số người mất ở mỗi bước, cho
  biết cải thiện bước nào chạm nhiều người nhất) với **rơi tương đối** (% so bước trước, cho biết
  bước nào chuyển đổi kém nhất); hai cách có thể chỉ ra hai bước khác nhau.
- **Định nghĩa**: funnel theo **cohort** (người vào bước 1 trong tuần X, bao nhiêu người tới bước 2
  trong N ngày) hay **tích luỹ** (đếm mỗi bước trong cả kỳ)? Funnel tích luỹ bị lệch vì người vào cuối
  kỳ chưa kịp đi tiếp. Có bắt buộc đi đúng thứ tự không? Đếm user hay session?
- **Headline** gắn với hành động: ví dụ funnel quay lại mua trên Online Retail II: 4 338 khách, 65.6%
  mua từ đơn thứ 2, 46.3% từ đơn thứ 3, 25.7% từ đơn thứ 5, 9.0% từ đơn thứ 10. Về số tuyệt
  đối, bước 1 → 2 mất nhiều khách nhất (1 493 khách); về tỉ lệ so bước trước, bước ≥ 5 → ≥ 10 rơi
  mạnh nhất (chỉ 35% đi tiếp), nhưng bước đó gộp năm lần mua nên không so ngang được. Headline: "1 493
  khách (34%) không quay lại lần 2, bước mất nhiều khách nhất: ưu tiên email/ưu đãi sau đơn đầu."
- **Breakdown**: một funnel gộp che khác biệt giữa kênh/thiết bị; small multiples funnel theo kênh
  thường là slide thứ hai.
- **So sánh**: kèm funnel kỳ trước hoặc benchmark; tỉ lệ một mình không biết tốt hay xấu.

## Simpson's paradox là gì? Làm sao phát hiện trên chart?

Xu hướng trong từng nhóm ngược với xu hướng khi gộp các nhóm, vì cơ cấu (mix) các nhóm khác nhau
giữa hai bên đang so. Ví dụ kinh điển: bệnh viện A tỉ lệ tử vong cao hơn B tổng thể, nhưng thấp hơn
B ở cả ca nhẹ lẫn ca nặng, vì A nhận nhiều ca nặng hơn.

Hiện tượng tương tự Simpson (confounding) trên Bike Sharing: gộp hai năm, nhiệt độ tương quan +0.63 với lượt thuê/ngày, nhưng
trong mùa hè 2012 tương quan là −0.33. Đường xu hướng gộp chủ yếu so mùa đông với mùa hè; trong mùa
hè, nóng thêm làm giảm lượt thuê.

Phát hiện:

- Mỗi khi so một tỉ lệ/trung bình gộp giữa hai nhóm hoặc hai kỳ, hỏi: cơ cấu theo phân khúc chính
  (kênh, quốc gia, thiết bị, khách mới/cũ) có thay đổi không? Vẽ cả tỉ trọng và metric theo phân khúc.
- Scatter tô màu theo nhóm, kèm đường xu hướng từng nhóm.
- Biến chia nhóm nào là đúng thì quyết định bằng cơ chế (biến đó có phải confounder không), không
  bằng thống kê.

## Mean hay median trên chart? Khi nào dùng cái nào?

Phụ thuộc vào hình dạng phân phối và câu hỏi:

- Phân phối gần đối xứng: mean và median gần nhau, dùng mean (cộng dồn được).
- Đuôi dài (doanh thu, giá trị đơn, thời gian phản hồi): median đại diện "trường hợp điển hình" tốt
  hơn. Online Retail II: giá trị hoá đơn mean 534 GBP, median 304 GBP, max 168 470 GBP, skew 51. Một
  bar "giá trị đơn trung bình theo quốc gia" sẽ bị vài đơn sỉ quyết định.
- Nhưng nếu câu hỏi là **tổng tiền** (dự báo doanh thu = số đơn × giá trị TB), phải dùng mean, vì
  median không cộng dồn được.

Trên chart nên hiện phân phối chứ không chỉ một con số: box plot, histogram có vạch mean và median,
hoặc median kèm p25–p75. Với latency/SLA thì p90/p95/p99 quan trọng hơn cả mean lẫn median.

## Khi nào dùng log scale? Rủi ro là gì?

Dùng khi:

- Dữ liệu trải nhiều bậc độ lớn (doanh thu theo khách từ 10 tới 100 000), thang tuyến tính dồn mọi
  thứ vào góc.
- Quan tâm **tốc độ tăng tương đối**: trên log scale, tăng trưởng % không đổi là đường thẳng (ca
  nhiễm giai đoạn đầu dịch, user tăng trưởng hằng tháng).
- Histogram đuôi dài: bins đều trên log cho thấy hình dạng thật.

Rủi ro: khán giả không chuyên đọc log như tuyến tính và đánh giá thấp chênh lệch (khoảng cách giữa
1 000 và 10 000 bằng giữa 10 và 100). Không vẽ được số 0 và số âm (dùng `log1p` hoặc symlog, và ghi
chú). Bar chart trên log không có ý nghĩa vì không có điểm 0. Luôn ghi "thang log" trên trục hoặc
tiêu đề; trình bày cho lãnh đạo thì cân nhắc vẽ % tăng trưởng trên thang tuyến tính thay vì log.

## Dashboard bị chê "rối". Bạn sửa thế nào?

"Rối" thường là triệu chứng của dashboard không có câu hỏi chính. Thứ tự sửa:

1. **Hỏi lại mục đích và người dùng**: dashboard này giúp ai quyết định gì, mở bao lâu một lần? Một
   dashboard cố phục vụ CEO và analyst cùng lúc sẽ rối với cả hai; tách thành dashboard tổng quan và
   dashboard chi tiết (drill-down).
2. **Cắt**: tile nào không ai nhìn trong 30 ngày (BI tool có log xem) thì bỏ. Mục tiêu 5–9 tile.
3. **Bố cục theo cách mắt quét**: KPI chính hàng trên với so sánh kỳ trước/target, trend ngay dưới,
   breakdown và bảng chi tiết ở dưới. Bộ lọc toàn cục một chỗ.
4. **Nhất quán**: cùng màu cho cùng khái niệm ở mọi tile, cùng định dạng số, cùng khoảng thời gian
   mặc định, cùng định nghĩa metric (lấy từ một semantic layer).
5. **Giảm mực**: bỏ 3D, gauge, pie nhiều lát, legend thừa; một màu nhấn; tiêu đề tile là câu hỏi
   hoặc insight.
6. **Kiểm với người dùng thật**: cho họ 5 giây nhìn, hỏi họ thấy gì. Nếu không trả lời được câu hỏi
   chính, chưa xong.

## Chọn matplotlib, plotly hay BI tool (Power BI, Tableau, Metabase) thế nào?

Theo người xem, tần suất và mức tương tác:

- **matplotlib/seaborn**: chart tĩnh cho slide, memo, báo cáo một lần; sinh từ code trong git nên tái
  lập được; chạy được trong pipeline (gửi ảnh vào Slack hằng sáng).
- **plotly**: cần hover/zoom trong notebook, gửi một tệp HTML cho người không có BI, prototype app
  (Streamlit, Dash). Có sẵn funnel, sunburst, map.
- **BI tool**: nhiều người xem lặp lại hằng tuần, cần tự lọc/cắt lát, cần phân quyền và lịch làm
  mới. Power BI khi công ty đã dùng Microsoft 365; Tableau khi cần phân tích trực quan mạnh và có
  ngân sách; Metabase/Superset khi muốn mã nguồn mở, SQL-first, tự host.
- **Excel**: người nhận cần sửa số hoặc tự thử kịch bản.

Điểm senior: chọn công cụ ít quan trọng bằng việc **định nghĩa metric nằm ở đâu**. Nếu mỗi workbook
tự tính "doanh thu", hai dashboard sẽ ra hai số. Metric nên định nghĩa một lần (dbt model, semantic
layer), mọi công cụ đọc từ đó.

## Quy trình đọc một chart của người khác?

Năm bước:

1. **Trục và đơn vị**: từ 0 không, log hay tuyến tính, tổng hay TB hay tỉ lệ (mẫu số là gì), kỳ
   nào, kỳ cuối đủ chưa, có bộ lọc ẩn không.
2. **Hình dạng tổng**: xu hướng, mùa vụ, phân phối, cụm.
3. **Điểm bất thường**: đỉnh, đáy, gãy; thật hay lỗi dữ liệu.
4. **So với tham chiếu**: kỳ trước, cùng kỳ năm trước, nhóm khác, target.
5. **Câu hỏi tiếp theo**: breakdown nào, dữ liệu nào xác nhận.

Và tách **quan sát** ("lượt thuê tháng 12 thấp hơn tháng 9 43%") khỏi **kết luận** ("nhu cầu giảm":
sai, vì mùa đông năm nào cũng giảm, và tháng 12/2012 vẫn cao hơn 12/2011 42%). Trong họp, nói quan
sát trước, kết luận kèm mức độ chắc chắn và bằng chứng còn thiếu.

## Màu trong chart: chọn palette thế nào?

- **Categorical** cho nhóm không thứ tự, tối đa ~7 màu; nhiều hơn thì gộp "Khác" hoặc small multiples.
- **Sequential** (viridis, Blues) cho giá trị từ thấp tới cao: heatmap số lượng, bản đồ mật độ.
- **Diverging** (RdBu) khi có điểm giữa có nghĩa: tăng/giảm so với kỳ trước, so với target; căn tâm
  tại điểm đó.

Quy tắc thêm: tránh rainbow/jet (tạo ranh giới giả, không đều về độ sáng); tránh đỏ/xanh lá là tín
hiệu duy nhất (khoảng 8% nam giới mù màu đỏ–xanh lá), thêm ký hiệu hoặc dùng cam/xanh dương; một màu
nhấn, còn lại xám; giữ nhất quán màu cho cùng khái niệm trên mọi chart của dashboard. Kiểm bằng
ColorBrewer hoặc chế độ mô phỏng mù màu.

## "Headline là insight" nghĩa là gì? Cho ví dụ sửa tiêu đề chart.

Tiêu đề chart nói **kết luận người đọc nên rút ra**, không mô tả chart chứa gì. Người bận chỉ đọc
tiêu đề; nếu tiêu đề là "Doanh thu theo tháng", họ phải tự diễn giải và có thể diễn giải sai.

- Yếu: "Lượt thuê theo giờ". Mạnh: "Ngày làm việc có hai đỉnh đi làm 8h và 17h; cuối tuần đông
  buổi trưa".
- Yếu: "Doanh thu theo tháng". Mạnh: "Tháng 12 chưa kết thúc: 9 ngày đầu cao hơn cùng kỳ năm trước".

Cấu trúc: metric + con số + so với gì. Phụ đề ghi phạm vi, bộ lọc, nguồn. Rủi ro: headline biến thành
quảng cáo nếu nói mạnh hơn dữ liệu; nếu bằng chứng yếu, headline phải nói vậy ("chưa đủ dữ liệu để
kết luận B tốt hơn A").

## Small multiples là gì? Khi nào dùng thay cho một chart nhiều đường?

Một loạt chart nhỏ cùng loại, cùng thang, mỗi panel là một nhóm. Dùng khi một chart có hơn ~4–5 đường
(spaghetti), khi các nhóm chồng lên nhau, hoặc khi câu hỏi là so **hình dạng** giữa nhóm. Ví dụ Bike
Sharing: panel `casual` và panel `registered`, mỗi panel hai đường ngày làm việc/cuối tuần theo giờ:
thấy ngay thành viên đi làm (đỉnh 8h, 17h) còn khách vãng lai đi chơi buổi trưa cuối tuần.

Quyết định quan trọng: **chung trục y** khi muốn so độ lớn (mặc định), **riêng trục y** khi chỉ so
hình dạng và nhóm khác nhau nhiều bậc, kèm ghi chú rõ để không ai so độ cao giữa panel. Sắp panel theo
thứ tự có nghĩa (theo quy mô hoặc theo thứ tự tự nhiên), không theo bảng chữ cái.

## Bạn sẽ dùng heatmap khi nào, và lỗi hay gặp với heatmap?

Heatmap hợp với ma trận hai chiều phân loại: giờ × thứ (tìm giờ cao điểm), cohort × tháng (retention),
sản phẩm × vùng. Nó tốt để thấy **pattern**, kém để so chính xác hai ô vì màu là kênh thị giác kém
chính xác.

Lỗi hay gặp:

- Dùng palette diverging cho dữ liệu không có điểm giữa, hoặc rainbow cho dữ liệu liên tục.
- Không chuẩn hoá: heatmap số lượng tuyệt đối theo cohort bị cohort lớn chi phối; retention nên là %
  của cohort.
- Ô có n nhỏ có màu cực đoan do nhiễu; cần ẩn hoặc làm mờ ô có n dưới ngưỡng.
- Thứ tự hàng/cột tuỳ tiện (theo alphabet) làm mất pattern; sắp theo thứ tự tự nhiên hoặc theo
  clustering.
- Thiếu giá trị trong ô khi người xem cần con số: thêm `annot=True` cho ma trận nhỏ.
