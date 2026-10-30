# Câu hỏi phỏng vấn: Product & customer analytics

## Funnel của bạn đếm theo visitor hay theo phiên? Khi nào dùng cái nào?

Hai đơn vị trả lời hai câu hỏi khác nhau:

- **Theo visitor (user)**: "trong số người đã xem, bao nhiêu người cuối cùng mua". Dùng cho câu hỏi về **người**:
  chiến dịch acquisition có đem về người mua không, tỉ lệ người dùng mới thành khách hàng.
- **Theo phiên**: "một lượt ghé có dẫn tới mua không". Dùng cho câu hỏi về **trải nghiệm trong một lần dùng**:
  trang checkout mới có giúp hoàn tất đơn trong cùng lượt không.

Trên Retailrocket, funnel có thứ tự theo visitor là 1 404 179 → 32 934 → 9 952, theo phiên 30 phút là
1 755 781 → 36 677 → 10 722. Người mua sau nhiều lượt ghé được tính là chuyển đổi theo visitor nhưng lượt ghé đầu
của họ là "không chuyển đổi" theo phiên. Ứng viên senior nói thêm: phiên do mình tự chia (30 phút không hoạt động)
là một quy ước; nếu được thì nhờ engineering sinh `session_id` ở client và ghi vào tracking plan.

## Conversion window là gì? Chọn 1 ngày, 7 ngày hay 30 ngày thế nào?

Conversion window là khoảng thời gian tối đa từ bước đầu tới bước cuối để được tính là chuyển đổi. Không có cửa
sổ thì người vào đầu kỳ có nhiều thời gian để mua hơn người vào cuối kỳ, và tỉ lệ theo tuần giảm dần về cuối dù
không có gì thay đổi.

Chọn bằng **phân phối thời gian tới khi chuyển đổi**, rồi cân với nhu cầu đọc số. Trên Retailrocket, trung vị từ lần
xem đầu tới lần mua đầu là 0.4 giờ nhưng phân vị 90 là 220 giờ; cửa sổ 7 ngày giữ 88.6% người mua, 30 ngày giữ
95.3%. Cửa sổ dài đầy đủ hơn nhưng số của một tuần phải chờ lâu hơn mới "chín". Với PM đọc số hằng tuần, 7 ngày
là hợp lý; với báo cáo quý, 30 ngày. Dù chọn gì, tuần chưa đủ cửa sổ không được đặt cạnh tuần đã chín.

## Bạn đọc một cohort retention heatmap thế nào?

Ba hướng:

1. **Theo hàng**: một cohort già đi thế nào. Cú rơi lớn ở tháng 1 rồi đi ngang là có nhóm khách lõi; tiếp tục rơi
   đều là sản phẩm chưa có giá trị lặp lại.
2. **Theo cột**: cùng tuổi, khác cohort. Đây là câu hỏi "chất lượng khách mới đang tốt lên hay xấu đi". Phải so cùng
   tháng năm trước khi có mùa vụ: trên Online Retail II, m1 của cohort 04/2011 là 25.5% so với 19.4% của 04/2010.
3. **Theo đường chéo**: cùng tháng lịch. Mọi cohort cùng sáng ở tháng 9-11 và tối ở tháng 12-2 là mùa vụ của khách
   sỉ, không phải chất lượng cohort. Sự cố tracking hay chiến dịch lớn cũng hiện thành một đường chéo.

Thêm hai chi tiết: ô chưa quan sát được để trống (khác 0), và bỏ cột k = 0 khỏi thang màu.

## Retention "bracket" và "unbounded" khác nhau thế nào? Khi nào dùng loại nào?

**Bracket (classic)**: tỉ lệ khách có hoạt động **trong** tháng k. **Unbounded**: tỉ lệ khách có hoạt động ở tháng k
**hoặc bất kỳ lúc nào sau đó**. Unbounded luôn cao hơn và không bao giờ tăng theo k; trên Online Retail II, cohort
01/2010 có bracket m1 20.6% nhưng unbounded m1 87.0%: phần lớn khách vẫn quay lại, chỉ không phải đúng tháng sau.

Bracket hợp với sản phẩm dùng đều đặn (app, thuê bao); unbounded hợp với sản phẩm mua thưa (khách sỉ đặt theo quý,
du lịch) và trả lời "bao nhiêu khách chưa bỏ hẳn". Bẫy của unbounded: con số của cohort gần đây **tăng lên khi có
thêm dữ liệu** (khách chưa kịp quay lại), nên không được so cohort mới với cohort cũ ở cùng k mà không cắt cùng
khoảng quan sát.

## Đường retention trung bình đi lên ở cuối. Bạn giải thích thế nào?

Gần như luôn là ảo giác, có hai nguyên nhân hay gặp:

- **Ít cohort phía sau các điểm cuối**: điểm k lớn chỉ có các cohort sớm nhất. Trên Online Retail II, điểm k = 23
  (40.7%) chỉ có một cohort.
- **Cohort đầu bị cắt trái**: dữ liệu bắt đầu 12/2009 nên cohort 12/2009 chứa cả khách lâu năm, giữ chân tốt hơn hẳn
  khách mới thật.

Cách trình bày: trung bình có trọng số theo cỡ cohort, ghi số cohort dưới mỗi điểm, cắt đường khi dưới 3 cohort,
và cân nhắc bỏ cohort cắt trái.

## LTV đơn giản tính thế nào, và vì sao nó thường lạc quan?

Công thức hay dùng: LTV bằng doanh thu năm mỗi khách nhân biên lợi nhuận gộp, chia cho (1 trừ retention năm). Nó
lạc quan vì ba giả định:

- Retention năm thường đo trên **toàn bộ khách**, chứa nhiều khách lâu năm đã "sống sót", trong khi khách mới rời
  đi nhanh hơn nhiều.
- Retention được coi là **không đổi theo tuổi**, trong khi đường thật rơi mạnh ở tháng đầu.
- Trung bình bị **khách lớn** kéo.

Trên Online Retail II, công thức cho khoảng 1 878 GBP lợi nhuận gộp (biên 35% là giả định), còn khách mới 2010 chỉ có
trung bình 1 449 GBP doanh thu, trung vị 708 GBP trong 12 tháng đầu. Cách đáng tin hơn là **LTV theo cohort**:
doanh thu luỹ kế mỗi khách theo tuổi, đọc thẳng từ dữ liệu, chỉ ngoại suy phần chưa quan sát và ghi rõ đó là ngoại
suy.

## CAC payback là gì? Không có số chi phí marketing thì bạn trả lời "được chi bao nhiêu" thế nào?

CAC là chi phí để có một khách mới; payback là số tháng tới khi lợi nhuận gộp luỹ kế của khách đó bằng CAC. Không
có chi phí thì **lật câu hỏi**: từ đường LTV theo cohort và biên lợi nhuận, tính CAC tối đa để hoàn vốn trong 6 hay
12 tháng, rồi để tài chính và marketing so với chi phí thật. Mọi số giả định (biên, CAC thử) ghi rõ là giả định,
và đưa ra dạng bảng kịch bản để người nhận tự thay số.

Thêm: CAC gộp (blended) trộn khách tự nhiên với khách từ quảng cáo; quyết định chi thêm cho một kênh cần CAC biên
của kênh và LTV của khách đến từ kênh đó. Ngưỡng LTV/CAC khoảng 3 là quy ước phổ biến của SaaS, không phải định luật;
công ty ít tiền mặt quan tâm payback ngắn hơn là tỉ lệ.

## RFM là gì? Bạn chấm điểm bằng quintile hay ngưỡng cố định?

RFM mô tả khách bằng Recency (bao lâu từ lần mua cuối), Frequency (số đơn), Monetary (số tiền) tại một ngày chốt,
đổi mỗi chiều thành điểm 1-5 rồi gom thành segment có tên.

- **Quintile** cân bằng 20% mỗi mức, hợp với Monetary lệch phải, nhưng ngưỡng đổi mỗi lần chạy (khách không đổi hành
  vi vẫn đổi segment) và chia ngẫu nhiên khi nhiều khách cùng giá trị: trên Online Retail II, 1 493 trong 4 338 khách
  có đúng 1 đơn.
- **Ngưỡng nghiệp vụ** (mua trong 14 ngày, từ 10 đơn) ổn định, giải thích được cho đội CRM, nhưng phải chọn theo
  nhịp mua.

Thực tế hay trộn: ngưỡng cho R và F, quintile cho M.

## RFM cho bạn segment rồi, tiếp theo là gì?

Segment chỉ có giá trị khi gắn với **hành động và cách đo**. Mỗi segment có một mục tiêu (giữ, bán thêm, đơn thứ
hai, win-back, bỏ qua) và một metric (retention, giá trị đơn, tỉ lệ quay lại 60 ngày). Trên Online Retail II,
champions là 11.7% khách nhưng 46.8% doanh thu: không gửi mã giảm giá đại trà cho họ, vì họ sẽ mua dù sao. Nhóm
at risk có M cao thì gọi điện. Cuối cùng, mọi chiến dịch theo segment cần **nhóm đối chứng** giữ lại, vì "khách at
risk quay lại sau email" có thể là khách tự quay lại.

## Giải thích support, confidence, lift. Luật nào bạn sẽ đưa cho merchandiser?

Với luật A ⇒ B: support là tỉ lệ giỏ có cả A và B; confidence là tỉ lệ giỏ có B trong số giỏ có A; lift là
confidence chia cho tỉ lệ giỏ có B. Lift 1 là độc lập, trên 1 là hay đi cùng, dưới 1 là ít đi cùng hơn ngẫu nhiên.

Không đưa luật theo confidence: B phổ biến thì confidence cao dù không có quan hệ gì. Không đưa thẳng luật lift cao
nhất: trên Online Retail II, luật lift cao nhất là các màu khác nhau của cùng một tách trà (lift 16), khách sỉ vốn
mua đủ bộ, nên hành động là bán theo bộ, không phải gợi ý chéo. Ưu tiên luật có support đủ lớn (ảnh hưởng doanh thu
thật), lift rõ, ổn định qua các mùa, và đưa kèm đề xuất thử nghiệm A/B để đo doanh thu tăng thêm.

## Vì sao luật market basket không chứng minh "gợi ý B cho người mua A sẽ tăng doanh thu"?

Luật là **tương quan trong dữ liệu quá khứ**. Người mua A có thể đã định mua B (gợi ý chỉ "nhận công" doanh thu sẵn
có), hoặc B được bày cạnh A trong catalogue nên đi cùng nhau. Muốn biết tác động phải thử nghiệm: chia ngẫu nhiên
người xem A thành nhóm thấy gợi ý và không thấy, đo doanh thu mỗi người (metric chính) và tỉ lệ thêm giỏ B, kèm
guardrail như giá trị đơn và tỉ lệ bỏ giỏ.

## Bạn được giao làm tracking plan cho một tính năng mới. Bạn làm gì?

1. Bắt đầu từ **câu hỏi và metric**: tính năng thành công nghĩa là gì (metric chính, guardrail), cần chia theo gì.
2. Liệt kê **sự kiện** tối thiểu để tính các metric đó, đặt tên theo quy ước `object_action` quá khứ
   (`recommendation_shown`, `recommendation_clicked`), mỗi sự kiện có trigger rõ (khi API trả thành công, không phải
   khi bấm).
3. **Thuộc tính** với kiểu, bắt buộc hay không, enum giá trị; định danh (`anonymous_id`, `user_id`, `session_id`),
   thời điểm UTC; không có dữ liệu cá nhân.
4. Owner, phiên bản, trạng thái cho từng sự kiện.
5. **QA trước khi ra mắt**: so log trên staging với plan bằng script tự động; sửa tracking sau ra mắt là mất dữ liệu
   những tuần đầu.

## Số trên Amplitude khác số trên warehouse. Bạn xử lý thế nào? Nên dùng công cụ nào?

Trước hết tìm vì sao lệch, theo thứ tự hay gặp: định nghĩa user khác (anonymous vs đăng nhập, merge identity),
múi giờ, lọc bot và nội bộ, sự kiện trùng hoặc gửi lại, cửa sổ chuyển đổi và thứ tự bước, dữ liệu đến muộn. Chọn
một mẫu nhỏ (một ngày, vài user) để đối chiếu từng sự kiện.

Về vai trò công cụ: **product analytics tool** (Amplitude, Mixpanel, PostHog) cho PM tự trả lời nhanh funnel,
retention, path; **warehouse + SQL/dbt** là nơi của con số chính thức, vì nó nối được sự kiện với đơn hàng, hoàn
tiền, chi phí, CRM và có định nghĩa kiểm được. GA4 hợp cho đo nguồn traffic và chiến dịch website. Khi lệch, số báo
cáo là số warehouse, và định nghĩa metric được ghi ở một chỗ để công cụ kia cấu hình theo.

## Case: Tỉ lệ chuyển đổi tuần này giảm từ 0.7% xuống 0.5%. PM hỏi chuyện gì xảy ra.

Đi theo thứ tự:

1. **Con số có so được không**: tuần này đã đủ cửa sổ chuyển đổi chưa? Trên Retailrocket, tuần cuối dữ liệu có buy
   rate 7 ngày 0.49%, thấp nhất bảng, chỉ vì chưa chín. Đủ ngày chưa, tracking có sự cố không (số sự kiện theo giờ,
   theo nền tảng, theo phiên bản app).
2. **Mẫu số hay tử số**: số người xem tăng đột biến (traffic chất lượng thấp từ một chiến dịch) hay số người mua giảm.
3. **Bước nào**: tách funnel xem → giỏ → mua; bước rơi cho biết đội nào cần xem.
4. **Phân khúc**: nguồn traffic, thiết bị, sản phẩm. Funnel theo sản phẩm có thể cho thấy vài sản phẩm nhiều người
   xem nhưng không ai thêm giỏ (hết hàng, lỗi trang).
5. **So với dải bình thường**: 19 tuần chín dao động 0.48-0.79%; một tuần 0.5% có thể nằm trong dao động.

Trả lời PM bằng kết luận trước ("chưa phải giảm thật vì...", hoặc "giảm ở bước giỏ → mua, tập trung ở mobile"), kèm
việc cần làm.

## Case: Head of CRM muốn gửi mã giảm 20% cho mọi khách "at risk". Bạn góp ý gì?

- **Ai thực sự at risk**: kiểm định nghĩa (bao nhiêu ngày không mua so với nhịp mua bình thường của khách đó). Khách sỉ
  đặt theo quý trông như "at risk" sau 90 ngày mà không phải.
- **Giá trị**: ưu tiên theo giá trị thu hồi được (M cao, cant lose); trên Online Retail II, 142 trong 278 khách at risk
  có điểm M từ 4.
- **Chi phí của giảm giá**: khách tự quay lại cũng nhận 20%; với nhóm giá trị cao, một cuộc gọi có thể hiệu quả hơn.
- **Đo được**: giữ 10-20% nhóm làm đối chứng ngẫu nhiên, metric chính là doanh thu ròng sau giảm giá mỗi khách trong
  60-90 ngày, guardrail là biên lợi nhuận.

## Case: CEO muốn biết khách mới năm nay có "tốt" như năm ngoái không.

Định nghĩa "tốt" bằng hai chiều đo được: **giữ chân** (retention m1, m3 theo cohort) và **giá trị** (doanh thu luỹ
kế mỗi khách sau 3, 6 tháng). So **cohort cùng tháng năm trước** để trừ mùa vụ, ở cùng tuổi đã quan sát được (cohort
gần đây chưa có m6). Báo cỡ cohort bên cạnh: trên Online Retail II, từ cohort tháng 4 tới tháng 10, m1 của 2011 cao hơn
cùng tháng 2010 ở cả 7 cặp (04: 25.5% so với 19.4%; 07: 21.6% so với 15.6%), nhưng cohort tháng 1-3/2011 thấp hơn, và
mọi cohort 2011 nhỏ hơn nhiều (106 so với 294 khách ở tháng 4). Câu trả lời đầy đủ là "từ quý 2, khách mới ít hơn
nhưng giữ chân tốt hơn; quý 1 thì kém hơn", kèm câu hỏi tiếp theo cho marketing: vì sao số khách mới giảm (thị
trường đã bão hoà hay ngân sách acquisition giảm).
