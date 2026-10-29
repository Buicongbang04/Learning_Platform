# Câu hỏi phỏng vấn: EDA & Data Storytelling

## Bạn nhận một bộ dữ liệu mới và một câu hỏi kinh doanh. Một giờ đầu bạn làm gì?

Không vẽ gì cả trong 15 phút đầu. Thứ tự:

1. **Làm rõ câu hỏi và quyết định**: kết quả phân tích sẽ dẫn tới hành động gì, ai ra quyết định,
   cần độ chính xác cỡ nào. Câu hỏi mơ hồ ("xem dữ liệu khách hàng") thì hỏi lại tới khi cụ thể.
2. **Grain và cơ chế sinh dữ liệu**: một dòng là gì, ghi khi nào, hệ thống nào ghi, cột nào được
   điền sau sự kiện (review chỉ có sau khi giao). Đọc data dictionary, hỏi data engineer.
3. **Kiểm tra chất lượng tối thiểu**: số dòng, khoảng thời gian, null theo cột, khoá có duy nhất
   không, join giữa các bảng có nhân dòng không, kỳ cuối có đầy đủ không.
4. **Một vài phân phối và một breakdown theo thời gian** của metric chính, để thấy vùng hỏng hoặc
   thay đổi định nghĩa.

Kết thúc giờ đầu bằng một danh sách: dữ liệu dùng được cho câu hỏi chưa, cần hỏi ai về điều gì, và
phạm vi phân tích (khoảng thời gian, tổng thể) bạn đề xuất.

## Bạn kiểm tra chất lượng dữ liệu như thế nào? Cho ví dụ lỗi bạn đã gặp.

Theo các chiều: completeness, uniqueness, validity, consistency, referential integrity, timeliness.
Quan trọng hơn danh sách là **phân loại theo tác động lên câu hỏi**: lỗi chặn (khoá chính lặp, khoá
ngoại mồ côi, timeline không thể có), cảnh báo (thiếu một phần), thông tin (đặc điểm nghiệp vụ).

Ví dụ trên Olist thật: `review_id` không duy nhất (1 603 dòng, 547 đơn có hơn một review). Ai dùng
`review_id` làm khoá hoặc join review vào đơn mà không dedupe sẽ đếm một số đơn hai lần và tính sai
tỉ lệ review xấu. Một ví dụ khác: 23 đơn có ngày giao cho hãng vận chuyển **sau** ngày khách nhận,
một timeline không thể xảy ra, cho thấy có cột được ghi nhận sai.

Ứng viên senior nói thêm: các kiểm tra quan trọng phải thành **rule tự động** chạy mỗi lần dữ liệu về
(dbt tests, Great Expectations), có chủ sở hữu và ngưỡng cảnh báo, không phải một notebook chạy một
lần.

## Dữ liệu thiếu 30% ở một cột quan trọng. Bạn xử lý thế nào?

Trước khi chọn cách xử lý, hỏi **vì sao thiếu**:

- **MCAR** (thiếu hoàn toàn ngẫu nhiên): bỏ dòng hoặc impute đơn giản ít gây lệch, chỉ mất power.
- **MAR** (thiếu phụ thuộc vào biến quan sát được): impute có điều kiện, hoặc model hoá xác suất
  thiếu.
- **MNAR** (thiếu phụ thuộc chính giá trị bị thiếu): không có cách thống kê nào cứu hoàn toàn. Ví dụ
  nội dung review Olist trống ở 58.7% dòng, và khách hài lòng thường không viết: phân tích nội dung là
  phân tích một tổng thể lệch về phàn nàn.

Kiểm tra thực tế: so phân phối các biến khác giữa dòng thiếu và không thiếu; xem tỉ lệ thiếu theo thời
gian (một ngày hệ thống ngừng ghi?). Luôn báo cáo số dòng bị loại và kiểm xem kết luận có nhạy với
cách xử lý không. "Missingness" đôi khi là feature tốt (module 10).

## Khi nào dùng trung bình, khi nào dùng trung vị? Còn trục log?

Trung bình trả lời câu hỏi về **tổng** (doanh thu = số đơn × giá trị trung bình), trung vị trả lời
câu hỏi về **trường hợp điển hình**. Với dữ liệu lệch phải như giá item Olist (trung bình 120.65,
trung vị 74.99, p99 890), nói "đơn điển hình khoảng 121 BRL" là sai, nhưng dự báo doanh thu thì phải
dùng trung bình.

Trục log khi dữ liệu dương, trải nhiều bậc độ lớn (giá: p99 gấp 11.9 lần trung vị), hoặc khi quan tâm
tới thay đổi tương đối. Có số 0 thì `log1p` hoặc tách riêng phần bằng 0. Luôn ghi "thang log" trên
trục, vì người đọc mặc định đọc khoảng cách như thang tuyến tính.

## Chọn biểu đồ thế nào? Vì sao nhiều người khuyên tránh pie chart?

Bắt đầu từ câu hỏi: theo thời gian → line; so sánh nhóm → bar sắp xếp (nhóm có thứ tự thì giữ thứ
tự tự nhiên); phân phối → histogram, nhiều nhóm thì box hoặc ECDF; quan hệ hai biến số → scatter,
rất nhiều điểm thì hexbin; thành phần → stacked bar 100%.

Pie bị chê vì mắt người so **độ dài trên cùng một đường gốc** chính xác hơn nhiều so với góc và diện
tích (Cleveland & McGill, 1984). Với 2–3 phần và câu hỏi "chiếm bao nhiêu phần của tổng" thì pie vẫn
chấp nhận được. Với 8 lát, người đọc không thể xếp hạng; bar sắp giảm dần cộng một nhóm "Khác" luôn
tốt hơn.

## Kể vài lỗi trực quan hoá làm người xem hiểu sai.

- **Trục bar không từ 0**: chênh lệch 2% trông như gấp đôi.
- **Hai trục y**: người vẽ chọn tỉ lệ hai trục nên tạo được mọi "tương quan" mong muốn.
- **Kỳ cuối chưa đủ**: Olist có 6 512 đơn tháng 8/2018 và 16 đơn tháng 9 vì dữ liệu cắt ở
  2018-10-17; line chart vẽ thẳng sẽ cho thấy một cú sụp đổ không có thật.
- **Xếp hạng nhóm nhỏ**: bang AP "tốt nhất" về review xấu (6.1%) chỉ vì có 66 đơn.
- **Biểu đồ tích luỹ** che việc kỳ gần nhất giảm.
- **Thiếu tháng trong chuỗi**: Olist không có đơn tháng 11/2016; line chart nối thẳng 10 sang 12.
- **Palette cầu vồng** cho dữ liệu liên tục tạo ranh giới giả, và không đọc được với người mù màu.

## Giải thích Simpson's paradox bằng một ví dụ bạn biết.

Trên Olist: khách SP có tỉ lệ review xấu 10.7%, khách ngoài SP 14.3%. Nhưng ở cùng số ngày giao
(chia 5 nhóm), khách SP có tỉ lệ cao hơn ở 4 nhóm, nhóm còn lại gần bằng. Lý do: 46.9% đơn SP giao
dưới 7 ngày, ngoài SP chỉ 12.7%. Chuẩn hoá theo cùng phân bố số ngày giao: SP 15.2%, ngoài SP 12.3%,
tức chênh lệch đổi dấu. Đây là đảo chiều dạng yếu (sau chuẩn hoá, 4/5 tầng), không phải mọi tầng.
Con số gộp phản ánh phần lớn **mix** (SP được giao nhanh); nó chưa đủ để kết luận về tính cách khách.

Điểm ứng viên senior phải nói: **thống kê không quyết định bảng nào đúng**, cơ chế mới quyết định.
Chia theo trễ / đúng hẹn (khách đánh giá theo lời hứa), SP lại thấp hơn ở cả hai tầng. Nếu câu hỏi là
"mở kho ngoài SP có giúp không" thì số ngày giao là mediator, không được chia theo nó. Phân tầng
theo confounder, không theo mediator hay collider.

## Tỉ lệ conversion của tuần này giảm 10% so với tuần trước. Bạn điều tra thế nào?

Theo thứ tự rẻ tới đắt:

1. **Dữ liệu có đúng không**: tuần này đã đủ ngày chưa, tracking có thay đổi không, có sự cố log,
   bot? So số liệu thô với nguồn khác.
2. **Có bình thường không**: biến động tuần–tuần thường lớn cỡ nào (xem 52 tuần trước), mùa vụ, ngày
   lễ, so với cùng kỳ năm trước.
3. **Tử số hay mẫu số**: ít người mua hơn, hay nhiều người vào hơn (chiến dịch kéo traffic chất lượng
   thấp)?
4. **Mix hay rate**: chia theo kênh, thiết bị, vùng, khách mới/cũ. Nếu mỗi phân khúc không đổi mà
   tổng giảm thì là mix shift (có thể dẫn tới Simpson), không phải sản phẩm tệ đi.
5. **Sự kiện**: release mới, thay đổi giá, đối thủ, sự cố thanh toán.

Báo cáo theo hướng "đã loại trừ gì, còn lại giả thuyết nào, cần dữ liệu gì để xác nhận".

## Viết tiêu đề cho một biểu đồ thế nào?

Tiêu đề là **kết luận** người đọc nên rút ra, có số: "Review xấu lên 21% vào tháng 3/2018, cùng lúc
giao trễ vọt lên 21%", thay vì "Tỉ lệ review xấu theo tháng". Phụ đề ghi định nghĩa và mẫu số ("đơn
giao xong có review, review xấu = 1–2 sao, dữ liệu tới 2018-08").

Lợi ích: người bận chỉ đọc tiêu đề vẫn hiểu; người kỹ có thể phản bác một khẳng định cụ thể; và
người vẽ bị buộc phải có kết luận. Rủi ro: tiêu đề nói quá dữ liệu (nhân quả khi chỉ có tương quan).
Dùng động từ cẩn thận: "đi cùng" khác "làm cho".

## SCQA là gì? Bạn cấu trúc một bài trình bày cho lãnh đạo ra sao?

SCQA (Barbara Minto): **Situation** (bối cảnh chung), **Complication** (điều thay đổi),
**Question** (câu hỏi người đọc tự đặt ra), **Answer** (câu trả lời). Sau đó trình bày theo kim tự
tháp: kết luận và đề xuất ở đầu, 2–4 lý lẽ đỡ kết luận, mỗi lý lẽ một bằng chứng; chi tiết phương
pháp vào phụ lục.

Lỗi thường gặp nhất của DS là kể theo trình tự mình làm ("tôi làm sạch, rồi tôi groupby…"). Lãnh
đạo cần biết nên làm gì và vì sao tin được, trong hai phút đầu. Câu chuyện phương pháp chỉ kể khi
được hỏi, và phải sẵn sàng.

## Dashboard và memo khác nhau thế nào? Khi nào làm cái nào?

Dashboard để **theo dõi**: một nhóm nhỏ KPI có định nghĩa chặt, so với kỳ trước và mục tiêu, có
ngưỡng cảnh báo và người chịu trách nhiệm, cập nhật tự động. Memo để **ra quyết định** cho một câu
hỏi: kết luận, bằng chứng chọn lọc, giới hạn, đề xuất.

Làm dashboard khi câu hỏi lặp lại và có người hành động theo định kỳ. Làm memo khi câu hỏi một lần
hoặc cần lập luận. Dấu hiệu dashboard hỏng: 40 biểu đồ, không ai biết nhìn cái nào; KPI không có
định nghĩa; kỳ cuối chưa đủ dữ liệu làm mọi người hoảng mỗi sáng thứ Hai.

## Một PM muốn bảng xếp hạng seller theo tỉ lệ giao trễ để phạt 10 seller tệ nhất. Bạn nói gì?

Xếp hạng thẳng theo tỉ lệ sẽ phạt seller **nhỏ và xui**: trên Olist (đơn giao xong có review) có 56 seller
tỉ lệ trễ 100%, và cả 56 chỉ có 1–2 đơn. Đề xuất thay thế:

- **Funnel plot**: vẽ tỉ lệ trễ theo số đơn, kèm giới hạn kiểm soát quanh tỉ lệ chung (hẹp dần khi
  n tăng). Chỉ seller nằm ngoài phễu mới khác biệt thật.
- Ngưỡng số đơn tối thiểu, hoặc shrinkage (empirical Bayes).
- Xếp theo **số đơn trễ vượt kỳ vọng** (tác động lên khách), không chỉ theo tỉ lệ.
- Kiểm tra confounder trước khi phạt: seller ở bang xa, bán hàng cồng kềnh, có hãng vận chuyển khác.
  Trễ có thể không phải lỗi seller.

Và hỏi lại mục tiêu: phạt hay hỗ trợ? Nếu mục tiêu là giảm trễ, can thiệp ở hãng vận chuyển hoặc ngày
hẹn giao có thể hiệu quả hơn.

## Case: Giám đốc vận hành Olist hỏi "Vì sao review xấu tăng vọt đầu năm 2018?" Bạn có hai ngày.

Kế hoạch:

1. **Xác nhận hiện tượng và định nghĩa**: tỉ lệ review xấu (1–2 sao, đơn giao xong, review mới nhất
   mỗi đơn) theo tháng. Tháng 1/2018: 13.7%; tháng 2: 19.4%; tháng 3: 21.2%; tháng 4: 11.8%. Kiểm tra
   không phải do thay đổi cách thu thập review.
2. **Tách mix và rate**: tỉ lệ trễ cùng tháng lên 15.9% và 21.1% (tháng 1 là 6.5%). Ở đơn đúng hẹn,
   review xấu chỉ nhích từ 10.3% lên khoảng 10.7%. Giữ tỉ lệ trễ của tháng 1 thì tháng 3 chỉ còn
   khoảng 13.6% review xấu. Kết luận (mô tả, chưa phải nhân quả): gần như toàn bộ phần tăng đi cùng giao trễ.
3. **Đào tiếp vào trễ**: tuyến nào (bang seller → bang khách), hãng vận chuyển, category, seller nào
   đóng góp nhiều nhất số đơn trễ vượt kỳ vọng; có sự kiện bên ngoài (thời tiết, đình công, mùa cao
   điểm sau Tết/Carnaval) không. Ghi rõ phần này là giả thuyết cần xác nhận với đội logistics.
4. **Trình bày**: memo một trang SCQA, tiêu đề là kết luận, ba biểu đồ (review xấu và trễ theo tháng;
   review xấu theo trạng thái trễ; đóng góp theo tuyến), giới hạn (tương quan, review tự nguyện), đề
   xuất (cảnh báo chủ động đơn có nguy cơ trễ, thử nghiệm A/B theo module 03).

## Case: Bạn xây dashboard "Sức khoẻ trải nghiệm khách" cho đội vận hành Olist. Thiết kế thế nào?

- **Người dùng và quyết định**: trưởng ca vận hành mỗi sáng cần biết có tuyến/seller nào cần can
  thiệp. Không phải lãnh đạo xem xu hướng quý.
- **KPI hàng đầu (3–5)**: đơn giao xong, tỉ lệ trễ, tỉ lệ review xấu, thời gian giao trung vị. Mỗi KPI
  có định nghĩa ghi trên dashboard, so với 4 tuần trước và mục tiêu, có người chịu trách nhiệm.
- **Độ chín của dữ liệu**: review về sau giao 1–2 tuần, nên tỉ lệ review xấu của tuần gần nhất chưa
  đầy đủ. Chỉ hiện tuần đã chín, hoặc đánh dấu rõ tuần đang chín. Ghi "dữ liệu tới ngày X".
- **Drill-down**: funnel plot seller (tỉ lệ trễ theo số đơn), bảng tuyến có số đơn trễ vượt kỳ vọng
  lớn nhất.
- **Cảnh báo**: ngưỡng dựa trên biến động lịch sử, không phải ngưỡng tuỳ hứng, để không báo động
  nhầm hằng ngày.
- **Chất lượng dữ liệu**: một ô hiện kết quả các kiểm tra tự động; khi pipeline lỗi, dashboard phải
  nói ra thay vì hiện số sai một cách tự tin.
- **Đo thành công**: dashboard có được dùng không (số lượt xem, quyết định được ghi lại), có KPI nào
  không ai nhìn thì bỏ.

## Case: Một phân tích của bạn cho kết quả ngược với điều CEO tin. Bạn trình bày thế nào?

1. **Kiểm tra lại bản thân trước**: định nghĩa metric, bộ lọc, khoảng thời gian, Simpson's paradox,
   kỳ chưa đủ. Nhờ một DS khác review. Kết quả gây bất ngờ thường là bug.
2. **Hiểu niềm tin của CEO dựa trên gì**: có thể CEO nhìn một phân khúc, một giai đoạn, hoặc một
   metric khác. Nhiều khi hai kết luận cùng đúng ở hai tổng thể khác nhau.
3. **Gặp riêng trước buổi họp lớn**, không làm CEO bất ngờ trước đám đông.
4. **Trình bày bằng câu hỏi chung**: "điều gì phải đúng để niềm tin này đúng?", rồi đưa bằng chứng
   cho từng điều kiện. Một biểu đồ rõ ràng thay cho mười bảng.
5. **Nói rõ mức độ chắc chắn và giới hạn**, đề xuất cách kiểm chứng rẻ (thí nghiệm nhỏ, phân tích
   thêm một tháng dữ liệu). Mục tiêu là quyết định đúng, không phải thắng tranh luận.

## Bạn dùng công cụ profiling tự động (ydata-profiling) không? Giới hạn của nó?

Có, cho lần nhìn đầu: vài phút ra phân phối, null, tương quan, cột hằng, dòng trùng. Giới hạn:

- Không biết **quy tắc nghiệp vụ** (đơn `delivered` phải có ngày giao; ngày giao cho hãng vận chuyển
  phải trước ngày khách nhận; tổng thanh toán khớp tiền hàng).
- Không biết **quan hệ giữa các bảng** (khoá ngoại mồ côi, join nhân dòng).
- Không biết **câu hỏi**: báo cáo 200 trang, không chỉ ra cái gì quan trọng.
- Chậm và tốn bộ nhớ trên dữ liệu lớn; tương quan Pearson giữa mọi cặp cột dễ gây hiểu nhầm.

Nên dùng nó để không bỏ sót điều hiển nhiên, rồi viết các kiểm tra có tên cho những gì quan trọng
và chạy chúng tự động trong pipeline.
