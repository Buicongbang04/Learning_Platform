# Câu hỏi phỏng vấn: Stakeholder, storytelling & phỏng vấn

## Trưởng phòng kinh doanh nhắn: "Kéo cho anh doanh thu theo nước". Bạn làm gì trước khi viết query?

Tìm quyết định phía sau câu nói, rồi trả lời kèm một bản nháp phạm vi thay vì hỏi năm câu mở. Ví dụ:

> "Dạ, anh cần số này để quyết định ưu tiên thị trường cho năm sau đúng không ạ? Em định lấy 12 tháng đủ
> (12/2010-11/2011), doanh thu gộp bỏ hoá đơn huỷ, so với cùng kỳ năm trước, kèm số khách mỗi nước. Em gửi
> bảng trước 3 giờ chiều nay, được không ạ?"

Câu trả lời đó làm bốn việc: đoán quyết định (để người hỏi xác nhận hoặc sửa), chốt định nghĩa (doanh thu gộp
hay ròng, có tính tháng đang chạy không), chọn tham chiếu (một con số không có "so với gì" không dẫn tới hành
động), và hẹn mốc. Nếu anh ấy trả lời "không, anh chỉ cần dán vào slide họp tuần", effort giảm còn mười phút
và có thể chỉ cần gửi link dashboard có sẵn.

Câu hỏi mạnh nhất để thêm khi yêu cầu lớn: "Nếu kết quả là X, anh sẽ làm gì khác?" Nếu mọi kết quả dẫn tới
cùng một hành động, phân tích lớn là không cần thiết.

Điều không nên làm: hỏi những câu đẩy việc kỹ thuật sang người hỏi ("anh muốn join bảng nào?"), hoặc im lặng
làm ba ngày rồi gửi một bảng 40 nước không ai đọc.

## Bạn có năm yêu cầu từ ba phòng ban cùng một tuần. Bạn ưu tiên thế nào?

1. **Phân loại** trước: cái nào đã có trên dashboard (self-serve: gửi link, năm phút), cái nào chưa rõ quyết
   định (hỏi lại), cái nào lặp lại (ticket dựng dashboard), cái nào lớn hơn nửa ngày (dự án, cần analysis plan).
2. **Chấm impact và effort** cho phần còn lại. Impact là quyết định phía sau lớn cỡ nào (tiền, số người ảnh
   hưởng, có đảo ngược được không); effort là giờ tới bản đủ để quyết định. Quick win (impact cao, effort thấp)
   làm trước; big bet chia mốc; money pit đề xuất cách rẻ hơn.
3. **Xếp lịch theo năng lực** thật (một tuần không phải 40 giờ phân tích; họp, review, hỗ trợ chiếm phần đáng kể).
4. **Báo cho người chờ**: khi nào có và vì sao. Người chờ chấp nhận "thứ Sáu" dễ hơn chấp nhận im lặng.
5. Khi hai yêu cầu quan trọng xung đột, **không tự quyết**: đưa cho người nắm ưu tiên chung (trưởng nhóm, PM)
   với chi phí cơ hội rõ ràng.

Ứng viên senior nói thêm điều kiện thất bại của cách chấm: impact do chính người hỏi tự khai thường bị thổi
phồng, nên hỏi "nếu kết quả là X thì anh làm gì khác" để kiểm, và chia đôi impact khi không chắc.

## Khi nào bạn nói "không" (hoặc "chưa") với một yêu cầu? Nói thế nào?

Nói "không" hoặc "chưa" khi:

- Không có quyết định nào phụ thuộc kết quả, và người hỏi không đưa được ra.
- Câu trả lời đã có ở dashboard / báo cáo chính thức (khi đó là "đã có, ở đây").
- Dữ liệu không thể trả lời câu hỏi (ví dụ hỏi nhân quả từ dữ liệu quan sát không có biến đối chứng), hoặc
  chi phí quá lớn so với giá trị (money pit).
- Nhận thêm sẽ làm trễ một việc ưu tiên cao hơn đã cam kết.

Cách nói: không bao giờ chỉ "không". Nói lý do bằng ngôn ngữ của người hỏi và đưa phương án thay thế:

> "Phân tích theo từng cửa hàng mất khoảng 3 ngày vì phải ghép dữ liệu POS cũ. Nếu mục tiêu là chọn 5 cửa
> hàng để thí điểm, em có thể dùng bảng tổng hợp theo vùng có sẵn và gửi trong hôm nay. Anh thấy đủ không?"

Với xung đột ưu tiên: "Em đang làm phân tích giá cho chị B, hạn thứ Năm. Việc của anh cần một ngày: em làm
từ thứ Sáu, hoặc anh trao đổi với chị B nếu cần sớm hơn."

## Khi nào nên dựng dashboard self-serve, khi nào trả lời ad-hoc một lần?

| Tín hiệu | Ad-hoc | Dashboard / báo cáo định kỳ |
| --- | --- | --- |
| Tần suất câu hỏi | Một lần | Lặp lại (cùng câu ≥ 2 lần, "tuần nào cũng cần") |
| Người dùng | Một người, một quyết định | Nhiều người, theo dõi liên tục |
| Định nghĩa metric | Có thể đặc thù cho câu hỏi | Phải ổn định, đã thống nhất |
| Chi phí | Vài giờ | Vài ngày dựng + bảo trì mãi mãi |

Quy tắc thực dụng: câu ad-hoc thứ hai giống câu thứ nhất là ticket dựng dashboard. Ngược lại, dashboard cho
câu hỏi một lần là nợ: không ai mở lần hai, nhưng nó vẫn chạy, vẫn có thể sai, và người khác tìm thấy và
dùng sai ngữ cảnh.

Self-serve không miễn phí: cần metric có một định nghĩa (semantic layer, module 09), hướng dẫn dùng, quyền
truy cập đúng, và office hours để người dùng hỏi cách dùng. Không có những thứ đó, "self-serve" thành mười
phiên bản doanh thu khác nhau trong mười file Excel.

## Headline tốt cho một slide trông thế nào? Sửa giúp tiêu đề "Doanh thu theo tháng".

Headline là câu người đọc nhớ nếu chỉ đọc một dòng: **kết luận có con số và tham chiếu**, không phải nhãn.
Trên Online Retail II, tháng 11/2011:

| Bậc | Headline |
| --- | --- |
| Nhãn | Doanh thu theo tháng |
| Quan sát | Doanh thu tháng 11 đạt 1.51 triệu GBP |
| So sánh | Doanh thu tháng 11 tăng 31% so với tháng 10, cao nhất năm |
| Insight | Tháng 11 tăng 31% nhờ số đơn (+36%); giá trị mỗi đơn còn giảm 4% |
| Khuyến nghị | Cao điểm đến từ số đơn chứ không từ đơn lớn hơn: tăng năng lực xử lý đơn trước tháng 9 |

(Tháng 10: 1 154 979 GBP, 2 040 hoá đơn, AOV 566; tháng 11: 1 509 496 GBP, 2 769 hoá đơn, AOV 545.)

Ba lỗi hay gặp: headline nói điều chart không chứng minh (nhân quả từ tương quan); số trong headline không khớp
số trên chart (làm tròn khác, kỳ khác); và tính từ thay cho số ("tăng mạnh", "đáng báo động"). Cách tự kiểm:
đọc ngang tiêu đề mọi slide; nếu chúng tạo thành một đoạn lý lẽ, deck đã ổn.

## Memo một trang gồm những gì? Vì sao kết luận phải ở đầu?

Cấu trúc tôi dùng:

1. **Headline**: kết luận + con số (một câu).
2. **Bối cảnh và câu hỏi** (S, C, Q của SCQA trong 2-3 câu): điều mọi người đã biết, điều thay đổi, câu hỏi
   cần trả lời.
3. **Khuyến nghị**: làm gì, ai làm, khi nào.
4. **Bằng chứng**: 3 ý, mỗi ý một con số (và một chart hoặc bảng nếu cần).
5. **Giới hạn**: điều dữ liệu không nói, điều là tương quan chứ chưa phải nhân quả, điều cần kiểm tiếp.
6. **Bước tiếp theo**: ai, việc gì, trước ngày nào.

Kết luận ở đầu vì người đọc bận dừng ở câu đầu: họ cần biết ngay có phải hành động không. Kể theo thứ tự đã
làm ("đầu tiên em làm sạch dữ liệu, sau đó...") buộc họ đọc hết để tìm câu trả lời, và thường họ không đọc hết.
Kết luận ở đầu còn có lợi cho chính DA: nó buộc bạn **có** một kết luận và cho người đọc thứ cụ thể để phản bác.

## Stakeholder nói "số của bạn sai, dashboard của tôi khác". Bạn xử lý thế nào?

Coi đó là thông tin, không phải tấn công. Các bước:

1. **Cảm ơn và hỏi cụ thể**: số nào, dashboard nào, kỳ nào, bộ lọc gì. Chụp lại màn hình của họ.
2. **Đối soát định nghĩa** trước khi nghi code: doanh thu gộp hay ròng (trừ đơn huỷ), theo ngày đặt hay ngày
   giao, múi giờ, có tính kỳ chưa đủ không, khách không có mã có tính không. Phần lớn chênh lệch đến từ đây.
3. **Dựng bảng cầu nối** (bridge): từ số A tới số B qua từng khác biệt định nghĩa, cộng lại khớp.
4. **Nếu bạn sai, nói sớm và rõ**: số đúng, ảnh hưởng tới kết luận (thường kết luận không đổi), và đã sửa gì để
   không lặp lại. Uy tín mất vì giấu lỗi, không mất vì lỗi được sửa nhanh.
5. **Sửa gốc**: nếu hai định nghĩa cùng tồn tại, đưa lên để chốt một định nghĩa chính thức (metric layer).

## Kết quả phân tích ngược với điều giám đốc đang tin. Bạn trình bày thế nào?

- **Kiểm kỹ hơn bình thường** trước khi trình bày: kết quả bất ngờ có xác suất sai cao hơn. Loại các nhánh
  dữ liệu (kỳ chưa đủ, định nghĩa, join nhân dòng) và thử một cách tính độc lập.
- **Pre-wire**: gặp riêng người đó trước buổi họp lớn. Không ai thích bị bất ngờ trước mặt cấp trên; phản biện
  của họ có thể chỉ ra điều bạn bỏ sót.
- **Bắt đầu từ điểm chung**: mục tiêu chung (tăng doanh thu, giữ khách), rồi bằng chứng, rồi kết luận.
- **Tách điều chắc và điều chưa chắc**: "Dữ liệu cho thấy X với mức chắc chắn này; điều này không loại trừ Y;
  cách rẻ nhất để biết chắc là một thử nghiệm 4 tuần."
- **Đề xuất bước tiếp theo** để họ có lối ra không mất mặt: thử nghiệm nhỏ, thêm dữ liệu, mốc xem lại.

Điều không làm: làm mềm số cho dễ nghe, hoặc chọn khung thời gian/cách chia để kết quả hợp ý.

## Bạn dùng AI/LLM trong phân tích thế nào? Làm sao chắc số đúng?

Tôi dùng LLM cho những việc **kiểm được nhanh**: viết nháp SQL/pandas, giải thích code người khác viết,
brainstorm giả thuyết và câu hỏi làm rõ, viết lại memo cho gọn. Tôi không dùng nó để **tự đọc dữ liệu và
đưa ra con số** hoặc kết luận nhân quả.

Nguyên tắc: mọi con số trong sản phẩm cuối truy được về một query hoặc cell tôi đã chạy. Kiểm code AI viết theo
danh sách: grain của kết quả (một dòng là gì), đối soát tổng, định nghĩa và bộ lọc, mã cột theo data dictionary,
đơn vị, chạy trên một ví dụ nhỏ biết trước đáp án.

Ví dụ thật: nhờ viết "AOV" và nhận `AVG(Quantity * Price)` trên bảng dòng sản phẩm. Trên Online Retail II nó
ra 20.12 GBP; AOV thật (trung bình trên hoá đơn) là 534.40 GBP, gấp 26.6 lần. Query chạy, số trông hợp lý, và
sai ở grain. Một lỗi khác hay gặp: LLM hiểu `weekday = 0` là thứ Hai hoặc `season = 1` là mùa xuân theo "lẽ
thường" mà không đọc data dictionary.

## Dữ liệu nào bạn không dán vào ChatGPT? Nếu bắt buộc cần AI trên dữ liệu khách hàng thì sao?

Không dán khi chưa được phép:

- **Dữ liệu cá nhân**: tên, email, số điện thoại, địa chỉ, mã khách gắn được với người thật. Ở Việt Nam, tính tới
  10/2026: Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 và Nghị định 356/2025/NĐ-CP hướng dẫn luật (cùng hiệu lực
  01/01/2026, nghị định thay Nghị định 13/2023/NĐ-CP); EU có GDPR. Đây là kiến thức tham khảo, không phải tư vấn pháp
  lý: kiểm văn bản hiện hành và hỏi pháp chế.
- **Dữ liệu kinh doanh nhạy cảm**: doanh thu chưa công bố, giá vốn, hợp đồng, kế hoạch.
- **Bí mật kỹ thuật**: chuỗi kết nối, API key, mật khẩu.

Khi cần AI trên dữ liệu đó, theo thứ tự: gửi **schema và mô tả cột** thay dữ liệu (đủ cho việc viết SQL); gửi
**bảng tổng hợp** thay từng dòng; **pseudonymize** hoặc bỏ cột định danh; dùng công cụ **đã được công ty duyệt**
(bản enterprise có cam kết không train trên dữ liệu, có hợp đồng xử lý dữ liệu) hoặc **model chạy cục bộ**. Và
hỏi chính sách trước, không phải sau.

## Vì sao bạn chọn công cụ này để giao kết quả: slide, memo, notebook HTML hay dashboard?

Tôi chọn theo câu hỏi, người đọc và tần suất, không theo thói quen:

| Công cụ | Chọn khi | Không chọn khi |
| --- | --- | --- |
| Memo trên Google Docs / Word / Notion | Một quyết định cần đọc kỹ, gửi trước họp, người đọc cần bình luận từng câu | Cần thảo luận trực tiếp với nhiều người |
| Slide (PowerPoint, Google Slides) | Trình bày trực tiếp, nhiều bên, cần dẫn dắt thảo luận | Gửi đi đọc một mình: slide không có người nói thường thiếu ngữ cảnh |
| Notebook xuất HTML / Quarto | Người đọc là DA/DS khác, cần thấy cách làm và tái lập | Người đọc là lãnh đạo không kỹ thuật |
| Dashboard BI (Power BI, Tableau, Metabase) | Câu hỏi lặp lại, nhiều người theo dõi | Câu hỏi một lần |
| Tin nhắn Slack/Teams | Ad-hoc, một con số kèm một câu | Kết luận có nhiều điều kiện, cần lưu lại |

Ví dụ: kết quả "nên cắt SKU nào" cho Head of Merchandising → memo một trang (quyết định lớn, cần đọc kỹ, có
giới hạn quan trọng), phụ lục là bảng SKU trong Google Sheets để họ lọc. Không dựng dashboard vì câu hỏi một lần
mỗi năm. Hệ sinh thái công ty cũng quyết định: công ty dùng Microsoft 365 thì Word/PowerPoint, chia sẻ trong
Teams; công ty dùng Google Workspace thì Docs/Slides.

## Bạn tiếp cận một câu SQL live trong phỏng vấn thế nào?

1. **Hỏi lại** grain và định nghĩa: một dòng của bảng là gì, đơn huỷ tính không, "khách mới" định nghĩa thế
   nào, múi giờ.
2. **Nhìn dữ liệu**: `SELECT * ... LIMIT 5`, đếm dòng, xem NULL ở cột quan trọng.
3. **Nói to kế hoạch** trước khi gõ: "gom về hoá đơn trước, rồi gom theo thứ".
4. **Viết từng bước bằng CTE**, đặt tên theo grain (`inv`, `customer_month`), chạy từng CTE.
5. **Tự kiểm**: tổng các nhóm bằng tổng chung, số dòng hợp lý, giá trị lạ.
6. **Nói điều nhận thấy**: "Online Retail II không có hoá đơn thứ Bảy nào; bảng chỉ có sáu ngày. Đó là sự thật
   vận hành, không phải lỗi query."

Ví dụ câu "ngày nào trong tuần có AOV cao nhất" trên Online Retail II: thứ Ba 613.01 GBP (3 554 hoá đơn), Chủ
nhật thấp nhất 369.25 GBP; tổng 19 960 hoá đơn khớp đối soát. Nếu bí: nói cách làm bằng lời và viết phần chắc
chắn trước. Người phỏng vấn chấm quy trình và khả năng tự phát hiện lỗi nhiều hơn tốc độ gõ.

## Đề take-home cho 3 giờ. Bạn phân bổ thời gian thế nào và nộp gì?

| Thời gian | Việc |
| --- | --- |
| 15 phút | Đọc đề, viết lại câu hỏi và quyết định; liệt kê giả định cho chỗ mơ hồ |
| 30 phút | Nhìn dữ liệu, kiểm chất lượng (huỷ, NULL, kỳ chưa đủ, mã lạ), chốt định nghĩa |
| 75 phút | Phân tích chính: một câu hỏi làm sâu, không năm câu làm nông |
| 30 phút | Viết trang tóm tắt: kết luận, 3 con số, khuyến nghị, giới hạn |
| 15 phút | Chạy lại từ đầu, kiểm số trong tóm tắt khớp output, dọn repo |
| 15 phút | Dự phòng |

Nộp: README với **trang đầu là tóm tắt cho người ra quyết định**, phần giả định, phương pháp ngắn, kết quả,
giới hạn, "nếu có thêm thời gian", nhật ký thời gian; notebook/SQL chạy lại được bằng một lệnh; không commit
dữ liệu lớn hay key. Làm 15 giờ cho bài 3 giờ là tín hiệu xấu: người chấm đánh giá cả khả năng ước lượng và
cắt phạm vi.

## Case study: "Số đơn hằng tuần giảm 10%". Bạn điều tra thế nào?

1. **Làm rõ**: giảm so với tuần trước hay cùng kỳ năm trước? Tuần này có ngày lễ, có đủ 7 ngày dữ liệu chưa?
   Định nghĩa "đơn" (có tính đơn huỷ, đơn test)? Từ ngày nào?
2. **Loại nhánh dữ liệu trước**: tracking (app version mới mất sự kiện đặt hàng?), pipeline trễ, đổi định
   nghĩa, bot/đơn test bị lọc mới. Nhánh này rẻ để kiểm và hay là thủ phạm.
3. **Phân rã**: số đơn = số phiên × tỉ lệ chuyển đổi. Giảm ở phiên (traffic: marketing, SEO, mùa vụ) hay ở
   chuyển đổi (giá, tồn kho, lỗi checkout)?
4. **Cắt lát**: nền tảng (iOS/Android/web), nước, kênh, khách mới/cũ, danh mục. Giảm đều khắp nơi gợi ý nguyên
   nhân chung (mùa vụ, vĩ mô); giảm tập trung gợi ý nguyên nhân cụ thể (release iOS, một kênh quảng cáo tắt).
5. **Giả thuyết nội bộ và bên ngoài**: release, đổi giá, hết hàng, chiến dịch dừng; đối thủ, thời tiết, sự kiện.
6. **Khuyến nghị và đo**: ví dụ "lỗi thanh toán trên Android 5.2 giải thích 7/10 điểm giảm: rollback và theo
   dõi chuyển đổi Android hằng ngày".

Ứng viên yếu nhảy vào giả thuyết business ngay ("chắc đối thủ khuyến mãi") mà chưa kiểm dữ liệu và chưa phân rã.

## Case study: CEO hỏi "năm sau có nên đẩy mạnh bán ra nước ngoài?" trên dữ liệu Online Retail II.

Làm rõ quyết định trước: ngân sách marketing quốc tế, tuyển sales, hay mở kho ở EU? Rồi nhìn số 12 tháng đủ
(12/2010-11/2011):

- Ngoài UK mang **15.9%** doanh thu (10 027 892 GBP tổng), từ 411 khách có mã.
- Nhưng **10 khách lớn nhất mang 49.8%** doanh thu ngoài UK (phần có mã khách), so với 14.3% ở UK. Một số "thị
  trường" thực chất là một hai khách sỉ.

Kết luận dạng SCQA: "thị trường quốc tế" là hai thứ khác nhau gộp lại: vài key account và một nền khách rộng
ở vài nước. Khuyến nghị tách hai việc: quản lý key account (giữ khách, rủi ro tập trung) và chọn mở rộng ở nước
có nền khách rộng, lặp lại mua nhiều. Tôi sẽ nêu giới hạn: dữ liệu một cửa hàng, một năm, không có chi phí
(không biết lợi nhuận theo nước), không có dữ liệu thị trường bên ngoài; đề xuất bước tiếp theo là xem biên lợi
nhuận theo nước và chi phí vận chuyển trước khi chốt ngân sách.

## Case study: Marketing nói "khách tham gia chương trình thành viên chi tiêu gấp đôi, hãy mở rộng chương trình". Bạn phản hồi thế nào?

Ví dụ giả định. Con số "gấp đôi" có thể đúng mà kết luận vẫn sai:

- **Selection bias**: khách vốn mua nhiều mới đăng ký thành viên. So sánh thành viên với không thành viên là
  so hai nhóm khác nhau từ đầu.
- **Kiểm**: so chi tiêu của cùng khách **trước và sau** khi tham gia (và so với nhóm tương tự chưa tham gia cùng
  kỳ, kiểu difference-in-differences, module 11); xem chi tiêu của thành viên trước khi tham gia đã cao hơn bao nhiêu.
- **Chi phí**: ưu đãi thành viên tốn bao nhiêu trên mỗi đơn; doanh thu tăng thêm có lớn hơn chi phí không.
- **Cách chắc nhất**: thử nghiệm ngẫu nhiên (mời ngẫu nhiên một nhóm, giữ một nhóm đối chứng) trước khi mở rộng.

Cách nói với marketing: không bác bỏ, mà đề xuất cách chứng minh chắc hơn: "Số này cho thấy thành viên là khách
giá trị. Để biết chương trình **tạo ra** thêm chi tiêu, em đề xuất mời ngẫu nhiên 50% khách đủ điều kiện trong 6
tuần; nếu đúng, ta có con số để xin thêm ngân sách."

## Portfolio của một DA nên có gì? Kể về một dự án của bạn.

Ba dự án tốt hơn mười notebook. Mỗi dự án:

- **Một câu hỏi business** cụ thể ("nên cắt SKU nào mà không mất khách lớn"), không phải "phân tích bộ dữ liệu X".
- **Dữ liệu thật** có nguồn và giấy phép; mô tả hạn chế.
- **README màn hình đầu**: kết luận, 3 con số, 1 chart, khuyến nghị. Người tuyển dụng đọc 1-3 phút.
- **Phương pháp đơn giản nhất đủ trả lời**, có giải thích lựa chọn; giới hạn; tái lập được bằng một lệnh.
- Không commit dữ liệu lớn, không commit `.env` hay key.

Roadmap gợi ý hai dự án: dự báo xu hướng doanh số (predicting sales trends) và phân khúc khách hàng (customer
segmentation). Khi kể về một dự án, dùng STAR và bắt đầu bằng câu hỏi và kết quả, không bằng thư viện: "Tôi
muốn biết cửa hàng nên chăm sóc riêng nhóm khách nào. Tôi chia khách theo RFM trên dữ liệu thật, đặt tên từng
nhóm theo hành vi, ước doanh thu mỗi nhóm mang lại và đề xuất một hành động cho hai nhóm lớn nhất; giới hạn là
không có dữ liệu chi phí nên chưa tính được lợi nhuận." Rồi để người phỏng vấn hỏi sâu vào con số và lựa chọn
của bạn.

## Kaggle, khoá học và chứng chỉ có giá trị gì với một DA?

- **Kaggle competitions**: luyện pandas, validation, đọc lời giải hay; nhưng câu hỏi đã đóng khung sẵn và không có
  stakeholder, nên chỉ chứng minh một phần kỹ năng DA. Thứ hạng ít quan trọng với DA hơn với DS/ML.
- **Kaggle datasets và notebooks**: nguồn dữ liệu cho portfolio (kiểm giấy phép, nguồn gốc, có bộ synthetic) và nơi
  viết phân tích công khai.
- **Khoá học/chứng chỉ** (Coursera, edX, Udemy, DataCamp): có ích nhất khi chuyển ngành, CV chưa có kinh nghiệm
  DA; chứng chỉ công cụ (Power BI PL-300, Tableau) có ích khi công ty mục tiêu dùng đúng công cụ đó. Với người có
  kinh nghiệm, dự án và câu chuyện có số thuyết phục hơn.
- **Networking**: cộng đồng, mentor, meetup, viết bài; nhiều vị trí được tuyển qua giới thiệu trước khi đăng tin.

Câu trả lời tốt cho thấy bạn học có chủ đích: chọn khoá học theo khoảng trống của mình và có sản phẩm sau mỗi
khoá (một dự án, một bài viết), không sưu tầm chứng chỉ.

## Kể về một lần phân tích của bạn có lỗi. Bạn đã làm gì?

Câu hỏi hành vi; trả lời theo STAR, phần Action và Result quan trọng nhất. Khung câu trả lời tốt:

- **Situation/Task**: báo cáo gì, cho ai, quyết định gì phụ thuộc vào nó.
- **Action**: phát hiện thế nào (tự đối soát, người khác báo), báo **ngay** cho người dùng số với số đúng và ảnh
  hưởng tới kết luận, sửa gốc (thêm test, thêm bước đối soát, sửa định nghĩa).
- **Result**: kết luận có đổi không, quyết định có bị ảnh hưởng không, quy trình nào đã thay đổi để lỗi không lặp
  lại (ví dụ: mọi báo cáo doanh thu giờ có dòng đối soát với số kế toán).

Ví dụ khung: "Tôi báo AOV 20 GBP trong slide tuần vì query lấy trung bình trên dòng sản phẩm; số đúng trên hoá
đơn là 534 GBP. Tôi gửi đính chính trong ngày, kết luận về xu hướng không đổi vì lỗi có ở mọi tuần, và từ đó mọi
metric mới phải có định nghĩa grain trước khi lên dashboard." Người phỏng vấn tìm sự trung thực và khả năng học
từ lỗi, không tìm một ứng viên chưa bao giờ sai.
