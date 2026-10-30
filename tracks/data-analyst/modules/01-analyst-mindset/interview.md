# Câu hỏi phỏng vấn: Vai trò DA & tư duy phân tích

## Data Analyst khác Data Scientist, Data Engineer và BI developer ở đâu? Bạn thấy mình ở đâu?

Phân biệt bằng **sản phẩm đầu ra** và **người đọc**, không bằng công cụ:

| Vai trò | Sản phẩm | Người đọc | Thành công là |
| --- | --- | --- | --- |
| Data Analyst | Phân tích, memo, dashboard, câu trả lời ad-hoc | Người ra quyết định (CEO, PM, marketing) | Quyết định thay đổi nhờ phân tích |
| BI developer | Dashboard định kỳ, data model trong BI | Nhiều người xem lặp lại | Số đúng, nhanh, ai cũng tự xem được |
| Analytics Engineer | Mô hình dbt, metric định nghĩa một chỗ | DA, BI, DS | Bảng đáng tin, có test, có tài liệu |
| Data Scientist | Model, thí nghiệm, phân tích nhân quả | Sản phẩm, team kỹ thuật, lãnh đạo | Model tốt hơn baseline và được dùng |
| Data Engineer | Pipeline, warehouse | Mọi người dùng dữ liệu | Dữ liệu đúng, đủ, kịp, rẻ |

Câu trả lời tốt nói thêm ranh giới thực tế mờ: công ty nhỏ một người làm nhiều vai; và nêu mình mạnh ở
đâu bằng ví dụ ("tôi từng phân rã doanh thu theo khách × tần suất × AOV để chỉ ra mức tăng đến từ khách
mới, team marketing đổi ngân sách theo đó"). Người phỏng vấn muốn nghe bạn hiểu DA là **người biến dữ liệu
thành quyết định**, không phải "người kéo số".

## Kể tên bốn loại analytics và cho mỗi loại một ví dụ trên cùng một doanh nghiệp.

Trên một hệ thống cho thuê xe đạp (Capital Bikeshare):

- **Descriptive** (chuyện gì đã xảy ra): lượt thuê 2012 là 2 049 576, tăng 64.9% so với 2011.
- **Diagnostic** (vì sao): ngày 29/10/2012 chỉ có 22 lượt; dữ liệu thời tiết cho thấy `weathersit = 3`,
  trùng ngày bão Sandy đổ bộ.
- **Predictive** (sẽ thế nào): dự báo lượt thuê tháng 12/2012 bằng tháng 12/2011 nhân tăng trưởng 11 tháng
  đầu năm ra 145 505, thực tế 123 713 (cao hơn 17.6%) vì tăng trưởng chậm lại cuối năm.
- **Prescriptive** (nên làm gì): chọn giờ bảo trì ít ảnh hưởng nhất; ngày làm việc vắng nhất lúc 3h sáng
  (khoảng 5 lượt/giờ).

Điểm cộng: nói rõ loại analytics do **câu hỏi** quyết định chứ không do công cụ, và phần lớn giá trị của DA
nằm ở descriptive và diagnostic làm đúng (so sánh công bằng, phân rã), không phải ở việc leo lên
prescriptive.

## Stakeholder nhắn: "Kéo giúp anh số khách hàng tháng này." Bạn làm gì trước khi viết SQL?

Hỏi lại để đóng khung, ngắn gọn, không biến thành thẩm vấn:

1. **Quyết định**: "Số này dùng cho việc gì?" (báo cáo tháng, đặt mục tiêu, đánh giá chiến dịch). Câu trả lời
   quyết định độ chính xác và so sánh cần có.
2. **Định nghĩa**: khách hàng là ai? Có tài khoản, có ít nhất một đơn hợp lệ, hay cả khách vãng lai? Đơn huỷ
   có tính không? Trên Online Retail II, khoảng 16.5% doanh thu không có `Customer ID`: đếm khách sẽ bỏ phần đó.
3. **So với gì**: tháng trước, cùng kỳ năm trước, kế hoạch?
4. **Phạm vi và thời hạn**: thị trường nào, "tháng này" là tháng lịch hay 30 ngày gần nhất, tháng chưa hết
   thì sao, cần khi nào.

Nếu stakeholder bận, đưa con số theo định nghĩa chuẩn của công ty, ghi rõ định nghĩa đó trong câu trả lời,
và hỏi một câu quan trọng nhất (thường là "dùng để quyết định gì"). Câu trả lời yếu: viết SQL ngay và gửi
một con số trần.

## KPI khác metric thế nào? Một KPI tốt cần những gì?

Metric là mọi thứ đo được; KPI là số ít metric được chọn để theo dõi việc đạt **mục tiêu**, có chủ sở hữu,
mục tiêu số và nhịp xem. Một KPI tốt:

- **Gắn với mục tiêu kinh doanh**: tăng nó thì công ty tốt hơn thật.
- **Hành động được**: team sở hữu nó tác động được. "Doanh thu toàn công ty" là KPI của CEO, không phải của
  team onboarding.
- **Định nghĩa một câu, tính một chỗ**: ai tính cũng ra cùng số.
- **Khó game**: không tăng được bằng cách làm hại khách hoặc dời số giữa các kỳ. "Số đơn" game được bằng
  giảm giá sâu, nên cần guardrail (biên lợi nhuận, tỉ lệ huỷ).
- **Có nhịp phù hợp**: số thay đổi chậm (churn năm) không nên xem hằng ngày.

Phản ví dụ: "số lượt xem trang" là vanity metric: tăng dễ, không chắc liên quan tới doanh thu.

## North star metric là gì? Đề xuất north star cho một cửa hàng quà tặng online bán sỉ lẫn lẻ.

North star là **một** con số thể hiện giá trị khách nhận được, mà khi tăng bền vững thì doanh thu dài hạn
tăng theo; nó định hướng mọi team. Nó đi kèm vài **input metric** (thành phần team tác động được) và
**guardrail** (không được xấu đi).

Với cửa hàng kiểu Online Retail II (nhiều khách sỉ là cửa hàng nhỏ ở châu Âu, đơn lặp lại):

- **North star**: số đơn hợp lệ của khách quay lại mỗi tháng. Khách sỉ quay lại là dấu hiệu sản phẩm và dịch
  vụ đủ tốt; doanh thu sỉ phụ thuộc vào lặp lại hơn là đơn đầu.
- **Input**: số khách mới có đơn đầu, tỉ lệ khách quay lại trong 90 ngày, số đơn mỗi khách quay lại, AOV.
- **Guardrail**: tỉ lệ đơn huỷ (dữ liệu có hoá đơn mã `C`), biên lợi nhuận gộp, tỉ lệ đơn giao trễ.

Vì sao không chọn doanh thu: doanh thu là kết quả đến chậm, tăng được ngắn hạn bằng tăng giá hoặc một đơn sỉ
lớn (một hoá đơn 168 470 GBP ngày 9/12/2011 làm lệch cả tháng), và không nói team nào cần làm gì.

## Leading và lagging indicator khác nhau thế nào? Cho ví dụ bạn đã kiểm một leading indicator thật sự dự báo được.

Lagging đo kết quả sau khi xảy ra (doanh thu tháng, churn quý): chính xác nhưng muộn. Leading thay đổi
trước và dự báo được kết quả (lượt thuê buổi sáng, số giỏ hàng hôm nay): sớm nhưng nhiễu, và **phải được
kiểm** rằng nó dự báo được.

Ví dụ trên Bike Sharing: lượt thuê trước 10h sáng làm chỉ số dẫn trước cho tổng lượt cả ngày. Gộp mọi ngày,
tương quan 0.79; tách theo loại ngày thì 0.94 (ngày làm việc) và 0.89 (cuối tuần), vì trước 10h chiếm 26.1%
lượt của ngày làm việc nhưng chỉ 13.7% của cuối tuần. Dự báo tổng ngày = lượt buổi sáng chia tỉ lệ đúng loại
ngày cho sai số tuyệt đối trung vị khoảng 9%; dùng một tỉ lệ chung cho mọi ngày thì khoảng 25%. Những ngày
dự báo sai nặng nhất là ngày bão (Irene 27/8/2011, Sandy 29/10/2012): buổi sáng bình thường rồi bão tới. Kết
luận: leading indicator phải kiểm theo phân khúc, và luôn có sự kiện mà nó không thấy trước.

## Vẽ metric tree cho doanh thu của một cửa hàng online. Dùng nó thế nào khi doanh thu thay đổi?

Doanh thu = doanh thu khách có mã + doanh thu không mã; doanh thu khách có mã = số khách × tần suất (đơn/khách)
× AOV (doanh thu/đơn). Dưới số khách: khách mới + khách quay lại; dưới AOV: số dòng mỗi đơn × giá trị mỗi dòng.

Khi doanh thu thay đổi, phân rã mức thay đổi thành đóng góp của từng nhánh. Với cây nhân, dùng phân rã log
(LMDI): đóng góp của thành phần X là

$$
L \ln\frac{X_1}{X_0}, \qquad L = \frac{R_1 - R_0}{\ln R_1 - \ln R_0}
$$

Các đóng góp cộng đúng bằng mức thay đổi và không phụ thuộc thứ tự. Trên Online Retail II, tháng 8 → 9/2011
doanh thu khách có mã tăng 307 494 GBP: 239 163 do thêm khách, 9 894 do tần suất, 58 438 do AOV. Câu cho
stakeholder: "78% mức tăng do thêm khách"; câu hỏi tiếp: khách mới hay khách cũ quay lại? Cây biến câu "vì sao"
thành chuỗi câu hỏi có thứ tự, và chỉ ra team nào sở hữu nhánh nào.

## Vì sao không phân rã bằng cách thay lần lượt từng thành phần?

Cách thay lần lượt (thay số khách kỳ 1 vào trước, giữ tần suất và AOV kỳ 0; rồi thay tần suất; rồi AOV) cộng
đúng tổng, nhưng **kết quả phụ thuộc thứ tự thay**: phần "tương tác" (cả số khách lẫn AOV cùng tăng) bị gán
cho thành phần thay sau. Khi các thành phần thay đổi lớn (như tháng 11 → 12/2011, số khách −63%, AOV +52%),
hai thứ tự cho hai câu chuyện khác nhau. LMDI chia phần tương tác theo trung bình log nên cân đối và không
phụ thuộc thứ tự. Một phương án khác chấp nhận được là Shapley (trung bình mọi thứ tự). Điều quan trọng
trong phỏng vấn: nêu được vấn đề thứ tự, và luôn kiểm tổng các đóng góp bằng mức thay đổi thật.

## Case: CEO nói "Doanh thu tháng 11 tăng 31% so với tháng 10, chiến dịch marketing tháng 11 hiệu quả quá." Bạn phản hồi thế nào?

Không phản bác ngay; tách **quan sát** khỏi **kết luận** rồi kiểm từng giả thuyết:

1. **Dữ liệu và lịch**: tháng 11 có bao nhiêu ngày bán so với tháng 10? Có đơn bị huỷ sau đó không?
2. **Mùa vụ**: tháng 11 năm trước so với tháng 10 năm trước tăng bao nhiêu? Quà tặng có mùa Giáng sinh, tăng
   tháng 11 là bình thường; câu hỏi là tăng **hơn mùa vụ** bao nhiêu.
3. **Metric tree**: tăng ở nhánh nào? Trên Online Retail II, tháng 10 → 11/2011 doanh thu gộp tăng 30.7%,
   nhưng doanh thu khách có mã chỉ tăng 11.8%; nhánh **không có Customer ID** tăng từ khoảng 116 nghìn lên 348
   nghìn GBP, trong đó hai hoá đơn không mã khoảng 51 và 53 nghìn GBP. Một phần lớn mức tăng là vài đơn lớn
   không gắn khách, khó quy cho chiến dịch nhắm khách.
4. **Nhân quả**: chiến dịch có nhóm đối chứng không? Không có thì chỉ nói được "tăng cùng lúc", không nói được
   "do chiến dịch". Đề xuất lần sau giữ lại một nhóm khách không nhận chiến dịch.

Câu trả lời cho CEO: "Doanh thu tháng 11 tăng 31%, nhưng khoảng hai phần ba mức tăng (232 trên 355 nghìn GBP)
đến từ đơn không gắn khách; phần có thể liên quan chiến dịch là số khách có mã tăng 22%, và phần đó vẫn lẫn với
mùa Giáng sinh. Để biết chắc, lần tới cần nhóm đối chứng."

## Case: Head of Operations của hệ thống xe đạp muốn "một dashboard về mọi thứ". Bạn làm gì?

"Dashboard về mọi thứ" là giải pháp, chưa phải vấn đề. Các bước:

1. **Hỏi quyết định**: họ quyết định gì hằng ngày, hằng tuần? (điều xe giữa các trạm, lịch bảo trì, số nhân
   viên ca). Mỗi quyết định cần số gì, lúc nào.
2. **Chọn 3–5 KPI** thay vì 40 metric: lượt thuê theo giờ so với cùng ngày tuần trước (lagging), lượt thuê
   trước 10h so với dự kiến (leading, để điều xe trong ngày), tỉ lệ xe hỏng (guardrail), thời gian xe trống ở
   trạm đông.
3. **Thiết kế cho nhịp dùng**: màn hình ca sáng có leading indicator và cảnh báo; màn hình tuần có xu hướng và
   so cùng kỳ; phần còn lại để self-serve.
4. **Thoả thuận phạm vi**: phiên bản đầu một tuần, xem họ dùng gì, bỏ gì.

Điểm cộng: nói được cái **không** đưa lên dashboard và vì sao (metric không ai hành động theo).

## Case: Một sản phẩm thương mại điện tử có số đơn tăng 10% nhưng doanh thu không đổi. Bạn điều tra thế nào?

Doanh thu = số đơn × AOV, nên AOV phải giảm khoảng 9% (1 / 1.1 − 1). Cây giả thuyết:

- **Dữ liệu**: định nghĩa "đơn" có đổi không (tách đơn thành nhiều đơn con, tính cả đơn huỷ)? Tiền tệ, thuế?
- **Mix**: thêm nhiều đơn nhỏ từ kênh mới, khách mới, danh mục rẻ? Phân rã AOV theo kênh và danh mục: AOV từng
  nhóm không đổi nhưng tỉ trọng nhóm rẻ tăng là hiệu ứng mix.
- **Giá**: khuyến mãi, giảm giá, miễn phí vận chuyển với ngưỡng thấp hơn?
- **Hành vi**: khách chia nhỏ đơn (ví dụ do ngưỡng miễn phí giao hàng thay đổi)?

Trước khi kết luận "tốt hay xấu", hỏi biên lợi nhuận: nhiều đơn nhỏ có thể làm chi phí giao hàng tăng và lợi
nhuận giảm dù doanh thu bằng. Đây là lý do metric tree nên có nhánh chi phí cạnh nhánh doanh thu khi bàn tới
quyết định.

## Khi nào bạn dùng Excel, khi nào SQL, khi nào Python cho một phân tích? Vì sao chọn công cụ đó?

Bốn câu hỏi quyết định: ai dùng kết quả và bao lâu một lần; dữ liệu ở đâu, lớn cỡ nào; có cần tái lập và
review không; công ty đang dùng gì.

- **SQL** khi dữ liệu nằm trong warehouse: tổng hợp ở sát dữ liệu, kéo về máy phần nhỏ đã tổng hợp. Gần như
  mọi phân tích bắt đầu ở đây.
- **Excel / Google Sheets** khi dữ liệu nhỏ, người nhận cần tự sửa số hoặc chạy kịch bản (team tài chính), và
  phân tích dùng một lần.
- **Python** khi làm sạch phức tạp, nhiều nguồn, thống kê hoặc cần tái lập (notebook trong git), hoặc cần
  phân rã như metric tree lặp lại hằng tháng.
- **BI** khi cùng câu hỏi được hỏi lại hằng tuần bởi nhiều người: chuyển từ ad-hoc sang dashboard.

Ví dụ trả lời "vì sao chọn": "Tôi làm phân rã doanh thu bằng Python chứ không bằng Excel vì nó chạy lại mỗi
tháng, cần review được, và dữ liệu 540 nghìn dòng; kết quả cuối tôi xuất ra một bảng nhỏ để team tài chính mở
bằng Excel."

## Diagnostic analytics: một KPI giảm 9% so với tháng trước. Quy trình của bạn?

1. **Kiểm dữ liệu và lịch trước**: số ngày trong kỳ, kỳ có đủ không, pipeline có lỗi, định nghĩa có đổi.
   Lượt thuê Bike Sharing tháng 10/2012 thấp hơn tháng 9 khoảng 9%, nhưng tháng 10 có 31 ngày, tháng 9 có 30:
   tính theo ngày thì mức giảm còn lớn hơn (khoảng 12%), nên số ngày không giải thích được.
2. **So với mùa vụ**: cùng chuyển tháng năm trước giảm bao nhiêu?
3. **Phân khúc**: phân khúc nào đóng góp nhiều nhất vào mức giảm (vãng lai hay thành viên)?
4. **Yếu tố ngoài**: thời tiết, ngày lễ, sự kiện (bão Sandy cuối tháng 10/2012).
5. **Ước phần giải thích được** của từng nhánh, ghi phần dư, kết luận đủ để quyết định.

Điểm then chốt: viết cây giả thuyết và ngưỡng kiểm **trước** khi nhìn dữ liệu, kiểm nhánh rẻ trước, và trình
bày theo thứ tự "kết luận → bằng chứng → giới hạn".

## Analysis plan gồm những gì? Khi nào cần viết?

Viết khi phân tích lớn hơn khoảng nửa ngày, có nhiều người liên quan, hoặc câu hỏi mơ hồ. Một trang:

- Bối cảnh và **quyết định** sẽ dùng kết quả.
- Câu hỏi đã đóng khung (metric, so với gì, phạm vi).
- Cây giả thuyết MECE, mỗi nhánh một con số kiểm.
- Định nghĩa metric, nguồn dữ liệu, giới hạn đã biết (kỳ chưa đủ, dữ liệu bị cắt đầu).
- Phương pháp, đầu ra, mốc thời gian, và **ngoài phạm vi**.

Giá trị lớn nhất không nằm ở tài liệu mà ở cuộc trao đổi: stakeholder đọc mười phút và nói "không, cái tôi
cần là X" trước khi bạn mất một tuần làm Y.

## Một phân tích của bạn ra kết quả ngược với điều sếp tin. Bạn trình bày thế nào?

- **Kiểm lại kỹ hơn bình thường** trước khi nói: định nghĩa, bộ lọc, kỳ, join có nhân bản dòng không. Kết quả
  bất ngờ thường là lỗi dữ liệu.
- **Bắt đầu từ điểm chung**: câu hỏi và định nghĩa metric mà cả hai đồng ý.
- **Trình bày bằng chứng theo thứ tự**: con số chính, so sánh công bằng, phân rã, rồi các cách giải thích khác
  đã loại trừ.
- **Nói rõ mức chắc chắn và giới hạn**; đề xuất cách kiểm tiếp (thí nghiệm, dữ liệu thêm) thay vì tranh luận.
- **Tách người khỏi vấn đề**: "dữ liệu cho thấy" chứ không "anh sai".

Người phỏng vấn đánh giá sự trung thực và khả năng giữ quan điểm có bằng chứng mà không đối đầu.

## Bạn phân biệt thế nào giữa tương quan và nhân quả khi báo cáo cho stakeholder?

Tương quan: hai thứ thay đổi cùng nhau. Nhân quả: thay đổi A **làm** B thay đổi. Ba lý do tương quan không phải
nhân quả: biến gây nhiễu (mùa vụ làm cả nhiệt độ và lượt thuê cùng tăng), nhân quả ngược (doanh thu cao nên
được chi nhiều quảng cáo hơn), và chọn mẫu (chỉ nhìn khách còn ở lại).

Khi báo cáo: dùng từ đúng ("tăng cùng lúc với", "liên quan tới") cho dữ liệu quan sát; muốn nói nhân quả thì cần
thí nghiệm (A/B, nhóm đối chứng) hoặc thiết kế quan sát chặt (difference-in-differences, module 11). Và nói rõ
quyết định có cần nhân quả không: điều xe theo dự báo chỉ cần dự báo tốt, không cần biết vì sao.

## Bạn ưu tiên thế nào khi nhận năm yêu cầu phân tích cùng lúc?

Xếp theo **tác động lên quyết định × độ gấp / công sức**:

- Hỏi mỗi yêu cầu phục vụ quyết định gì, giá trị quyết định đó lớn cỡ nào, hạn khi nào.
- Việc nhỏ có tác động lớn làm ngay; việc lớn tác động lớn lên kế hoạch; việc nhỏ tác động nhỏ gom lại hoặc
  chuyển thành self-serve (hướng dẫn họ dùng dashboard); việc lớn tác động nhỏ thì thương lượng phạm vi hoặc
  từ chối có lý do.
- Minh bạch: gửi danh sách ưu tiên cho các stakeholder (hoặc quản lý) thay vì âm thầm làm theo người hỏi to
  nhất.

Một DA senior biết nói "không" hoặc "chưa" kèm lý do và phương án thay thế.
