# Hướng làm: ghép doanh số nội bộ với World Bank để chọn thị trường

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, các con số tham chiếu, một memo mẫu rút gọn,
các quyết định cần cân nhắc và rubric.

## Hai hàm

- `match_countries`: kiểm alias trước (mã không có trong `wb_countries["iso3"]` thì `ValueError`), dựng dict
  `tên.strip().casefold() -> iso3` từ World Bank, rồi duyệt `names` theo thứ tự: có trong `aliases` thì dùng alias
  (`None` là cố ý không nối), không thì tra dict, không thấy thì `unmatched`. Alias đứng trước khớp tên vì nó là quyết
  định có chủ đích của người phân tích.
- `coverage`: tập tên có `iso3`, chia tổng doanh thu của chúng cho tổng doanh thu; tên còn lại sắp giảm dần theo doanh
  thu để thấy ngay phần mất lớn nhất.

## Con số tham chiếu (World Bank lastupdated 2026-10-08)

- Doanh thu dòng hợp lệ 01–11/2011: 9 204 146 GBP, ngoài Anh 1 519 815 GBP, 37 tên nước.
- Không khớp nguyên văn: `EIRE`, `Hong Kong`, `Unspecified`, `USA`, `European Community`, `RSA`, `Czech Republic`. Năm
  alias (`IRL`, `HKG`, `USA`, `ZAF`, `CZE`) và hai tên cố ý không nối; `Channel Islands` khớp nguyên văn (World Bank có
  mã `CHI`). Doanh thu nối được: 99.93%.
- World Bank `/country` trả 296 dòng, bỏ "Aggregates" còn 217 nước/vùng lãnh thổ.

| Nước | Doanh thu (GBP) | Khách | Khách lớn nhất | Dân số 2011 (triệu) | GDP/người 2011 (USD) | Doanh thu / triệu dân |
| --- | --- | --- | --- | --- | --- | --- |
| EIRE (Ireland) | 266 080 | 3 | 49% | 4.58 | 52 614 | 58 095 |
| Netherlands | 264 934 | 8 | 98% | 16.69 | 54 702 | 15 871 |
| Germany | 205 642 | 92 | 7% | 80.27 | 47 631 | 2 562 |
| France | 192 822 | 83 | 9% | 65.34 | 43 930 | 2 951 |
| Spain | 59 417 | 28 | 21% | 46.74 | 31 825 | 1 271 |
| Switzerland | 55 785 | 21 | 20% | 7.91 | 91 910 | 7 050 |
| Belgium | 37 969 | 25 | 12% | 11.04 | 47 761 | 3 440 |
| Sweden | 34 306 | 8 | 81% | 9.45 | 60 379 | 3 631 |

Ngoài châu Âu: Australia 137 488 GBP với 9 khách, khách lớn nhất 91%; Hong Kong 15 692 GBP, **không có dòng nào có
`Customer ID`**.

## Memo mẫu (rút gọn)

- **Khuyến nghị**: Đức và Pháp cho marketing thu hút khách mới (nhiều khách, không tập trung, độ thâm nhập thấp so với
  quy mô kinh tế); Ireland và Hà Lan là quan hệ tài khoản lớn, giữ bằng account manager.
- **Câu hỏi và cách đo**: câu hỏi đóng khung theo quyết định ngân sách; bốn chỉ số: doanh thu, số khách, độ tập trung,
  doanh thu trên triệu dân; vì sao không xếp theo doanh thu thô.
- **Kết quả**: bảng 4–6 nước, ba gạch đầu dòng có số (Hà Lan 98% một khách; Đức/Pháp thâm nhập thấp hơn Ireland
  khoảng 20 lần với GDP/người tương đương).
- **Độ tin cậy**: độ phủ 99.93%, các alias; doanh thu gộp; "nước" là địa chỉ khách khai, khách sỉ có thể bán lại khắp
  châu Âu; một năm dữ liệu.
- **Nguồn**: bộ, sheet, khoảng thời gian, định nghĩa doanh thu; API, chỉ số, năm, `lastupdated`, ngày tải, nơi lưu raw.
- **Bước tiếp theo**: tăng trưởng theo năm (ghép sheet 2009-2010), tỉ lệ quay lại của khách Đức/Pháp, rủi ro tập trung
  ở Hà Lan/Ireland.

## Các quyết định cần cân nhắc

- **Không nối thì không bịa**: `European Community` và `Unspecified` giữ là "không nối được" và báo phần doanh thu của
  chúng; đừng chia đều cho các nước.
- **Đo độ phủ trước khi đọc bảng ghép**: một alias thiếu (ví dụ `EIRE`) làm nước có doanh thu ngoài Anh lớn nhất biến
  mất khỏi bảng mà phép `join` không báo lỗi gì.
- **Năm của chỉ số khớp năm của doanh số** (2011), không lấy năm mới nhất cho tiện.
- **Chuẩn hoá theo quy mô** (doanh thu trên triệu dân, hoặc trên GDP) trả lời "còn dư địa không"; doanh thu thô trả lời
  "ai đang mua nhiều". Câu hỏi của Sales Director là câu thứ nhất.
- **Độ tập trung**: số khách và phần của khách lớn nhất quyết định một nước là "thị trường" hay "vài tài khoản".
- **Tái lập**: JSON thô có `lastupdated`, ngày tải; định nghĩa doanh thu ghi trong memo.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Nối nguồn và độ phủ | 20 | Alias có lý do, tên không phải nước để "không nối", báo độ phủ có số |
| Chỉ số đúng câu hỏi | 20 | Có chỉ số chuẩn hoá theo quy mô và chỉ số tập trung khách; năm khớp nhau |
| Kết luận và khuyến nghị | 20 | Kết luận trước, khác với "xếp theo doanh thu", có hành động cho cả nhóm nước tập trung |
| Độ tin cậy | 15 | Nêu ít nhất ba giới hạn có nội dung (ghép tên, doanh thu gộp, địa chỉ khách, một năm) |
| Nguồn và tái lập | 15 | Đủ để người khác lấy lại đúng số: bộ, sheet, thời gian, định nghĩa, API, chỉ số, `lastupdated`, ngày tải |
| Văn phong | 10 | Viết cho Sales Director, ngắn, bảng gọn, không thuật ngữ thừa |

Từ 70 điểm trở lên là memo đủ gửi Sales Director.
