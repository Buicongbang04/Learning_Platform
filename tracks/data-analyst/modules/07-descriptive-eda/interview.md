# Câu hỏi phỏng vấn: Thống kê mô tả & EDA

## Stakeholder hỏi "trung bình bao nhiêu?". Trước khi tính, bạn hỏi lại gì?

"Trung bình" chưa phải công thức. Tôi viết lại câu hỏi thành ba phần và xác nhận với người hỏi:

1. **Đơn vị** (grain): trung bình theo khách, theo đơn, theo cửa hàng, hay theo cửa hàng-ngày?
2. **Tập dòng được tính**: có tính đơn huỷ, ngày đóng cửa, khách dùng thử, kỳ chưa đủ ngày không?
3. **Mục đích**: con số sẽ được nhân lên thành tổng (ngân sách, dự báo) hay dùng để mô tả "một khách điển
   hình"? Mục đích đầu cần mean, mục đích sau thường cần median.

Ví dụ trên Rossmann: "doanh số trung bình một ngày" là 5 774 EUR nếu tính mọi dòng (gồm ngày đóng cửa) và
6 956 EUR nếu chỉ tính ngày mở cửa có bán, chênh 20%. Cả hai đều đúng, cho hai câu hỏi khác nhau. Câu trả
lời tôi gửi luôn ghi kèm định nghĩa và n.

## Mean, median, mode: khi nào dùng cái nào? Cho ví dụ mỗi cái bị lừa.

- **Mean** khi cần cộng lại được: tổng = mean × n. Bị lừa bởi đuôi dài và outlier: khoảng cách tới đối thủ
  của các cửa hàng Rossmann có mean 5 405 m nhưng median 2 325 m; chỉ 29% cửa hàng xa hơn mean.
- **Median** khi hỏi "điển hình" trên dữ liệu lệch. Bị lừa khi người nhận nhân nó lên thành tổng (median
  doanh số ngày × 30 không ra doanh số tháng), và trên dữ liệu rời rạc ít giá trị: median `tenure` của khách
  rời bỏ Telco là 10 tháng, nhưng tháng hay gặp nhất của họ là tháng đầu tiên.
- **Mode** cho biến phân loại hoặc rời rạc (gói cước phổ biến nhất). Bị lừa trên biến liên tục: mode cước
  tháng Telco là 20.05 USD, chỉ là giá trị lặp nhiều nhất trong nhóm khách không dùng internet.

Và cả ba đều bị lừa khi dữ liệu **nhiều đỉnh**: cước Telco có mean 64.76, median 70.35, nhưng chỉ 7.6%
khách có cước trong mean ± 5 USD. Khi đó báo theo nhóm (không internet 21, DSL 58, cáp quang 91.5).

## Variance và standard deviation khác nhau thế nào? Vì sao có n − 1?

Variance là trung bình bình phương độ lệch khỏi mean, đơn vị là bình phương đơn vị gốc (USD²), nên khó
diễn giải; SD là căn bậc hai, cùng đơn vị với dữ liệu. Variance dùng để tính (variance của tổng các biến
độc lập bằng tổng variance), SD dùng để báo cáo.

Chia cho n − 1 (Bessel's correction) khi dữ liệu là **mẫu** và muốn ước lượng variance của tổng thể: mean
mẫu được tính từ chính dữ liệu nên độ lệch tới nó nhỏ hơn độ lệch tới mean thật, chia n sẽ ước lượng thấp.
Chia n khi dữ liệu là toàn bộ tổng thể bạn mô tả.

$$
s^2 = \frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar x)^2
$$

Điều quan trọng trong thực tế: pandas mặc định n − 1, numpy mặc định n, Excel có `STDEV.S` và `STDEV.P`. Với
n lớn (7 043 khách) hai bản gần bằng nhau (30.090 và 30.088); với 12 tháng hay 17 cửa hàng thì không. Hai
báo cáo khác công cụ ra hai con số là chuyện thật, nên tôi ghi rõ đã dùng bản nào.

## Khi nào báo IQR thay vì SD?

Khi dữ liệu lệch hoặc có outlier. SD bình phương độ lệch nên một giá trị cực trị chi phối nó; IQR (p75 −
p25) chỉ nhìn 50% giữa nên ổn định. Doanh số ngày Rossmann có skew 1.59 và kurtosis 4.85: báo "median 6 369,
IQR 4 859–8 360 EUR" mô tả ngày bình thường tốt hơn "mean 6 956 ± 3 104".

Ngược lại, SD hợp khi phân phối gần đối xứng một đỉnh (khi đó khoảng 68% nằm trong mean ± 1 SD) và khi cần
đưa vào tính toán tiếp (khoảng tin cậy, sample size). Báo cả hai không thừa: khoảng cách lớn giữa SD và
IQR/1.35 (IQR của phân phối chuẩn bằng khoảng 1.35 SD) là tín hiệu đuôi nặng.

## Skewness và kurtosis nói gì? Kurtosis có phải đo "độ nhọn" không?

Skewness đo độ lệch: dương khi đuôi phải dài, âm khi đuôi trái dài. Kurtosis đo độ nặng của đuôi so với
phân phối chuẩn; pandas, Excel `KURT`, DuckDB `kurtosis` trả **excess kurtosis** (chuẩn = 0).

Kurtosis **không** đo độ nhọn: nó gần như hoàn toàn do phần đuôi quyết định. Kurtosis âm thường gặp ở dữ
liệu phẳng hoặc **hai đỉnh**: `tenure` của Telco có excess kurtosis −1.39 vì hình chữ U (khách mới ở tháng 1,
khách lâu năm dồn ở mức trần 72 tháng). Số khách mỗi ngày của cửa hàng Rossmann có kurtosis 13.3: đuôi nặng,
vài ngày đông bất thường (khai trương, trước lễ).

Trong thực tế tôi dùng hai con số này để **quyết định vẽ gì**, không để báo cáo. Stakeholder không cần nghe
chữ kurtosis; họ cần nghe "vài ngày đột biến chiếm phần lớn biến động".

## Skew gần 0 thì có phải phân phối đối xứng và chuẩn không?

Không. Skew gần 0 chỉ nói các moment bậc ba cân bằng. `tenure` của Telco có skew 0.24 nhưng là hình chữ U;
tách theo hợp đồng thì month-to-month lệch phải (skew 1.05, median 12 tháng) còn hợp đồng hai năm lệch trái
(skew −1.34, median 64). Tổng thể là hỗn hợp của các nhóm có hình dạng ngược nhau. Bài học: luôn vẽ
histogram (tốt nhất là theo nhóm) trước khi tin vào bất kỳ con số tóm tắt hình dạng nào.

## "Trung bình của trung bình" sai ở đâu? Cho ví dụ.

Mean của các mean nhóm cho mỗi nhóm cùng trọng số, bất kể nhóm có bao nhiêu đơn vị. Ví dụ thật:

- Tỉ lệ churn ba loại hợp đồng của Telco là 42.7%, 11.3%, 2.8%; mean của ba tỉ lệ là 18.9%, trong khi tỉ lệ
  churn thật là 26.5%, vì nhóm month-to-month (churn cao) có 3 875 khách, đông nhất.
- AOV trung bình của 38 quốc gia trên Online Retail II là 915 GBP; AOV trên mọi hoá đơn là 534 GBP. Lebanon có
  một hoá đơn nhưng nặng bằng Vương quốc Anh với 18 019 hoá đơn.

Cách đúng: mean có trọng số theo số đơn vị (tương đương tổng tử / tổng mẫu), hoặc báo theo nhóm kèm n. Mean
không trọng số chỉ đúng khi câu hỏi thật sự là "một nhóm điển hình" (ví dụ "một cửa hàng điển hình bán bao
nhiêu" thì mỗi cửa hàng một phiếu).

## Ratio of sums và mean of ratios khác nhau thế nào? Chọn cái nào?

Trên Rossmann, doanh số mỗi khách tính bằng tổng doanh số / tổng số khách là 9.12 EUR; mean của tỉ số doanh
số / số khách từng cửa hàng-ngày là 9.49 EUR. Chúng khác vì ngày đông khách có giá trị mỗi khách thấp hơn,
mà mean of ratios cho ngày vắng và ngày đông cùng trọng số.

- **Ratio of sums** trả lời câu hỏi về tổng thể: "mỗi khách mang lại bao nhiêu" (dùng cho dự báo doanh thu
  từ lượng khách).
- **Mean (hoặc median) of ratios** trả lời "một cửa hàng-ngày điển hình thế nào" (dùng khi so cửa hàng).

Sai lầm không phải chọn cái nào mà là dùng một công thức để trả lời câu hỏi của cái kia, hoặc để hai báo cáo
dùng hai công thức cho cùng một tên metric.

## Case: dashboard báo doanh số nửa cuối năm giảm 13% so với cùng kỳ. Bạn kiểm tra gì trước?

Trước khi tìm nguyên nhân kinh doanh, tôi kiểm con số có so được không:

1. **Tập đơn vị có giống nhau không?** Đếm số cửa hàng có dữ liệu ở mỗi kỳ. Trên Rossmann, nửa cuối 2014 chỉ
   có 935 cửa hàng (180 cửa hàng không có dữ liệu từ 01/07 tới 31/12/2014), so với 1 115 cùng kỳ 2013.
2. **So trên balanced panel**: chỉ 935 cửa hàng có dữ liệu cả hai kỳ. Tổng của chúng tăng 2.5% (1 016.3 →
   1 041.8 triệu EUR). Cú giảm 13.2% hoàn toàn là do thiếu dữ liệu.
3. **Kiểm mix**: doanh số trung bình mỗi cửa hàng-ngày trên mọi cửa hàng tăng 3.4%, nhưng trên 935 cửa hàng
   chỉ tăng 2.7%, vì 180 cửa hàng vắng mặt vốn bán thấp hơn mức chung (6 690 so với 7 012 EUR/ngày).
4. **Hỏi chủ dữ liệu**: 180 cửa hàng thiếu do đóng cửa sửa chữa, đổi hệ thống POS hay lỗi pipeline? Câu trả
   lời quyết định có được điền bù hay phải ghi chú.

Trả lời stakeholder: "Doanh số không giảm; so cùng tập cửa hàng tăng 2.5%. Dashboard thiếu dữ liệu của 180 cửa
hàng nửa cuối 2014, đã báo team data engineering." Và đề xuất dashboard hiển thị số đơn vị có dữ liệu cạnh mỗi
tổng.

## Case: Head of Retention cần biết nên nhắm nhóm khách nào để giảm churn. Bạn làm EDA thế nào?

Tôi time-box (ví dụ 2 ngày) và đi theo câu hỏi:

1. **Định nghĩa**: churn là gì trong dữ liệu (Telco: `Churn = Yes` là rời trong tháng gần nhất; 26.5%), một
   dòng là một khách.
2. **Chất lượng tối thiểu**: `TotalCharges` có 11 ô trống, đều là khách `tenure = 0`; ghi chú, không xoá bừa.
3. **Bảng tỉ lệ theo nhóm** có n, tỉ lệ, **tỉ trọng trong số khách rời bỏ** và lift: month-to-month churn
   42.7% và chiếm 88.6% số khách rời; khách 0–6 tháng churn 52.9%; cáp quang 41.9%.
4. **So phân phối** biến số giữa hai nhóm (median, IQR, không chỉ mean): tenure median 10 so với 38 tháng.
5. **Phân tầng để tránh kết luận sai**: khách rời có `TotalCharges` thấp hơn, nhưng trong mọi nhóm tenure họ
   lại có `TotalCharges` cao hơn; tenure là biến gây nhiễu.
6. **Đề xuất**: nhóm month-to-month dùng cáp quang (2 128 khách, churn 54.6%, chiếm 62.2% số khách rời) là
   ứng viên đầu tiên, nói rõ đây là tương quan và đề xuất thử nghiệm ưu đãi chuyển hợp đồng.

Ưu tiên theo **tỉ trọng trong số khách rời**, không chỉ theo tỉ lệ: người cao tuổi churn 41.7% nhưng chỉ chiếm
25.5% số khách rời.

## Case: CFO hỏi "bao nhiêu % khách mang lại 80% doanh thu?" để thiết kế chương trình VIP. Bạn trả lời thế nào?

Đây là câu hỏi về **độ tập trung**, một dạng độ phân tán. Tôi tính doanh thu mỗi khách (định nghĩa doanh thu
và kỳ rõ ràng), sắp giảm dần, rồi báo:

- Top share: top 1%, 10%, 20% khách chiếm bao nhiêu % doanh thu; bao nhiêu % khách cần để đạt 80%.
- Lorenz curve và Gini để so giữa các kỳ hoặc các thị trường bằng một con số.
- Ngưỡng VIP theo phân vị (ví dụ p90 doanh thu năm), kèm số khách và doanh thu của nhóm đó.

Những điều tôi nói rõ: khách mua lần đầu vào cuối kỳ có ít thời gian để chi, nên độ tập trung bị phóng đại (cần
so trên cohort có đủ thời gian quan sát); khách vãng lai không có mã khách không nằm trong phân tích; và "80/20"
là một quy luật kinh nghiệm, không phải con số phải ra. Bài Advanced 02 làm đúng việc này trên Online Retail II.

## Bạn sinh thống kê mô tả bằng công cụ nào: SQL, pandas hay Excel? Vì sao?

Tôi chọn theo nơi dữ liệu nằm, ai dùng kết quả và có cần lặp lại không:

- **SQL trên warehouse** khi dữ liệu lớn đã nằm ở đó và thống kê được xem định kỳ: tính gần dữ liệu, định nghĩa
  sống trong view/dbt model dùng chung. Cần biết khác biệt giữa database: Postgres không có `median()` (dùng
  `percentile_cont`), SQL Server `AVG` trên cột `int` trả số nguyên.
- **pandas** (hoặc DuckDB trên file) cho EDA: thống kê tuỳ biến (có trọng số, trimmed mean, theo nhóm), vẽ ngay,
  viết hàm tái dùng và test được.
- **Excel** khi dữ liệu nhỏ và người nhận muốn tự xem công thức; nhớ `STDEV.S` khác `STDEV.P`,
  `PERCENTILE.INC` khác `PERCENTILE.EXC`.

Profiling tự động (ydata-profiling) tốt cho lần nhìn đầu nhưng không biết câu hỏi kinh doanh, nên không thay được
bước EDA có câu hỏi.

## Cột có 30% giá trị thiếu. Mean của cột đó có tin được không?

`AVG`, `AVERAGE`, `mean()` đều bỏ qua NULL lặng lẽ, nên con số là mean của 70% còn lại. Tin được hay không phụ
thuộc vào **cơ chế thiếu**: nếu thiếu ngẫu nhiên thì mean vẫn ước lượng tốt; nếu thiếu có hệ thống (khách
không trả lời khảo sát thu nhập thường là thu nhập cao, review không có nội dung thường là khách hài lòng) thì
mean lệch. Tôi luôn báo `count` cạnh `mean`, so phân phối của các biến khác giữa nhóm thiếu và không thiếu, và
phân biệt NULL với 0: Rossmann ghi ngày đóng cửa là doanh số 0, không phải NULL, nên nó kéo mean xuống thay vì
bị bỏ qua.

## Trimmed mean và winsorized mean là gì? Khi nào dùng?

Trimmed mean bỏ p% quan sát ở mỗi đầu rồi lấy mean; winsorized mean thay các giá trị ngoài p% bằng giá trị ở
ngưỡng rồi lấy mean. Cả hai ổn định hơn mean, dùng nhiều thông tin hơn median. Khoảng cách tới đối thủ của
Rossmann: mean 5 405 m, trimmed 10% 3 775 m, winsorized 5–95% 4 933 m, median 2 325 m.

Dùng khi cần một con số "trung bình" ít nhạy với vài giá trị cực trị nhưng vẫn mang tinh thần mean (ví dụ chấm
điểm thi, theo dõi thời gian phản hồi). Nhược điểm: ngưỡng cắt tuỳ ý, khó giải thích với stakeholder, và
**không cộng lại thành tổng** được. Trong báo cáo kinh doanh tôi thường dùng median kèm khoảng phân vị cho câu
hỏi "điển hình" và mean (thật) cho câu hỏi tổng.

## Bạn trình bày kết quả EDA cho lãnh đạo thế nào?

Một trang, không phải notebook. Thứ tự: headline là kết luận có con số; dữ liệu và phạm vi (kỳ, lọc gì, n,
định nghĩa metric); ba phát hiện, mỗi cái một con số so với một tham chiếu và một chart; điều chưa biết (tương
quan hay nhân quả, dữ liệu thiếu); bước tiếp có người làm. Notebook đi kèm cho ai muốn kiểm lại. Lỗi hay gặp
là trình bày theo thứ tự mình đã làm ("đầu tiên tôi xem phân phối của...") thay vì theo thứ tự người nghe cần
("nhóm A rời bỏ nhiều nhất, vì..., đề xuất...").

## Phân phối của một metric có đuôi dài. Khi so hai nhóm, bạn so bằng gì?

Không chỉ so mean. Tôi so median và IQR, vẽ ECDF hai nhóm trên cùng trục (đọc được "bao nhiêu % dưới X" cho
từng nhóm), và nếu cần một con số thì báo chênh lệch median kèm khoảng tin cậy bootstrap. Mean vẫn cần nếu
quyết định dựa trên tổng (doanh thu nhóm A sẽ tăng bao nhiêu), nhưng khi đó tôi kiểm xem chênh lệch mean có do
vài quan sát cực trị gây ra không (bỏ top 1% rồi so lại). Trên dữ liệu rất lệch, chênh lệch mean có thể đổi dấu
chỉ vì một khách sỉ.
