# Hướng làm: EDA một trang về 1 115 cửa hàng Rossmann

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết `store_profile`, một chuỗi EDA mẫu, các con số
tham chiếu trên bộ thật, các quyết định cần cân nhắc và rubric chấm báo cáo.

## `store_profile`

Lọc ngày bán một lần; `groupby("Store")` cho `size`, `mean`, `median`, `std / mean`, `sum(Sales) / sum(Customers)`.
`promo_lift`: `groupby(["Store", "Promo"]).Sales.mean().unstack().reindex(columns=[0, 1])` (để cột luôn có mặt kể cả
khi dữ liệu thiếu hẳn một loại), rồi `col1 / col0 - 1`. Thuộc tính cửa hàng: `join` với
`stores.set_index("Store")[...]`, `how="left"` để không mất cửa hàng thiếu thuộc tính.

## Chuỗi EDA mẫu và con số tham chiếu

| Bước | Con số (ngày bán, 01/2013–07/2015) |
| --- | --- |
| Phạm vi | 1 115 cửa hàng, 844 338 cửa hàng-ngày bán; 181 cửa hàng có dưới 700 ngày bán (180 thiếu cả nửa cuối 2014) |
| Phân phối `mean_sales` | median 6 590, mean 6 935, p25–p75 5 322–7 964 EUR; skew 1.75; p90/p10 2.14; max 21 757 (cửa hàng 817), min 2 704 (cửa hàng 307) |
| Biến động trong cửa hàng | CV median 0.264, từ 0.123 tới 0.551 (cửa hàng 198); CV cao đi kèm doanh số thấp (Spearman −0.22) |
| Nhóm thấp | Quartile dưới: 279 cửa hàng dưới 5 322 EUR/ngày |
| Ít khách hay giỏ nhỏ | Spearman doanh số với khách/ngày 0.80, với EUR/khách 0.07. Median khách/ngày Q1 494, Q4 1 003; EUR/khách Q1 9.11, Q4 9.37 |
| Promo2 | Q1 61% cửa hàng chạy Promo2, Q4 42% (chung 51%) |
| Assortment | Tỉ lệ mặt hàng cơ bản (`a`) Q1 65%, Q4 43%; mở rộng (`c`) Q1 34%, Q4 55% |
| StoreType | Loại a chiếm 62% Q1, 55% Q4; loại b (17 cửa hàng) dồn lên Q4 |
| Đối thủ | Spearman doanh số với `CompetitionDistance` −0.03; median khoảng cách Q1 2 070 m, Q4 2 000 m |
| Khuyến mãi | `promo_lift` median 0.41; Q1 0.44, Q4 0.36 (cửa hàng nhỏ tăng mạnh hơn khi có Promo, theo tỉ lệ) |

**Câu chuyện mẫu**: cửa hàng chênh nhau khoảng gấp đôi giữa p10 và p90; khác biệt đến từ **lượng khách**, không từ
giá trị giỏ; nhóm thấp nghiêng về mặt hàng cơ bản và Promo2; khoảng cách tới đối thủ không giải thích được gì. Bắt
đầu từ lượng khách (vị trí, lưu lượng qua lại), không từ giá.

Headline mẫu: **"Cửa hàng bán thấp là cửa hàng vắng khách: quartile thấp nhất có 494 khách/ngày so với 1 003 ở
quartile cao, giá trị mỗi khách như nhau"**.

## Các quyết định cần cân nhắc

- **Grain và tập ngày**: `mean_sales` trên ngày bán so được giữa cửa hàng có và không thiếu dữ liệu; tổng theo kỳ
  thì không (180 cửa hàng thiếu nửa cuối 2014). Cửa hàng mở Chủ nhật (chủ yếu loại b) có thêm một loại ngày khác hẳn;
  có thể kiểm lại bằng mean chỉ trên thứ Hai–thứ Bảy.
- **Mean hay median mỗi cửa hàng**: doanh số ngày của một cửa hàng lệch phải (ngày trước lễ); median ổn định hơn nhưng
  mean cộng được thành tổng. Hai cách xếp hạng gần như trùng nhau ở đây; nói rõ đã dùng cách nào.
- **Định nghĩa "thấp"**: quartile là quy ước; một ngưỡng nghiệp vụ (dưới chi phí vận hành) tốt hơn nếu có dữ liệu chi
  phí. Kết luận không nên đổi khi dùng 20% hay 30% dưới cùng: kiểm độ nhạy.
- **Tỉ lệ, không số đếm**: nhóm thấp có nhiều cửa hàng loại a chủ yếu vì loại a là 54% chuỗi; so tỉ lệ trong nhóm với
  tỉ lệ chung.
- **Tương quan và nhân quả**: Promo2 dồn ở nhóm thấp có thể vì Promo2 được giao cho cửa hàng yếu (reverse causality).
  Có `Promo2SinceYear`/`Promo2SinceWeek` để so trước/sau trên từng cửa hàng.
- **Ngoại lệ**: cửa hàng 817 và 262 (trên 20 000 EUR/ngày) là cửa hàng thật, không xoá; mô tả chúng riêng nếu cần.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Câu hỏi và phạm vi | 10 | Viết lại câu hỏi thành câu trả lời được bằng dữ liệu; nêu tập ngày, n, định nghĩa "doanh số thấp", dữ liệu thiếu |
| Mô tả phân phối | 15 | Có center (median), spread (p10–p90 hoặc IQR), shape (lệch phải); không chỉ báo mean |
| Tách thành phần | 20 | Tách doanh số thành số khách × giá trị mỗi khách và chỉ ra thành phần nào tạo khác biệt, có số |
| Điểm chung của nhóm thấp | 20 | So tỉ lệ đặc điểm giữa nhóm thấp và nhóm khác (ít nhất hai đặc điểm), có số; nêu cả đặc điểm **không** liên quan (đối thủ) |
| Tương quan và nhân quả | 15 | Nêu ít nhất một giải thích thay thế (Promo2 giao cho cửa hàng yếu, vị trí là biến gây nhiễu) và dữ liệu cần để kiểm |
| Viết một trang | 15 | Headline trả lời thẳng câu hỏi có con số; người đọc không cần biết tên cột; mỗi phát hiện có số, tham chiếu, bằng chứng |
| Bước tiếp theo | 5 | Việc cụ thể có người làm và dữ liệu cần thêm |

Từ 70 điểm trở lên là báo cáo gửi được cho Head of Operations.

## Sai lầm hay gặp

- Mở đầu bằng "dữ liệu có 1 017 209 dòng, 9 cột" và một loạt chart mô tả mọi cột: người đọc không biết bắt đầu từ đâu.
- Tính mean doanh số trên mọi dòng (kể cả ngày đóng cửa) và so cửa hàng: cửa hàng đóng nhiều ngày (Chủ nhật, lễ địa
  phương) bị phạt oan.
- Kết luận "Promo2 làm giảm doanh số" từ việc nhóm thấp chạy Promo2 nhiều hơn.
- Báo "cửa hàng loại a chiếm phần lớn nhóm thấp" mà không nói loại a chiếm phần lớn cả chuỗi.
