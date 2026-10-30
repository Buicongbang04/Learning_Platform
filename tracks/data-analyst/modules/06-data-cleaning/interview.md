# Câu hỏi phỏng vấn: Làm sạch dữ liệu

## Bạn làm gì đầu tiên khi nhận một bộ dữ liệu mới?

Trước khi làm sạch hay phân tích, tôi dựng **hồ sơ** và trả lời bốn câu:

1. **Grain**: một dòng là gì (một mặt hàng trong hoá đơn, một cửa hàng một ngày, một sự kiện)? Từ grain suy ra khoá
   phải duy nhất và độ phủ phải đủ.
2. **Phạm vi**: bao nhiêu dòng, khoảng thời gian, kỳ đầu và kỳ cuối có đủ không (Online Retail II dừng 09/12/2011 lúc
   12:50, tháng 12 chưa đủ).
3. **Hồ sơ cột**: kiểu, tỉ lệ thiếu, số giá trị khác nhau, khoảng giá trị, giá trị lạ (âm, 0, năm 1900).
4. **Dấu vân tay thế giới thật**: phân phối có lệch như dữ liệu thật không, có mùa vụ không, cột tiền có khớp số
   lượng × giá không.

Chỉ sau đó tôi mới đặt quy tắc làm sạch, và mỗi quy tắc gắn với một chỉ số sẽ báo cáo. Ứng viên junior thường nhảy
thẳng vào `dropna()`; ứng viên senior hỏi "dữ liệu này dùng để trả lời câu hỏi gì".

## Phân biệt MCAR, MAR, MNAR. Vì sao DA cần quan tâm?

- **MCAR**: khả năng thiếu không phụ thuộc biến nào (máy quét kẹt giấy ngẫu nhiên). Bỏ dòng thiếu chỉ làm mất dữ liệu,
  không làm lệch.
- **MAR**: thiếu phụ thuộc biến quan sát được (đơn từ app cũ không có mã vùng). Bỏ dòng làm lệch, nhưng sửa được nếu
  phân tích theo biến đó.
- **MNAR**: thiếu phụ thuộc chính giá trị bị thiếu (khách rất không hài lòng ít trả lời khảo sát). Không sửa được bằng
  dữ liệu có sẵn.

DA cần quan tâm vì cách xử lý phụ thuộc cơ chế. Ví dụ Online Retail II: 24.9% dòng hợp lệ thiếu `Customer ID`, nhưng
27.0% ở UK và 0% ở Đức; thiếu ở mức cả hoá đơn, tập trung buổi chiều, hoá đơn nhiều món mỗi món 1 cái. Không phải MCAR.
Nếu team CRM `dropna()` rồi tính doanh thu, doanh thu thấp đi 16.5%. Không chứng minh được cơ chế, nhưng bác được MCAR
bằng cách so tỉ lệ thiếu giữa các nhóm.

## Khi nào bỏ dòng thiếu, khi nào điền, khi nào giữ?

Quyết định theo **chỉ số**, không theo cột:

| Tình huống | Cách |
| --- | --- |
| Chỉ số không cần cột thiếu (doanh thu không cần mã khách) | Giữ dòng, báo tỉ lệ thiếu |
| Chiều phân tích thiếu một phần (vùng) | Giữ, nhãn "Không rõ", báo tỉ lệ |
| Lấy được giá trị đúng từ nguồn khác (bảng giá theo ngày) | Điền từ nguồn, ghi nhật ký |
| Thiếu mang nghĩa xác định (giờ không có dòng nghĩa là 0 lượt thuê) | Điền giá trị đó, nhưng tách khỏi thiếu do hệ thống ngừng |
| Chỉ số cần cột, không có nguồn | Tính trên phần có dữ liệu, nói rõ phạm vi |
| Biến đầu vào cho model | Impute (median, model) kèm cờ "đã điền", fit trên train |

Hai điều không làm trong báo cáo: điền khoá định danh (mã khách chung "GUEST" sẽ thành khách lớn nhất, gấp 6 lần khách
thật lớn nhất trên Online Retail II) và điền tiền bằng trung bình.

## Phân biệt trùng chính xác, trùng theo khoá và trùng gần đúng. Xử lý mỗi loại thế nào?

- **Trùng chính xác**: mọi cột giống nhau. Online Retail II sheet 2010-2011 có 5 268 dòng như vậy. Chưa chắc là lỗi:
  grain "một mặt hàng trong hoá đơn" cho phép quét hai lần. Hỏi nguồn, rồi quyết định và ghi nhật ký.
- **Trùng theo khoá**: cùng khoá, khác giá trị (hai dòng cùng `(Store, Date)` khác doanh số). Là lỗi khoá; phải tìm bản
  đúng (mới nhất, từ nguồn chính), không lấy đại dòng đầu.
- **Trùng gần đúng**: tên viết lệch (`RETRO LEAVES` / `RETO LEAVES`, `Cty TNHH ABC` / `ABC Co., Ltd`). Chuẩn hoá chuỗi,
  blocking, đo similarity, lọc bằng quy tắc nghiệp vụ, rồi người duyệt.

`df.duplicated(keep=False)` đánh dấu mọi dòng trong nhóm trùng (để xem), `keep="first"` để bỏ. Bỏ cả hai dòng của một
cặp trùng là lỗi hay gặp: mất một dòng thật.

## Fuzzy matching tên sản phẩm cho similarity 0.96. Bạn có gộp không?

Chưa. Similarity đo ký tự, không đo nghĩa. Trên Online Retail II, `GARDENIA 1 WICK MORRIS BOXED CANDLE` và
`GARDENIA 3 WICK ...` giống 0.97, `LETTER A BLING KEY RING` và `LETTER B ...` giống 0.96: đều là sản phẩm khác nhau. Ở
ngưỡng 0.9, 589 cặp tên của các mã khác nhau, và sau khi lọc bằng quy tắc "khác đúng một từ, từ đó không có số, dài ít
nhất 4 ký tự, là lỗi chính tả" thì không còn cặp nào.

Quy trình tôi dùng: chuẩn hoá (rẻ, bắt phần lớn), blocking để chạy được, fuzzy cho ứng viên, quy tắc nghiệp vụ loại
biến thể cỡ/màu/số, người duyệt, lưu bảng ánh xạ. Và luôn hỏi: có khoá ổn định không (mã hàng)? Nếu có, gom theo khoá,
tên chỉ là nhãn.

## IQR, z-score, robust z: khác nhau thế nào, dùng khi nào?

- **IQR**: ngoài khoảng Q1 − 1.5 IQR tới Q3 + 1.5 IQR. Không giả định phân phối chuẩn; một ngưỡng cho cả chuỗi.
- **z-score**: lệch khỏi mean hơn 3 std. Giả định gần chuẩn; bị masking (một điểm cực lớn làm std phình, điểm lớn thứ
  hai thoát).
- **Robust z**: dùng median và MAD, ngưỡng 3.5; ít bị chính outlier kéo.

Cả ba đều sai khi dữ liệu có mùa vụ hoặc nhiều đỉnh. Bike Sharing: cả ba không đánh dấu ngày bão 29/10/2012 (22 lượt,
z = −2.31) vì lượt thuê dao động theo mùa; IQR trên lượt theo giờ đánh dấu 505 giờ, phần lớn 8h, 17h, 18h, tức giờ cao
điểm. Với chuỗi có mùa vụ, tôi so với mốc theo ngữ cảnh: trung vị trượt, hoặc cùng giờ × loại ngày.

## Outlier: bỏ, sửa hay giữ?

Quy tắc thống kê chỉ cho ứng viên. Tôi phân loại mỗi điểm:

1. **Thiếu đo**: con số thấp vì đo thiếu (29/10/2012 chỉ có 1 giờ dữ liệu). Không dùng như một quan sát.
2. **Lỗi đo / nhập**: không thể xảy ra (độ ẩm 0% khi trời mưa, giá âm, tuổi 200). Sửa cột sai thành thiếu, giữ phần
   còn lại của dòng.
3. **Đã bị huỷ / đảo**: hoá đơn 168 470 GBP bị huỷ 12 phút sau. Xử lý theo quy tắc huỷ.
4. **Sự kiện thật**: bão, Giáng sinh, đơn sỉ lớn. Giữ trong báo cáo, chú thích; trong model thì gắn cờ hoặc thêm biến.

Winsorize hợp cho trực quan hoá hoặc model nhạy outlier, không bao giờ cho tổng tiền.

## Case: Kế toán trưởng nói doanh thu của team data lệch sổ kế toán. Bạn xử lý thế nào?

1. **Đừng cãi bằng con số cuối**. Dựng bảng đối soát từ tổng thô tới số báo cáo, mỗi bước một lý do, số dòng và số tiền
   bị loại. Trên Online Retail II sheet 2009-2010: tổng `Quantity × Price` thô 9 539 484.63 GBP;
   loại hoá đơn huỷ (các dòng này cộng lại −629 855.37, nên loại chúng làm tổng tăng), dòng giá âm (−136 552.02, điều
   chỉnh nợ xấu), mã phí (466 073.72), dòng trùng (34 100.71) → doanh thu hàng hoá 9 805 717.59.
2. **Tách định nghĩa khỏi lỗi**. Phí ship có phải doanh thu không? Kế toán tính, báo cáo "doanh thu hàng hoá" thì
   không. Đó là quyết định định nghĩa: liệt kê để kế toán chọn.
3. **Đối chiếu từng bước** với sổ: thường lệch nằm ở một hai bước (huỷ tính theo ngày huỷ hay ngày mua, phí sàn).
4. **Ghi lại định nghĩa thống nhất** trong tài liệu metric và đưa nhật ký vào pipeline để lần sau không phải làm tay.

## Case: Giám đốc vận hành gửi một bộ dữ liệu từ đối tác và xin 5 báo cáo cho buổi họp quý. Bạn thấy số liệu "phẳng" bất thường. Bạn làm gì?

Đây là tình huống bộ Grocery Sales: 6.76 triệu dòng, mỗi giao dịch đúng một dòng, `TotalPrice` toàn 0, số lượng mỗi dòng
đều từ 1 tới 25 (chi-square so với đều: p = 0.51), mọi giờ trong ngày bằng nhau (3h sáng như 18h), số dòng mỗi ngày
có phương sai / trung bình 0.92 (như đếm Poisson), 23 nhân viên chênh nhau 0.8%, rượu vang nằm trong danh mục "Snails".

1. **Thu bằng chứng ở nhiều chiều độc lập**, không dừng ở một kiểm định. So với một siêu thị thật (dunnhumby: trung vị
   5 món mỗi giỏ, 79% dòng mua 1 đơn vị, 17h đông gấp 100 lần 4h).
2. **Trả lời từng yêu cầu**: báo cáo nào cần cột nào, cột đó vì sao không mô tả hành vi thật. Giỏ hàng: không có giỏ.
   Giờ cao điểm: không có giờ cao điểm thật; vẽ ra vẫn có một giờ "cao nhất" và ai đó sẽ xếp ca theo nó.
3. **Kết luận trước**: "Bộ này là dữ liệu sinh giả, không báo cáo insight; cần bản xuất POS thật có mã giỏ, giá, giờ".
   Nói bộ này dùng được cho việc gì (tập SQL, thiết kế schema).

Không làm: giao dashboard kèm "lưu ý ở phụ lục", hoặc "sửa" `TotalPrice` bằng `Price × Quantity` rồi báo cáo.

## Case: Team BI sắp đưa một nguồn mới lên dashboard doanh số tuần. Bạn kiểm gì trước?

Một bộ check khai báo được, phủ sáu chiều: completeness, uniqueness, validity, consistency, timeliness, accuracy. Với
Rossmann store sales (1 115 cửa hàng, 2013-2015): khoá `Store` + `Date` duy nhất, không ô thiếu, đóng cửa không có doanh
số, `StateHoliday` thuộc tập cho phép. Mọi check theo dòng đều đạt, nhưng **check độ phủ** cho thấy 180 cửa hàng không có
dòng nào từ 01/07 tới 31/12/2014. Tổng chuỗi tháng 7/2014 vì thế "giảm" 8.5% so với tháng 6, một cú giảm không có thật.

Báo cáo của tôi phân loại mức độ theo **tác động lên chỉ số**, không theo số dòng: lỗ hổng độ phủ (0 dòng lỗi) là chặn;
54 ngày mở cửa mà doanh số 0 là cần xử lý; năm đối thủ mở cửa 1900 là ghi chú. Khuyến nghị xử lý tạm (so sánh
like-for-like trên cửa hàng có đủ dữ liệu cả hai kỳ), hỏi nguồn, và đưa check vào pipeline (dbt tests, pandera).

## Bạn chọn công cụ làm sạch thế nào: Excel, OpenRefine, pandas, SQL hay dbt? Vì sao?

Theo ba câu hỏi: làm một lần hay lặp lại, dữ liệu lớn cỡ nào và ở đâu, ai review.

| Tình huống | Công cụ | Vì sao |
| --- | --- | --- |
| Gộp 50 000 tên công ty viết lệch, một lần, có người duyệt | OpenRefine | Clustering cho nhóm ứng viên, duyệt bằng mắt nhanh |
| File đối tác hằng tuần, 12 bước, cần review | pandas trong git, có test và nhật ký | Tái lập, review được diff, chạy lại được |
| CSV 517 MB trên laptop 4 GB | DuckDB (SQL trên file) | Quét theo khúc, không nạp cả tệp vào RAM |
| Dữ liệu đã ở warehouse, kiểm mỗi lần nạp | dbt tests | Chạy cùng `dbt build`, chặn dữ liệu lỗi trước dashboard |
| Người nhận cần tự sửa, dữ liệu nhỏ | Excel / Power Query | Ai cũng mở được; Power Query ghi lại các bước |
| Team dùng R | dplyr | Theo codebase sẵn có; chi phí chuyển đổi lớn hơn lợi ích |

Tôi chọn công cụ theo việc và theo hệ sinh thái công ty, không theo thói quen. Lỗi hay gặp: làm tay trong Excel một việc
lặp lại hằng tuần, hoặc viết pipeline cho một việc làm một lần.

## Dữ liệu đọc từ Excel/CSV hay bị lỗi kiểu gì? Phòng thế nào?

- **Cột trộn kiểu**: `Invoice` của Online Retail II có `489434` (int) và `C489449` (str). Xét tiền tố `C` trên cột chưa
  ép `str` sẽ lỗi hoặc bỏ sót.
- **pandas đoán kiểu theo khúc**: `StateHoliday` của Rossmann đọc mặc định thành 131 072 số `0` và 886 137 chuỗi `"0"`;
  lọc `== "0"` bỏ sót 13% số dòng mà không báo lỗi.
- **Số nguyên có ô thiếu thành float**: `Customer ID` = `13085.0`. Dùng `Int64`.
- **Mã mất số 0 đầu**: mã bưu chính, mã cửa hàng đọc thành số.
- **Ngày**: số serial Excel (ngày kể từ 1899-12-30), nhiều định dạng trong một cột.

Phòng: khai báo `dtype` khi đọc, mã luôn là chuỗi, `pd.to_datetime(format=..., errors="coerce")` rồi **đếm** `NaT`, và
một check kiểu trong bộ DQ.

## Nhật ký làm sạch là gì, vì sao cần?

Một bảng nhỏ: mỗi bước làm sạch một dòng, gồm lý do, số dòng bị loại, số dòng còn lại, và số tiền bị loại nếu là dữ liệu
tài chính. Mỗi dòng chỉ bị loại cho lý do đầu tiên nó vi phạm, nên nhật ký cộng lại khớp từ số thô tới số cuối.

Vì sao cần: (1) đối soát với kế toán, BI, team khác mà không phải ngồi cùng nhau đọc code; (2) phát hiện bất thường khi
chạy lại (tuần này bước "trùng" loại gấp 10 tuần trước: nguồn có vấn đề); (3) tách quyết định định nghĩa (bỏ phí ship)
khỏi sửa lỗi, để người đọc thấy và chọn. Đi kèm hai nguyên tắc: không sửa tệp thô, và làm sạch là một hàm chạy lại được.

## Data quality có những chiều nào? Chiều nào hay bị bỏ sót?

Completeness (thiếu), uniqueness (khoá), validity (miền giá trị, kiểu), consistency (giữa cột, giữa bảng: `Promo2 = 0`
thì `Promo2Since` phải trống), timeliness (dữ liệu tới đâu, có kỳ nào thiếu), accuracy (khớp nguồn sự thật như sổ kế
toán).

Hay bị bỏ sót nhất là **độ phủ theo thời gian**, vì check theo dòng không thấy dòng vắng mặt. Thứ hai là **accuracy**:
mọi check đạt mà con số vẫn sai nếu không ai đối chiếu với một nguồn độc lập. Thứ ba là **tính hợp lý của cả bộ**: dữ
liệu sinh giả đạt mọi check kiểu và khoá.

## Bạn dùng kiểm định thống kê thế nào để nghi ngờ một bộ dữ liệu? p-value lớn có chứng minh dữ liệu giả không?

Hai công cụ: kiểm định **chi-square độ phù hợp** cho số đếm theo nhóm so với phân phối đều, và **chỉ số phân tán**
(phương sai / trung bình) của số đếm theo ngày.

p-value lớn **không chứng minh** gì; nó chỉ nói kiểm định không thấy khác biệt với "đều". Sức nặng đến từ ngữ cảnh: với
hàng triệu dòng, dữ liệu thật hầu như luôn có p-value gần 0 vì chỉ cần lệch nhỏ là bị bắt. Grocery Sales có p = 0.51 cho
số lượng, 0.86 cho giờ, 0.43 cho nhân viên, 0.99 cho sản phẩm; chỉ số phân tán ngày 0.92 so với 388 của một siêu thị
thật. Nhiều chiều độc lập cùng phẳng, cộng lỗi logic (cột tiền toàn 0, rượu vang trong danh mục "ốc"), mới là bằng
chứng. Bẫy cần tránh: đếm tổng theo thứ trong tuần khi số ngày mỗi thứ khác nhau (19 thứ Hai so với 18 thứ Năm) cho p
gần 0 giả; phải so trung bình mỗi ngày.

## Đối chiếu pandas và dplyr cho các thao tác làm sạch thường gặp.

| Việc | pandas | dplyr / tidyr |
| --- | --- | --- |
| Bỏ dòng thiếu một cột | `df.dropna(subset=["x"])` | `drop_na(x)` |
| Điền | `df["x"].fillna(0)` | `mutate(x = replace_na(x, 0))` |
| Bỏ trùng theo khoá | `df.drop_duplicates("k")` | `distinct(k, .keep_all = TRUE)` |
| Lọc | `df.query("q > 0")` | `filter(q > 0)` |
| Chuẩn hoá chuỗi | `df.s.str.strip().str.upper()` | `mutate(s = str_to_upper(str_trim(s)))` |
| Chuỗi thao tác | `.pipe(f).pipe(g)` | `%>% f() %>% g()` |

Khác biệt cần nhớ: `distinct()` không có `.keep_all = TRUE` chỉ trả cột khoá; `NA` trong R lan qua phép so sánh
(`filter(x > 0)` bỏ dòng `NA` âm thầm), pandas `NaN > 0` là `False` nên cũng bỏ. Cả hai đều cần đếm thiếu trước khi lọc.
