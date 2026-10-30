# Câu hỏi phỏng vấn: Excel / Spreadsheet

## VLOOKUP, INDEX/MATCH và XLOOKUP khác nhau thế nào? Bạn dùng cái nào?

| | VLOOKUP | INDEX/MATCH | XLOOKUP |
| --- | --- | --- | --- |
| Hướng tra | Khoá ở cột đầu, kết quả bên phải | Mọi hướng | Mọi hướng |
| Mặc định | Khớp **gần đúng** (phải thêm `FALSE`) | `MATCH(...,0)` là khớp chính xác | Khớp chính xác |
| Chèn cột vào bảng | Hỏng (số cột gõ cứng) | Không ảnh hưởng | Không ảnh hưởng |
| Không tìm thấy | `#N/A`, phải bọc `IFNA` | `#N/A`, phải bọc `IFNA` | Có tham số `if_not_found` |
| Có ở | Mọi nơi | Mọi nơi | Excel 365/2021, Google Sheets, LibreOffice ≥ 24.8 |

Câu trả lời senior: dùng XLOOKUP khi biết mọi người nhận file có bản hỗ trợ, INDEX/MATCH khi gửi ra
ngoài hoặc cho người dùng Excel 2016/2019 (họ sẽ thấy `#NAME?`), VLOOKUP chỉ khi bảng tra nhỏ, ổn
định, khoá ở cột đầu, và **luôn** có `FALSE`. Quan trọng hơn hàm là hai quyết định: khoá đã chuẩn hoá
chưa (khoảng trắng, hoa thường, số lưu dạng text), và "không tìm thấy" thì trả gì.

## VLOOKUP thiếu tham số FALSE thì chuyện gì xảy ra?

VLOOKUP mặc định khớp gần đúng: nó giả định cột khoá đã sắp tăng dần, tìm nhị phân và trả về dòng
lớn nhất nhỏ hơn hoặc bằng khoá. Trên bảng chưa sắp xếp, kết quả là **giá trị của một dòng khác**,
không báo lỗi. Trên danh mục giá của bài basic 02 (4 101 mã, sắp theo mô tả chứ không theo mã),
`VLOOKUP(mã, Catalog!B:C, 2)` thiếu FALSE chỉ trả đúng giá cho 65 trong 1 078 dòng có mã trong danh mục,
và gán **một con số** cho 438 trong 440 dòng mã mới đáng ra phải "không tìm thấy". Trong bài audit, bảng
mùa sắp theo tên (mã 3, 1, 2, 4): lỗi chỉ lộ thành `#N/A` ở các tháng mùa 2, các mã khác tình cờ đúng,
nên người làm trước tưởng chỉ là "vài ô lỗi".

Khớp gần đúng chỉ đúng cho bảng bậc thang có chủ đích (bậc thuế, bậc chiết khấu theo số lượng), sắp
tăng dần, và nên ghi chú ngay cạnh công thức rằng đó là cố ý.

## Bạn nhận một workbook báo cáo từ đồng nghiệp đã nghỉ việc. Bạn kiểm nó thế nào trước khi dùng số của nó?

Quy trình theo thứ tự rủi ro:

1. **Show Formulas** (Ctrl+`): tìm số gõ cứng giữa vùng công thức. Một ô dán đè giá trị là lỗi phổ
   biến nhất và không ai thấy khi nhìn số.
2. **Vùng tổng hợp**: SUM/SUMIFS có phủ hết dòng không? Dòng mới thêm có nằm trong vùng không?
3. **Tham chiếu khi kéo**: công thức tăng trưởng có `$` sai chỗ không (mọi tháng chia cho một ô)?
4. **Tra cứu**: VLOOKUP có `FALSE` không, "không tìm thấy" trả gì, có `IFERROR(...,0)` nuốt lỗi không?
5. **Dòng tổng của tỉ lệ**: là tổng tử chia tổng mẫu hay trung bình các tỉ lệ?
6. **Đối chiếu độc lập**: tính lại 2–3 con số chính bằng pandas/SQL hoặc pivot từ dữ liệu gốc.

Trong bài advanced 02, sáu lỗi loại này làm tăng trưởng 2012 so với 2011 hiện 53.1% thay vì 64.9%,
và tháng 12/2012 hiện YoY +223.9% thay vì +41.7%. Ghi kết quả thành bảng: ô, lỗi, ảnh hưởng trước →
sau, cách sửa; rồi đề xuất thêm sheet Checks để lần sau workbook tự báo.

## SUMIFS và pivot table: khi nào dùng cái nào?

- **Pivot**: khám phá nhanh, đổi chiều liên tục, drill-down; báo cáo một lần.
- **SUMIFS**: báo cáo có bố cục cố định (template gửi hằng tuần), khi ô báo cáo cần tham chiếu ổn định
  từ ô khác, khi cần điều kiện phức tạp mà pivot không làm được (khoảng ngày động, so với ô tham số).

Rủi ro của pivot: quên Refresh, vùng nguồn không mở rộng, công thức trỏ vào ô pivot vỡ khi pivot đổi
bố cục. Rủi ro của SUMIFS: vùng điều kiện và vùng cộng lệch kích thước (Excel báo `#VALUE!`), tiêu chí
text có ký tự đại diện `*`/`?` bị hiểu là wildcard. Thực tế tốt: pivot để tìm câu chuyện, SUMIFS (hoặc
SQL) để dựng báo cáo lặp lại, và đối chiếu hai cái với nhau.

## Vì sao "trung bình của trung bình" sai? Cho ví dụ.

Vì mỗi trung bình có mẫu số khác nhau. AOV (doanh thu / số đơn) của Germany và France trong 3 tháng
9–11/2011 là sáu con số; trung bình sáu con số đó là 562.08 GBP, nhưng AOV đúng của cả nhóm là tổng
doanh thu chia tổng số đơn: 166 426.86 / 311 = 535.13 GBP. Ô France 10/2011 (956.73, kéo bởi một hoá
đơn 8 895.76 GBP trên chỉ 35 đơn) được đối xử ngang ô có 68 đơn.

Quy tắc cho dòng "Tổng" của một bảng tỉ lệ: cộng tử số, cộng mẫu số, rồi chia. Áp dụng cho AOV,
conversion rate, lượt thuê trung bình/ngày, margin %.

## COUNT, COUNTA, COUNTIF, COUNTIFS khác nhau thế nào?

- `COUNT` đếm ô chứa **số** (và ngày, vì ngày là số). Đếm cột `Customer ID` bằng COUNT ra số dòng có
  mã khách: 6 761 trên 6 810 dòng của bài basic 03.
- `COUNTA` đếm ô **không trống**, kể cả text, lỗi và chuỗi rỗng do công thức trả `""`.
- `COUNTBLANK` đếm ô trống (ô có `""` từ công thức cũng tính là trống).
- `COUNTIF(vùng, điều_kiện)`, `COUNTIFS` nhiều điều kiện.

Bẫy: mã khách lưu dạng text thì COUNT ra 0. Không hàm nào trong số này đếm **giá trị khác nhau**; cần
cột phụ đánh dấu lần xuất hiện đầu, `UNIQUE` (Excel 365, Sheets, LibreOffice mới) hoặc pivot với
distinct count (Excel Data Model).

## DATEDIF dùng thế nào và có những bẫy gì?

`DATEDIF(start, end, "d"|"m"|"y"|"ym"|"yd"|"md")`. Bẫy:

1. Đếm đơn vị **tròn**: từ 12/11/2010 tới 03/11/2011 là 11 tháng (ngày 3 chưa tới ngày 12).
2. `start > end` ra `#NUM!`; đừng giấu bằng `IFERROR`, hãy báo ngày đảo như một lỗi dữ liệu.
3. Đơn vị `"md"` có thể sai ở cuối tháng, Microsoft khuyên tránh.
4. Ngày kèm giờ: trừ trực tiếp ra số thập phân; nên lấy `INT()` hoặc chỉ giữ phần ngày.
5. Excel không gợi ý DATEDIF khi gõ (hàm giữ lại vì tương thích Lotus 1-2-3), nhiều người tưởng không có.

Ứng dụng của DA: tenure khách (tháng từ lần mua đầu tới lần mua cuối), recency (ngày từ lần mua cuối
tới ngày báo cáo, tham số trong một ô tuyệt đối như `$L$1`, không dùng `TODAY()` để báo cáo không
đổi mỗi lần mở).

## TRIM, PROPER, SUBSTITUTE có những giới hạn gì khi làm sạch dữ liệu?

- `TRIM` bỏ dấu cách (mã 32) ở hai đầu và gộp dấu cách liền nhau, nhưng **không** bỏ non-breaking
  space (mã 160) từ dữ liệu copy trên web; dùng `SUBSTITUTE(A2,CHAR(160)," ")` trước. `CLEAN` bỏ ký tự
  điều khiển.
- `PROPER` viết hoa chữ cái sau mọi ký tự không phải chữ cái: `POPPY'S` thành `Poppy'S`, `3D` giữ
  `3D`. Tên riêng như `McDonald`, `iPhone` cũng sai. Dùng cho hiển thị, không dùng làm khoá.
- `SUBSTITUTE` phân biệt hoa thường và thay **mọi** lần xuất hiện, kể cả trong từ khác.

Trên Online Retail II, 885 trong 4 223 mô tả sản phẩm đổi sau TRIM, và 112 mã hàng chỉ khác nhau ở
chữ hoa/thường (`15056BL` và `15056bl`). Excel so sánh không phân biệt hoa thường nên không thấy vấn đề,
SQL JOIN thì thấy hai sản phẩm.

## Bạn dùng conditional formatting và data validation để làm gì?

**Data validation** để kiểm soát **đầu vào**: dropdown cho ô chọn segment/quốc gia, giới hạn khoảng cho
ô giả định (% tăng giá từ -50% tới 50%), ngày trong kỳ. Nó chặn lỗi gõ `"At-risk"` hay `"At risk "` thay vì `"At risk"`
làm COUNTIF ra 0 im lặng.

**Conditional formatting** để mắt thấy **ngoại lệ**: khách `Lost`, tăng trưởng âm, ô kiểm tra FALSE,
heatmap trên ma trận. Dùng tiết chế: một hai quy tắc có ý nghĩa nghiệp vụ. Không dùng conditional
formatting thay cho kiểm tra: màu không chặn ai gửi file sai, một ô `ALL OK = FALSE` ở đầu báo cáo thì
có.

## Case: Head of Sales gửi file Excel 300 000 dòng, nhờ bạn "thêm vài cột tính hoa hồng rồi gửi lại hằng tuần". Bạn làm gì?

Câu hỏi làm rõ trước: hoa hồng dùng để **trả lương** (cần chính xác, giải trình được) hay để theo dõi?
Quy tắc hoa hồng có thay đổi theo thời gian không? Ai khác sửa file này?

Đề xuất:

1. 300 000 dòng lặp hằng tuần, lại liên quan tới tiền trả cho người: không nên là workbook sửa tay.
   Đưa dữ liệu vào SQL (DuckDB/warehouse), viết quy tắc hoa hồng thành bảng tham số có ngày hiệu lực,
   tính bằng SQL/Python có test.
2. Đầu ra vẫn là Excel vì Head of Sales quen Excel: mỗi tuần sinh file tóm tắt theo nhân viên (vài
   trăm dòng) kèm sheet chi tiết lọc được, sheet README (định nghĩa, ngày chạy) và sheet Checks (tổng
   hoa hồng khớp tổng doanh thu × tỉ lệ).
3. Trong lúc chưa xong pipeline, nếu phải làm bằng Excel: dữ liệu gốc một sheet không sửa, quy tắc
   trong sheet tham số, cột tính bằng công thức, tổng đối chiếu.

Điểm phỏng vấn muốn nghe: biết giới hạn của spreadsheet, nhưng không ép business bỏ Excel; đổi phần
logic, giữ phần giao diện quen thuộc.

## Case: Dashboard nói doanh thu tháng là 1.2 triệu, file Excel của finance nói 1.15 triệu. Bạn đối chiếu thế nào?

Reconcile là việc spreadsheet làm tốt nhất:

1. Thống nhất **định nghĩa**: gộp hay ròng (đã trừ huỷ/trả hàng)? Có thuế không? Theo ngày đặt hàng
   hay ngày ghi nhận? Múi giờ cắt ngày nào?
2. Đặt hai nguồn cạnh nhau ở **mức chi tiết nhỏ nhất** có chung khoá (ngày, rồi hoá đơn). XLOOKUP mỗi
   hoá đơn của nguồn A vào nguồn B, cột chênh lệch = A − B.
3. Pivot chênh lệch theo loại: hoá đơn chỉ có ở A, chỉ có ở B, có ở cả hai nhưng khác số tiền.
4. Giải thích phần lớn chênh lệch bằng vài nguyên nhân (đơn huỷ, ngày cắt), ghi vào bảng reconcile.

Trên Online Retail II, chênh lệch kiểu này xuất hiện ngay: đơn huỷ (mã `C…`) và dòng giá 0 có tính
không, hai sheet trùng nhau 01–09/12/2010 có bị cộng hai lần không. Kết luận gửi stakeholder: con số
nào là "chính thức", vì sao, và định nghĩa đó được ghi ở đâu.

## Case: Marketing muốn một Google Sheet cả team cùng sửa để theo dõi chiến dịch, kèm số đơn hàng từ hệ thống. Bạn thiết kế thế nào?

- Tách **phần người nhập** (tên chiến dịch, ngân sách, kênh, ngày chạy) khỏi **phần hệ thống đổ vào**
  (số đơn, doanh thu từ warehouse qua Connected Sheets hoặc script định kỳ). Hai phần ở hai sheet,
  phần hệ thống được khoá (protected range).
- Data validation cho kênh, trạng thái, ngày; một cột ID chiến dịch duy nhất làm khoá ghép.
- Sheet báo cáo dùng XLOOKUP/SUMIFS ghép hai phần theo ID, có ô kiểm tra "chiến dịch không có ID khớp".
- Định nghĩa metric (đơn quy cho chiến dịch nào: last click? trong bao nhiêu ngày?) ghi ở sheet
  README, vì đây là chỗ hai team sẽ cãi nhau.
- Khi số chiến dịch hoặc dữ liệu lớn dần (Sheets chậm từ vài chục nghìn dòng có công thức, trần 10
  triệu ô), chuyển phần tính toán vào warehouse, Sheet chỉ còn là form nhập và bảng hiển thị.

## Vì sao bạn chọn Excel (hay Google Sheets, hay Python) cho một việc cụ thể?

Trả lời theo tiêu chí, không theo sở thích:

| Tiêu chí | Hướng về spreadsheet | Hướng về SQL/Python |
| --- | --- | --- |
| Cỡ dữ liệu | Vài nghìn tới vài chục nghìn dòng | Từ ~100 nghìn dòng, nhiều bảng join |
| Tần suất | Một lần, ad-hoc | Lặp lại hằng tuần/ngày |
| Người dùng kết quả | Cần tự lọc, tự sửa giả định | Chỉ đọc kết quả |
| Giải trình | Không cần sau này | Phải tái lập sau nhiều tháng (tài chính, pháp lý) |
| Cộng tác | Nhiều người cùng xem (Sheets) | Nhiều người cùng sửa logic (git + review) |

Ví dụ trả lời: "Phân tích 300 dòng khiếu nại một lần cho Head of CS, tôi dùng Google Sheets vì họ
tự lọc theo loại lỗi được và không cần ai cài gì. Báo cáo doanh thu tuần cho 12 thị trường, tôi viết
SQL và để Python sinh file Excel có sheet Checks, vì mỗi tuần sửa tay một workbook là mỗi tuần có một
cơ hội gõ đè ô." Giữa Excel và Sheets: Excel khi cần Power Query/Power Pivot, mô hình tài chính,
gửi đối tác; Sheets khi cần cộng tác thời gian thực và công ty dùng Google Workspace.

## Excel có giới hạn bao nhiêu dòng? Chuyện gì xảy ra khi vượt?

1 048 576 dòng × 16 384 cột mỗi sheet (`.xlsx`); định dạng `.xls` cũ chỉ 65 536 dòng × 256 cột.
LibreOffice Calc từ 7.4 có cùng giới hạn với `.xlsx`. Google Sheets giới hạn theo **ô**: 10 triệu ô
mỗi file.

Khi mở CSV vượt giới hạn, Excel cảnh báo rồi **cắt bớt** phần thừa; nếu ai đó bỏ qua cảnh báo rồi lưu
lại, dữ liệu mất vĩnh viễn. Sự cố Public Health England năm 2020 (15 841 ca COVID-19 dương tính báo
trễ) đến từ giới hạn 65 536 dòng của `.xls`. Online Retail II được phát hành thành hai sheet vì tổng
hai năm là 1 067 371 dòng, vượt một sheet. Cách xử lý: đọc bằng pandas/DuckDB, tổng hợp xuống mức cần
xem rồi mới đưa ra spreadsheet; Excel có Power Query/Data Model để giữ dữ liệu lớn ngoài lưới ô.

## Làm sao để một workbook gửi đi "tự báo" khi sai?

- Sheet **Checks** với các ô TRUE/FALSE: tổng báo cáo = tổng dữ liệu gốc, số đơn khớp, dữ liệu đúng
  kỳ, không ô lỗi; một ô `ALL OK = AND(...)` đặt ở đầu sheet báo cáo, tô đỏ khi FALSE.
- Kiểm tra so **hai đường tính độc lập** (báo cáo đi qua SUMIFS theo tuần, kiểm tra cộng thẳng cột
  doanh thu của dữ liệu gốc). So một ô với chính nó hoặc với số gõ tay không kiểm gì.
- Ô thông tin (không phải TRUE/FALSE) cho những thứ cần người đọc biết: số dòng bị loại vì huỷ/giá 0,
  số dòng trùng lặp hoàn toàn (24 trong 6 729 dòng của bài advanced 01, giữ lại và nêu ra thay vì tự
  xoá vì có thể là hai lần quét hàng thật).
- Sheet README: nguồn, khoảng thời gian, định nghĩa metric, ai làm, ngày cập nhật.

## Spreadsheet có cách nào để version control và review không?

Không tốt như code, nhưng có:

- Google Sheets và Excel trên OneDrive/SharePoint có **version history**, xem ai sửa ô nào khi nào.
- Excel có **Inquire / Spreadsheet Compare** (bản Office Professional Plus/365 Enterprise) để so hai
  phiên bản; LibreOffice có Edit > Track Changes > Compare Document.
- Tách logic khỏi workbook: công thức nặng chuyển vào SQL/dbt có git, workbook chỉ hiển thị.
- Sinh workbook bằng Python (openpyxl): file là đầu ra của code đã review, có thể sinh lại; diff nằm
  ở code chứ không ở `.xlsx` nhị phân.
- Quy ước: bản gửi đi có số phiên bản và ngày trong tên file hoặc sheet README, không gửi "final_v3_sửa".
