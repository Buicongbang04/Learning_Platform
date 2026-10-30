# Câu hỏi phỏng vấn: Business & financial analytics

## Doanh thu tháng này giảm 8% so với tháng trước. Quy trình điều tra của bạn là gì?

Đi theo thứ tự "có thật không → so với gì → phân rã → drill-down → nguyên nhân có đối chứng → hành động":

1. **Kiểm con số**: tháng đã đủ ngày chưa (so tháng dở dang với tháng đủ là lỗi phổ biến nhất); định nghĩa doanh
   thu có đổi không (gộp hay thuần, có trừ huỷ không); có nguồn dữ liệu nào ngừng đổ về (một quốc gia, một nhóm cửa
   hàng, một kênh); số ngày cuối tuần, ngày lễ của hai tháng.
2. **So với gì**: tháng trước không trừ được mùa vụ; cùng kỳ năm trước trừ được mùa vụ nhưng lệch lịch (lễ di động).
   Thường xem cả hai, cộng với kế hoạch.
3. **Phân rã** theo công thức của chỉ số: doanh thu = khách × tần suất × AOV, hoặc price-volume-mix, hoặc mix và rate
   theo kênh. Phân rã chỉ ra *thành phần* nào đổi.
4. **Drill-down** thành phần đó theo các chiều (sản phẩm, vùng, kênh, loại khách) để biết thay đổi tập trung hay lan
   rộng. Tập trung (một khách sỉ, một sản phẩm) thường có nguyên nhân cụ thể; lan rộng thường là mùa vụ, giá, kinh tế.
5. **Giả thuyết + đối chứng**: "đối thủ mở cửa hàng" chỉ thuyết phục khi cửa hàng không có đối thủ mới không giảm.
6. **Memo**: headline là kết luận có con số, phần nào chắc, phần nào là giả thuyết, ai làm gì tiếp.

Lỗi hay gặp nhất là nhảy thẳng vào bước 4 và tìm ra một "nguyên nhân" cho một cú giảm không có thật.

## Mix effect và rate effect là gì? Cho ví dụ hai thứ ngược chiều nhau.

Khi KPI là trung bình có trọng số của các nhóm (AOV toàn bộ = tổng tỉ trọng đơn × AOV từng nhóm), thay đổi của nó
tách được thành **rate** (giá trị trong từng nhóm đổi, tính theo tỉ trọng mới) và **mix** (tỉ trọng nhóm dịch chuyển,
tính theo giá trị cũ); hai phần cộng đúng bằng thay đổi.

Ví dụ thật trên Online Retail II: AOV quý 1/2011 là 530.94 GBP, tháng 9-11/2011 là 560.20 (+5.5%). Rate +50.90, mix
−21.64. Đơn khách vãng lai có AOV gần gấp đôi (957 lên 1 866) nhưng tỉ trọng giảm từ 9.2% xuống 4.6%; khách có mã
(95% số đơn) chỉ +2%. Báo "AOV tăng 5.5%" mà không phân rã thì người nghe sẽ hiểu sai là khách quen mua giỏ to hơn.

Trường hợp cực đoan là Simpson's paradox: mọi nhóm tăng nhưng tổng giảm vì tỉ trọng dồn về nhóm có giá trị thấp.
Câu phỏng vấn hay hỏi tiếp: "tỉ lệ chuyển đổi toàn site giảm nhưng mọi kênh đều tăng" thì trả lời bằng đúng phân rã này.

## Price-volume-mix bridge là gì? Có cạm bẫy nào?

PVM tách thay đổi doanh thu của các sản phẩm có ở cả hai kỳ thành ba phần: giá (giá từng sản phẩm đổi), lượng (tổng
số lượng đổi với mix và giá giữ nguyên), mix (khách chuyển sang sản phẩm đắt / rẻ hơn); cộng thêm sản phẩm mới và
sản phẩm ngừng bán. Ba cạm bẫy:

- **Công thức là một lựa chọn**: trên Online Retail II, mùa cao điểm 2011 so với 2010, tính giá trên lượng kỳ mới cho
  hiệu ứng giá −117 nghìn GBP; tính trên lượng kỳ gốc cho +147 nghìn, đổi cả dấu (mix cũng đổi dấu). Ghi rõ công thức,
  giữ cố định, và không lấy hiệu ứng nhỏ, đổi dấu làm thông điệp chính.
- **Giá bình quân thực thu không phải giá niêm yết**: hiệu ứng giá âm ở ví dụ trên đến từ bán xả đồ Giáng sinh tồn kho
  (median giá dòng 1.45 xuống 0.39 GBP, giá cao nhất gần như giữ nguyên).
- **Sản phẩm mới**: ở ví dụ trên, 743 mã mới mang về 1.18 triệu GBP, lớn hơn cả mức tăng tổng (+190 nghìn); mã cũ
  bán ít hơn 22% về số lượng. Không tách sản phẩm mới thì câu chuyện "danh mục được thay mới" biến mất.

## Gross margin, contribution margin và operating margin khác nhau thế nào? Markup khác margin ra sao?

- **Gross margin** = (doanh thu thuần − giá vốn) / doanh thu thuần. Nói về giá bán so với giá mua / sản xuất.
- **Contribution margin** = (doanh thu − mọi chi phí biến đổi) / doanh thu: trừ thêm giao hàng, phí thanh toán, hoa
  hồng, đóng gói, những thứ đi theo từng đơn hoặc từng đồng doanh thu. Dùng cho quyết định "thêm một đơn / một khách /
  một kênh có lời không" và tính hoà vốn.
- **Operating margin** trừ thêm chi phí cố định (lương văn phòng, thuê, phần lớn marketing). Nói về hiệu quả cả
  doanh nghiệp.

**Markup** chia cho giá vốn, **margin** chia cho giá bán: markup 50% (vốn 100, bán 150) là margin 33%. Hai phòng ban
dùng hai khái niệm mà không nói rõ là nguồn lệch số kinh điển. Thêm một bẫy: margin chia cho doanh thu **thuần**; trên
Online Retail II, huỷ và trả hàng bằng 8.4% doanh thu gộp, đủ để làm lệch mọi tỉ lệ.

## Bạn tính unit economics của một đơn hàng thế nào? Sai lầm hay gặp là gì?

Contribution của một đơn = doanh thu − giá vốn − phí thanh toán (theo tiền) − chi phí mỗi đơn (đóng gói, giao) −
chi phí mỗi dòng hàng (nhặt hàng). Mỗi loại chi phí có **driver** riêng: giá vốn theo số lượng hàng, phí thanh toán
theo tiền thu, giao hàng theo số đơn (và cân nặng, điểm đến).

Sai lầm hay gặp:

- Gộp mọi chi phí thành "x% doanh thu": đơn nhỏ trông có lời trong khi chi phí cố định mỗi đơn ăn hết.
- Khi mô phỏng tăng giá, để giá vốn tăng theo doanh thu: đánh giá thấp lợi ích của tăng giá. Trong bài Basic 02 (giả
  định giá vốn 60%), làm đúng thì tăng giá 5% được mất tới khoảng 12% số đơn; làm sai chỉ còn khoảng 5%.
- Báo "5% đơn đang lỗ" thay vì "lỗ bao nhiêu tiền": cùng bài đó, 1 023 đơn lỗ nhưng tổng chỉ khoảng 4 nghìn GBP
  trên 3.76 triệu contribution. Đặt giá trị đơn tối thiểu vì con số "5%" là quyết định sai.

## Sản phẩm có contribution margin 40%. Tăng giá 5% thì được mất bao nhiêu lượng? Elasticity liên quan thế nào?

Mỗi đơn vị lời thêm 5 (trên giá 100), từ 40 lên 45. Contribution không đổi khi 45 q' = 40 q, tức lượng giảm tối đa
−p / (m + p) = 0.05 / 0.45 ≈ 11.1%. Giảm giá thì ngược lại và đắt hơn nhiều: margin 20%, giảm giá 10% phải bán thêm
100% mới hoà.

Elasticity ε = % đổi lượng / % đổi giá. Tăng giá có lợi khi khách phản ứng yếu hơn ngưỡng hoà vốn: ở đây khi
|ε| nhỏ hơn khoảng 0.111 / 0.05 ≈ 2.2. Ước elasticity từ dữ liệu quan sát dễ sai (giá đổi cùng lúc với mùa, quảng
cáo, đối thủ), nên DA đưa ngưỡng hoà vốn và đề xuất thử nghiệm giá trên một nhóm cửa hàng / khách hàng có đối chứng.

## Dashboard ghi "ngày khuyến mãi bán nhiều hơn 39%". Đó có phải tác động của khuyến mãi không?

Chưa chắc. Đó là chênh lệch quan sát; tác động tăng thêm là phần không có nếu không khuyến mãi. Cần kiểm:

- **So sánh cùng điều kiện**: Rossmann chỉ khuyến mãi thứ Hai tới thứ Sáu, nên so với ngày thường không khuyến mãi,
  không với cả cuối tuần. Ở đây hai con số tình cờ gần bằng nhau (thứ Bảy thấp, Chủ nhật cao bù nhau), nhưng theo từng
  thứ thì lift từ +57% (thứ Hai) xuống +22% (thứ Sáu).
- **Kéo cầu**: khách mua trữ trong tuần khuyến mãi, tuần sau mua ít. Lịch Rossmann xen kẽ tuần nên mọi tuần không
  khuyến mãi đều ngay sau một tuần có: mốc so sánh có thể đã bị kéo xuống, làm lift phóng đại.
- **Lượt khách hay giỏ hàng**: +19.8% lượt khách, +15.9% chi tiêu mỗi khách. Khác nhau về hành động (traffic thì nghĩ
  tới nhân sự quầy, giỏ thì nghĩ tới tồn kho).
- **Lợi nhuận**: doanh thu +39% chưa trừ tiền giảm giá. Với margin giả định 30%, khuyến mãi hoà vốn khi tiền giảm
  giá khoảng 12% doanh số ngày khuyến mãi.

Câu trả lời tốt kết thúc bằng thiết kế thử nghiệm: giữ / bỏ khuyến mãi trên hai nhóm cửa hàng ngẫu nhiên, metric
chính là lợi nhuận gộp theo tuần.

## Cannibalization và halo effect là gì? Đo thế nào?

**Cannibalization**: doanh số tăng ở chỗ được khuyến mãi / mở mới nhưng lấy từ chỗ khác của chính mình: sản phẩm thay
thế (khuyến mãi nước ngọt chai 1.5 lít làm giảm chai 500 ml), cửa hàng gần đó (mở cửa hàng mới cách 300 m), kỳ khác
(kéo cầu). **Halo**: ngược lại, khách đến vì một sản phẩm khuyến mãi và mua thêm hàng không khuyến mãi.

Cách đo ở mức DA: mở rộng phạm vi đo từ "mã khuyến mãi" ra "cả nhóm sản phẩm / cả khu vực / cả chu kỳ trước-trong-
sau"; tách lượt khách và chi tiêu mỗi khách; so với nhóm đối chứng (danh mục / cửa hàng không khuyến mãi cùng thời
gian). Nếu tổng của nhóm không tăng bằng phần tăng của mã khuyến mãi, phần chênh là cannibalization.

## FP&A nhờ bạn dự báo doanh số 8 tuần tới. Bạn làm và trình bày thế nào?

1. **Chuỗi so sánh được**: chỉ đơn vị có dữ liệu đủ cả kỳ (cửa hàng mở mới / đóng cửa / thiếu dữ liệu tính riêng),
   bỏ kỳ dở dang ở đầu và cuối. Trên Rossmann, tổng mọi cửa hàng tụt khoảng 14% từ 7/2014 chỉ vì 180 cửa hàng thiếu
   dữ liệu; chuỗi 934 cửa hàng đủ ngày thì tăng.
2. **Baseline đơn giản trước**: seasonal naive, moving average, một phương pháp dùng thông tin biết trước (lịch khuyến
   mãi, ngày lễ).
3. **Backtest nhiều điểm cắt**, horizon đúng bằng nhu cầu (8 tuần), đo MAPE và bias. Trên Rossmann: trung bình theo
   lịch khuyến mãi 6.26%, seasonal naive 6.31%, moving average 14.8%, ETS mùa vụ 52 tuần khoảng 10%.
4. **Trình bày**: con số theo tuần, khoảng (±MAPE backtest hoặc phân vị sai số), giả định (lịch khuyến mãi, số cửa
   hàng), tuần nào rủi ro cao (lễ di động). Hai phương pháp chênh 0.05 điểm qua vài điểm cắt chồng nhau là nhiễu;
   chọn cái dễ giải thích.

## Vì sao seasonal naive là baseline bắt buộc? Khi nào mới dùng ETS hay machine learning?

Seasonal naive không cần fit, ai cũng hiểu ("bằng cùng tuần năm ngoái"), và thường rất khó thắng với chuỗi mùa vụ
mạnh. Một phương pháp phức tạp không thắng được nó trong backtest thì không có lý do tồn tại: thêm chi phí bảo trì,
khó giải thích, và nhiều khi tệ hơn. Ví dụ Rossmann: ETS mùa vụ 52 tuần trên hơn hai năm dữ liệu phải ước 52 hệ số
mùa vụ từ hai quan sát mỗi tuần, ra MAPE khoảng 10% so với 6.3% của seasonal naive.

Dùng ETS khi có đủ vài chu kỳ mùa và xu hướng / mùa vụ ổn định; dùng ML (lag feature, nhiều chuỗi một model) khi có
nhiều chuỗi, nhiều biến giải thích biết trước, và có người duy trì pipeline (track Data Science module 07). Dù dùng gì,
seasonal naive vẫn nằm trong bảng backtest làm thước đo.

## MAPE, MAE và bias khác nhau thế nào? Khi nào MAPE đánh lừa?

MAE là sai số tuyệt đối trung bình theo đơn vị gốc (dễ nói với vận hành: "lệch khoảng 2 triệu mỗi tuần"). MAPE chia cho
thực tế nên so được giữa các chuỗi khác cỡ. Bias = tổng(dự báo − thực tế) / tổng thực tế: cho biết dự báo cao hay thấp
có hệ thống, điều FP&A quan tâm nhất (thiếu hàng hay thừa hàng).

MAPE đánh lừa khi thực tế gần 0 (chia cho số rất nhỏ, ngày đóng cửa), và nó phạt dự báo cao nặng hơn dự báo thấp. Bias
gần 0 không có nghĩa chính xác: moving average trên Rossmann có bias +0.5% nhưng MAPE 14.8%, vì sai cao ở tuần thấp
và sai thấp ở tuần cao triệt tiêu nhau. Báo cáo dự báo nên có cả độ lớn sai số lẫn bias.

## Scenario, sensitivity và forecast khác nhau thế nào? Bạn dựng một mô hình what-if ra sao?

- **Forecast**: điều gì sẽ xảy ra nếu mọi thứ tiếp tục như cũ.
- **Scenario**: điều gì xảy ra nếu một bộ giả định nhất quán đổi (xấu: mất 10% đơn và giá vốn tăng; tốt: AOV +5%).
- **Sensitivity**: mỗi giả định đổi một lượng, các giả định khác giữ nguyên, kết quả đổi bao nhiêu: chỉ ra giả định
  nào cần xác minh kỹ nhất.

Dựng mô hình driver: viết chỉ số đích thành phép tính từ vài driver người ra quyết định hiểu (số đơn, AOV, tỉ lệ giá
vốn, chi phí mỗi đơn), mỗi driver một ô giả định có nguồn, công thức chỉ tham chiếu ô. Trên Online Retail II tháng
11/2011 (giả định giá vốn 60%, 8 GBP mỗi đơn), mỗi driver +10%: giá vốn làm contribution −15.6%, chi phí mỗi đơn chỉ
−0.4%. Kết luận thực dụng: dành thời gian xác minh giá vốn, không phải cước giao hàng.

## Bạn thiết kế cảnh báo KPI hằng ngày thế nào để người nhận không bỏ qua?

- **Baseline có mùa vụ**: median cùng thứ của vài tuần trước (cùng trạng thái khuyến mãi nếu có), bỏ ngày lễ khỏi
  lịch sử. Median để một ngày bất thường không kéo baseline.
- **Độ lệch tương đối và thang robust**: ln(giá trị / baseline) chia 1.4826 × MAD của độ lệch trong các ngày
  **trước** đó, ngưỡng khoảng 4. Ngưỡng cố định báo theo mùa (Bike Sharing: 98 ngày, 72 ngày vào tháng 1-3); so với
  hôm qua báo cả ngày sau ngày bất thường.
- **Gộp và phân loại**: ngày liên tiếp thành một đợt; gắn lý do biết trước (lễ, trước / sau lễ, thời tiết). Trên
  doanh số ngày Rossmann, 46 trong 48 cảnh báo là do lịch.
- **Runbook và chủ sở hữu**: mỗi cảnh báo có người nhận, việc kiểm đầu tiên (dữ liệu có về đủ không), và nơi ghi kết
  luận để chỉnh quy tắc. Đo tỉ lệ cảnh báo dẫn tới hành động; thấp thì nâng ngưỡng hoặc bỏ metric.

## Vì sao bạn giao mô hình what-if cho CFO bằng spreadsheet mà không phải notebook Python hay dashboard BI?

Chọn công cụ theo người dùng và cách dùng. CFO cần **tự đổi giả định ngay trong buổi họp** và thấy kết quả: spreadsheet
có ô giả định tách riêng, bảng kịch bản (Data Table, Scenario Manager), Goal Seek cho câu "giá vốn lên bao nhiêu thì
lỗ". Notebook đòi người dùng sửa code; dashboard BI hiện số thực tế, không giả lập.

Nhưng spreadsheet không phải nơi tính dữ liệu gốc: phần nặng (PVM trên hàng nghìn mã, chuẩn bị mốc từ hàng triệu dòng)
làm bằng SQL/Python, có kiểm tra, rồi đổ vào sheet "dữ liệu" của mô hình. Khi mô hình phải chạy hằng tháng cho nhiều
phòng ban với quy trình duyệt, chuyển sang công cụ FP&A (Anaplan, Pigment) hoặc pipeline. Ngược lại, cảnh báo hằng
ngày không bao giờ nên nằm trong spreadsheet hay notebook chạy tay: nó cần lịch chạy tự động (job SQL, BI alert).

## Like-for-like (comparable store) sales là gì? Vì sao quan trọng?

Tăng trưởng chỉ tính trên các cửa hàng (hoặc sản phẩm, thị trường) có hoạt động đầy đủ ở cả hai kỳ: bỏ cửa hàng mới
mở, đã đóng, đóng cửa sửa chữa dài ngày, hoặc thiếu dữ liệu. Tăng trưởng tổng = tăng trưởng like-for-like + đóng góp
của mở mới / đóng cửa; nhà đầu tư bán lẻ nhìn like-for-like vì nó cho biết cửa hàng hiện có có bán tốt hơn không.

Trong phân tích, like-for-like còn là cách bảo vệ khỏi dữ liệu thiếu: trên Rossmann, 180 cửa hàng không có dữ liệu nửa
cuối 2014 làm tổng tụt khoảng 14%; chuỗi 934 cửa hàng đủ ngày thì tăng 1.5% cùng thời điểm. Báo cáo tăng trưởng nên
ghi rõ là tổng hay like-for-like, và danh sách loại trừ.

## Case: Chuỗi tăng 3.4% so với cùng kỳ nhưng 33 trong 1 115 cửa hàng giảm hơn 10%. Bạn trả lời Head of Retail Operations thế nào?

Đây là bài Advanced 01, trên Rossmann (6 tháng đầu 2015 so với 2014). Hướng làm:

- **Phân rã nhân** doanh số mỗi cửa hàng = ngày mở cửa × lượt khách mỗi ngày × chi tiêu mỗi khách. Ở 33 cửa hàng, 30
  mất hơn 10% lượt khách, chi tiêu mỗi khách gần như không đổi, chỉ một cửa hàng ít ngày mở cửa hơn (đóng 5 tuần).
  Vấn đề là khách không đến, không phải giá.
- **Nguyên nhân có đối chứng**: cửa hàng có đối thủ gần nhất mở trong 2014 giảm khoảng 4%, cửa hàng có đối thủ từ
  trước tăng khoảng 4%; đối thủ mới cách dưới 500 m thì median −5.8%. 18 trong 33 cửa hàng thuộc nhóm này.
- **Phần chưa giải thích**: 14 cửa hàng tụt thành bậc ở một tháng trong 2014 rồi đứng yên; dữ liệu (chỉ ghi một đối
  thủ, có ô ghi năm 1900) không giải thích được. Việc cần làm là quản lý vùng kiểm tại chỗ, không phải phân tích thêm.
- **Hành động theo nhóm**: đối thủ mới thì chỉnh mục tiêu và thử chương trình giữ khách có đối chứng; đóng cửa thì tách
  khỏi like-for-like; chưa rõ thì kiểm tại chỗ trong hai tuần.

## Case: CFO hỏi "đơn nhỏ đang lỗ, có nên đặt giá trị đơn tối thiểu 25 GBP không?"

Trả lời bằng unit economics và bảng kịch bản, với giả định chi phí ghi rõ (bài Basic 02, Online Retail II, giả định giá
vốn 60%, phí thanh toán 2%, 8 GBP mỗi đơn, 0.25 GBP mỗi dòng):

- 1 064 đơn dưới 25 GBP, contribution trung bình khoảng −4 GBP mỗi đơn. Bỏ hết (khách bị chặn bỏ đi): contribution
  cả năm tăng khoảng 4 nghìn GBP, khoảng 0.1%.
- Rủi ro không nằm trong bảng: đơn nhỏ hay là đơn đầu tiên của khách mới; chặn chúng có thể mất khách có giá trị lâu
  dài (kiểm bằng cohort, module 12).
- Đòn bẩy lớn hơn nhiều nằm ở chỗ khác: giá vốn ±20% đổi contribution ±1.28 triệu; tăng giá 5% được mất tới 12% số đơn.

Kết luận gửi CFO: "không đáng đặt đơn tối thiểu; nếu muốn, thử phí giao hàng cho đơn nhỏ trên một nhóm khách và đo
tỉ lệ quay lại".

## Case: Giám đốc kinh doanh thấy "hiệu ứng giá" âm trong báo cáo PVM và muốn tăng giá. Bạn nói gì?

Trước hết, hiệu ứng giá trong PVM đo **giá bình quân thực thu**, không phải giá niêm yết. Trên Online Retail II (mùa
cao điểm 2011 so với 2010), hiệu ứng giá âm đến từ một nhóm đồ Giáng sinh bị bán xả (median giá dòng 1.45 xuống 0.39
GBP trong khi giá cao nhất gần như giữ), tức là một quyết định thanh lý tồn kho có chủ đích, không phải "giá đang quá
thấp". Thứ hai, dấu của hiệu ứng giá đổi khi đổi công thức (−117 nghìn hay +147 nghìn), nên nó không đủ chắc để làm căn
cứ đổi giá.

Câu hỏi "có nên tăng giá" cần hai thứ khác: ngưỡng hoà vốn (với margin hiện tại, tăng 5% được mất bao nhiêu lượng) và
phản ứng thật của khách (thử nghiệm giá trên một nhóm sản phẩm hoặc khách hàng có đối chứng). Câu chuyện lớn hơn trong
bridge là danh mục: tăng trưởng đến hoàn toàn từ mã mới, mã cũ bán ít hơn 22%. Đó mới là thứ đáng bàn trong buổi họp.
