# Câu hỏi phỏng vấn: Thu thập dữ liệu

## Bạn nhận một câu hỏi phân tích cần dữ liệu chưa có sẵn. Bạn hỏi gì trước khi bắt đầu lấy?

Bốn nhóm câu hỏi, theo thứ tự:

1. **Quyết định và độ chính xác**: số này dùng để quyết định gì, sai bao nhiêu thì quyết định đổi, lấy một lần hay lặp
   lại? Việc một lần cho slide khác hẳn việc hằng ngày cho dashboard.
2. **Chủ sở hữu và đường chính thức**: dữ liệu đã có trong warehouse chưa, ai sở hữu nguồn, có API hay export có
   control total không? Đường chính thức gần như luôn rẻ hơn tự lấy, vì phần kiểm số đã có người làm.
3. **Tác động lên nguồn**: truy vấn có đè tải lên database production không, API có rate limit không, crawl có làm chậm
   website của người khác không?
4. **Được phép không**: điều khoản sử dụng, dữ liệu cá nhân, bản quyền; mật khẩu và API key giữ ở đâu.

Câu trả lời tốt kết thúc bằng thứ tự ưu tiên: warehouse → read replica / export chính thức → API → scraping, và nói rõ
mỗi bậc đi xuống là thêm việc kiểm và thêm rủi ro. Câu trả lời yếu bắt đầu bằng công cụ ("tôi viết scraper bằng Python").

## Vì sao DA không nên chạy truy vấn phân tích trên database production của ứng dụng?

Database production phục vụ khách hàng: mỗi truy vấn quét cả bảng hay join lớn của DA tranh tài nguyên với request của
người dùng, có thể khoá bảng, làm chậm thanh toán. Cách đúng:

- **Read replica**: bản sao chỉ đọc, trễ vài giây, đủ cho mọi phân tích không cần thời gian thực.
- **Warehouse**: dữ liệu đã được DE đưa sang, có mô hình, có tài liệu; truy vấn ở đây rẻ và an toàn.
- **Tài khoản chỉ đọc**, có giới hạn thời gian chạy truy vấn.

Kèm theo nguyên tắc "đưa tính toán tới gần dữ liệu": tổng hợp bằng SQL ngay trong database, chỉ kéo bảng kết quả về
pandas. Kéo 50 triệu dòng về để `groupby` thành 90 con số là tốn cho cả hai phía.

## Bind parameter là gì? Vì sao một DA cũng phải quan tâm tới SQL injection?

Bind parameter là chỗ giữ trong câu SQL (`WHERE invoice_date >= :start`) mà giá trị được gửi **tách khỏi** câu lệnh:
database không bao giờ hiểu giá trị là một phần của SQL.

```python
from sqlalchemy import text

sql = text("SELECT COUNT(*) FROM sales WHERE invoice_date >= :start AND country = :country")
params = {"start": "2011-11-01", "country": "France"}  # conn.execute(sql, params)
```

Ghép chuỗi bằng f-string hỏng ngay khi giá trị có dấu nháy (`Côte d'Ivoire`), và thành lỗ hổng khi giá trị đến từ người
dùng: filter trên app Streamlit nội bộ, tham số trên dashboard. DA ngày càng hay viết những app như vậy. Thêm lợi ích phụ:
database cache được kế hoạch thực thi cho câu lệnh có tham số.

## Đối tác gửi một file CSV doanh số. Những gì có thể sai, và bạn kiểm gì trước khi tính?

Những thứ có thể sai, theo thứ tự từ "lỗi to" tới "sai âm thầm":

| Vấn đề | Hậu quả |
| --- | --- |
| Encoding (cp1252 thay cho UTF-8) | `UnicodeDecodeError`: lỗi to, tốt |
| Delimiter `;` | Bảng 1 cột, không lỗi |
| Dấu thập phân `,` | Cột giá thành chuỗi; `giá * số lượng` lặp chuỗi, không lỗi |
| Ngày dd/mm | `01/11` thành 11 tháng 1; ngày > 12 thành `NaT` |
| Mã có số 0 đầu, mã lẫn chữ | `02113` thành `2113`, join lệch |
| Dòng mở đầu, dòng tổng | Tiêu đề sai, dòng tổng bị cộng như dữ liệu |

Trên một export thật 1 580 dòng (khách Pháp tháng 11/2011 của Online Retail II, định dạng ERP kiểu Pháp): đọc mặc định thì
lỗi encoding; sửa encoding thì ra bảng 1 583 dòng × 1 cột; đọc ngày theo kiểu tháng trước thì 685 dòng parse "được" nhưng
sai tháng và 895 dòng thành `NaT`. Kiểm sau khi đọc: `df.shape`, `df.dtypes`, khoảng ngày, số dòng so với **control total**
của hệ thống nguồn, vài tổng quen thuộc. Và xin Parquet hoặc tệp gốc từ hệ thống nếu được, thay vì tệp đã qua Excel.

## Vì sao pandas đọc cột mã khách thành `12674.0`? Sửa thế nào?

Cột số nguyên có ít nhất một ô trống: pandas biểu diễn ô trống bằng `NaN`, mà `NaN` là số thực, nên cả cột thành `float64`.
Hậu quả: mã `12674.0` không khớp mã `12674` (int) hay `"12674"` (chuỗi) ở bảng khác khi join; xuất ra CSV thành `12674.0`.

Sửa: `dtype={"Customer ID": "Int64"}` (số nguyên cho phép thiếu, chữ I hoa) khi đọc, hoặc đọc mọi cột mã là chuỗi
(`dtype=str`) vì mã không phải để cộng trừ. Cột `Invoice` của Online Retail II lẫn `536365` và `C536379`: đọc là chuỗi
ngay từ đầu, đừng để mỗi lần đọc ra một kiểu.

## API trả dữ liệu theo trang. Có những kiểu phân trang nào, và làm sao biết bạn đã lấy đủ?

| Kiểu | Đi trang | Dừng |
| --- | --- | --- |
| Page number | `page=1, 2, ...` | `page >= pages` |
| Offset/limit | `offset += limit` | Trang ngắn hơn `limit` |
| Cursor | `cursor = response["next_cursor"]` | Không còn cursor |
| Link header | URL `rel="next"` trong header | Không còn link |

Lấy đủ: **so số bản ghi nhận được với `total`** khi API có trường đó; không có thì đếm theo cách khác (gọi lại với bộ lọc
hẹp hơn, so với báo cáo của nguồn). Thiếu trang không gây lỗi nào. Ví dụ World Bank: 10 nước ASEAN × 9 năm = 90 bản ghi,
`per_page=50` thì `pages = 2`; chỉ đọc trang 1 là thiếu 40 bản ghi mà code vẫn chạy "thành công".

Thêm một bẫy: dữ liệu thay đổi giữa hai lần gọi trang (bản ghi mới chèn vào đầu) làm trùng hoặc sót ở ranh giới trang.
Cursor hoặc lọc theo một mốc thời gian cố định tránh được.

## API trả 429. Bạn xử lý retry thế nào? Lỗi nào không được thử lại?

- **Thử lại**: lỗi mạng, timeout, 429, 500, 502, 503, 504. Chờ đúng `Retry-After` nếu header có; không thì backoff mũ
  (1, 2, 4, 8 giây, có thể thêm jitter ngẫu nhiên để nhiều client không thử lại cùng lúc); giới hạn số lần, hết lần thì báo
  lỗi rõ ràng.
- **Không thử lại**: 400 (tham số sai), 401/403 (sai quyền), 404. Gửi lại request sai vẫn sai, chỉ tốn quota.
- **Phòng hơn chữa**: tự giới hạn tốc độ dưới mức cho phép, tăng `per_page` để giảm số request, cache response đã lấy.

Trong test, thay tầng mạng bằng server giả (`httpx.MockTransport`) trả lần lượt 503, 429 kèm `Retry-After: 7`, rồi 200,
và truyền hàm `sleep` giả để kiểm client đã chờ đúng `[1, 7]` giây mà test không phải chờ thật.

## API trả HTTP 200 nhưng bảng của bạn rỗng. Bạn nghĩ tới những khả năng nào?

1. **Lỗi nằm trong body**: World Bank trả `200` với `[{"message": [{"key": "Invalid value"}]}]` khi tên chỉ số sai.
   Client chỉ kiểm status sẽ lấy phần tử thứ hai, gặp lỗi khó hiểu hoặc trả rỗng.
2. **Không có dữ liệu thật**: bộ lọc hợp lệ nhưng không khớp gì (`[metadata, None]`, `total = 0`); ví dụ năm chưa có số.
3. **Phân trang sai**: offset bắt đầu từ 1 thay vì 0, hoặc trang đầu là 0.
4. **Quyền**: một số API trả 200 với danh sách rỗng khi key không có quyền xem dữ liệu.
5. **Đổi phiên bản API**: tên trường đổi, parser không tìm thấy gì.

Cách phòng: kiểm cấu trúc body, báo lỗi khi kết quả rỗng mà không mong đợi rỗng, log URL (đã che key) và metadata của
response để tái hiện.

## Bạn giữ API key thế nào? Lỡ commit key vào git thì làm gì?

Key là mật khẩu: không viết trong code hay notebook, không dán vào chat. Đọc từ biến môi trường, đặt trong tệp `.env` nằm
trong `.gitignore`, hoặc dùng secret manager của công ty. Gửi key qua header thay vì query string khi API cho phép, vì URL
hay bị ghi vào log; nếu buộc phải để trong URL thì che key trước khi log hay lưu metadata.

Lỡ commit: **thu hồi key và cấp key mới ngay**, rồi mới dọn lịch sử git. Xoá dòng trong commit sau không đủ: lịch sử giữ
key mãi, repo có thể đã được clone, và có bot quét GitHub tìm key trong vài phút. Xoá output của notebook cũng không xoá
key nằm trong source cell.

## Scraping có hợp pháp không? Bạn kiểm gì trước khi scrape một website?

Không có câu trả lời chung; kiểm ba lớp, không lớp nào thay được lớp khác:

- **`robots.txt`** (RFC 9309): website muốn bot làm gì. Là quy ước kỹ thuật, không phải giấy phép.
- **Điều khoản sử dụng**: có cấm thu thập tự động không. Vụ hiQ Labs với LinkedIn ở Mỹ cho thấy dữ liệu công khai vẫn có
  thể dẫn tới vi phạm thoả thuận người dùng.
- **Dữ liệu cá nhân và bản quyền**: tên, số điện thoại, email của người dùng là dữ liệu cá nhân (Việt Nam: Luật Bảo vệ dữ
  liệu cá nhân 2025, trước đó Nghị định 13/2023/NĐ-CP; châu Âu: GDPR). "Công khai" không có nghĩa là được dùng cho mục đích
  khác.

Trước khi scrape: có API, feed, tệp tải hay dữ liệu mua được không? Nếu vẫn scrape: User-Agent thật, nghỉ giữa request,
giới hạn số trang, chạy giờ thấp điểm, không lách chặn. Nghi ngờ về pháp lý thì hỏi pháp chế; đó không phải quyết định
của DA.

## Case: scraper giá đối thủ chạy hằng ngày, sáng nay báo 0 sản phẩm. Bạn làm gì?

1. **Chặn số sai đi tiếp**: dashboard không được hiện "giá đối thủ = trống" như thể đối thủ hết hàng. Đánh dấu ngày hôm
   nay là thiếu dữ liệu.
2. **Xem raw**: HTML lưu lại của hôm nay có gì? Ba khả năng chính: website đổi cấu trúc (class `product_pod` không còn),
   bị chặn (trang captcha, 403, 429), hoặc nội dung chuyển sang tải bằng JavaScript.
3. **Sửa theo nguyên nhân**: đổi cấu trúc thì sửa selector và **parse lại từ raw** những ngày bị ảnh hưởng; bị chặn thì
   dừng, không lách (đổi IP, giả trình duyệt), xem lại tần suất và hỏi lại điều khoản; JavaScript thì xem tab Network có API
   JSON nào không.
4. **Phòng lần sau**: kiểm số bản ghi mỗi lần chạy (một trang danh mục phải có 20 sản phẩm), cảnh báo khi lệch nhiều so
   với hôm qua, và một test parser trên trang mẫu đã lưu.

Điểm cộng: nói về người dùng số liệu (team pricing biết khi nào số không có) trước khi nói về code.

## Idempotent nghĩa là gì trong thu thập dữ liệu? Bạn làm một lần nạp thành idempotent thế nào?

Chạy lại cùng một lần nạp cho **cùng kết quả**: không nhân đôi dòng, không mất dòng. Cần vì job sẽ bị chạy lại (lỗi mạng,
người chạy tay hai lần, backfill).

- **Xoá rồi ghi theo phân vùng** (batch, ngày) trong **một transaction**: lỗi giữa chừng thì rollback, dữ liệu cũ còn.
- **Upsert theo khoá** (`INSERT ... ON CONFLICT (city, date) DO UPDATE`): hợp khi có khoá tự nhiên và nguồn sửa số cũ.
- **Tệp**: ghi qua tệp tạm rồi `os.replace` để không ai đọc được tệp ghi dở.

Ví dụ thật: nạp Online Retail II vào SQLite theo batch `2009-2010` và `2010-2011`; nạp lại batch `2010-2011` vẫn còn
1 044 848 dòng. Bảng dòng hoá đơn không có khoá tự nhiên (một hoá đơn có thể có hai dòng giống hệt nhau), nên dùng
xoá-rồi-ghi theo batch chứ không upsert.

## Ghép hai file dữ liệu của cùng một nguồn, làm sao biết chúng có chồng nhau?

Kiểm **khoảng thời gian** và **khoá** trước khi `concat`: min/max ngày của từng tệp, và số dòng trùng trên khoá (hoặc trên
mọi cột nếu không có khoá). Hai sheet của Online Retail II trùng nhau từ 01/12 tới 09/12/2010: 22 523 dòng. Ghép thẳng thì
doanh thu tháng 12/2010 thành 1.26 triệu thay vì 0.82 triệu GBP, cao thêm 53%, vì 9 ngày đầu tháng 12 là mùa mua quà Giáng
sinh và chiếm hơn nửa doanh thu tháng. Nhân đôi kiểu này không làm code lỗi; chỉ đối chiếu (số dòng, tổng theo tháng so
với nguồn) mới thấy.

## Vì sao lưu dữ liệu thô kèm metadata trước khi làm sạch?

- **Tái lập**: số trên slide truy ngược được về response cụ thể, lấy lúc nào, với tham số nào.
- **Nguồn sửa số**: World Bank cập nhật số liệu theo đợt (`lastupdated` trong metadata), dữ liệu thời tiết gần đây được
  sửa khi mô hình cập nhật. Có raw cũ thì so được "số đổi từ bao nhiêu thành bao nhiêu".
- **Sửa parser không cần gọi lại nguồn**: tiết kiệm quota, không phụ thuộc nguồn còn trả dữ liệu cũ hay không.
- **Kiểm toàn vẹn**: `sha256`, `n_bytes` cho biết tệp có bị cắt, hai lần tải có khác nhau không.

Metadata tối thiểu: URL và tham số (đã che key), thời điểm tải, phiên bản/ngày cập nhật của nguồn, hash, giấy phép.

## Case: Head of Expansion cần số để chọn thị trường thứ hai trong ASEAN. Bạn lấy dữ liệu và trình bày thế nào?

Lấy từ nguồn chính thức có giấy phép: World Bank API (dân số `SP.POP.TOTL`, GDP/người `NY.GDP.PCAP.CD`, tỉ lệ dùng internet
`IT.NET.USER.ZS`), lưu JSON thô kèm `lastupdated`. Dựng chỉ số quy mô "dân số online" = dân số × tỉ lệ dùng internet.

Năm 2023: Indonesia khoảng 195 triệu người dùng internet, Philippines khoảng 90 triệu, Việt Nam khoảng 78 triệu, Thái Lan
khoảng 64 triệu. Myanmar thiếu tỉ lệ internet 2021–2023: để trống và ghi chú, không điền 0. Trình bày: quy mô cạnh sức mua
(GDP/người của Thái Lan, Malaysia gấp 1.5–2.5 lần Indonesia, Philippines, Việt Nam), và nói rõ dân số online là chỉ số quy
mô, chưa phải độ hấp dẫn: còn logistics, quy định TMĐT, đối thủ, chi phí thu hút khách. Câu trả lời yếu: scrape một bảng
Wikipedia và đưa một bảng xếp hạng theo dân số.

## Case: ghép doanh số nội bộ theo quốc gia với dữ liệu World Bank. Những bẫy nào bạn đề phòng?

1. **Tên không khớp**: dữ liệu Online Retail II ghi `EIRE`, `RSA`, `USA`, `Czech Republic`, `Hong Kong`; World Bank ghi
   `Ireland`, `South Africa`, `United States`, `Czechia`, `Hong Kong SAR, China`. Nối bằng mã ISO3 qua bảng alias có chủ
   đích; `European Community`, `Unspecified` không phải một nước, để "không nối được".
2. **Đo độ phủ**: phần doanh thu nối được (99.93% sau alias). Thiếu alias `EIRE` là mất nước có doanh thu ngoài Anh lớn
   nhất, và `join` không báo lỗi gì.
3. **Năm khớp nhau**: doanh số 2011 thì dân số, GDP năm 2011.
4. **Độ tập trung**: Hà Lan có doanh thu 265 nghìn GBP năm 2011 nhưng một khách chiếm 98%; Ireland 266 nghìn GBP từ 3
   khách. Đó là vài tài khoản lớn, không phải thị trường. Đức (92 khách) và Pháp (83 khách) mới là nền khách hàng rộng.

## Khi nào bạn dùng requests/httpx, Scrapy, Playwright, hay một công cụ như Airbyte? Vì sao chọn công cụ đó?

| Tình huống | Chọn | Vì sao |
| --- | --- | --- |
| Gọi một API trong notebook, vài chục request | httpx (hoặc requests) | Đơn giản; httpx có timeout mặc định và `MockTransport` để test |
| Scrape vài chục trang tĩnh, một lần | httpx + BeautifulSoup | Đủ dùng, dễ đọc, dễ kiểm |
| Crawl hàng chục nghìn trang, chạy định kỳ | Scrapy | Có sẵn hàng đợi, giới hạn tốc độ, retry, pipeline lưu trữ |
| Nội dung chỉ hiện sau JavaScript, không có API nội bộ | Playwright | Làm như trình duyệt thật; chậm và dễ vỡ nên là phương án cuối |
| Kéo hằng ngày từ CRM, quảng cáo, thanh toán vào warehouse | Airbyte / Fivetran | Connector có sẵn lo phân trang, rate limit, đổi schema; thường do DE quản |

Lý do chọn luôn quay về: làm một lần hay lặp lại, bao nhiêu dữ liệu, ai bảo trì khi nguồn đổi. Viết một client tự chế cho
nguồn có connector chuẩn là tạo ra thứ phải bảo trì mãi.

## SQLite, DuckDB hay Postgres cho dữ liệu phân tích của bạn và team nhỏ? Vì sao?

- **SQLite**: một tệp, không cần server, có transaction và upsert. Hợp để một người (hoặc một job) nạp và nhiều notebook
  đọc. Online Retail II hai sheet (1 044 848 dòng) nạp vào SQLite trong khoảng 15 giây, truy vấn doanh thu 25 tháng dưới 1
  giây, so với khoảng một phút để đọc lại tệp Excel mỗi lần.
- **DuckDB**: cũng là một tệp, nhưng tối ưu cho phân tích (lưu theo cột), đọc thẳng CSV/Parquet; nhanh hơn SQLite nhiều
  với truy vấn tổng hợp trên bảng lớn. Hợp cho phân tích trên máy.
- **Postgres**: server, nhiều người ghi cùng lúc, phân quyền, BI tool kết nối qua mạng. Hợp khi bảng thành tài sản chung
  của team hay nguồn cho dashboard.

Viết code qua SQLAlchemy và SQL di động thì chuyển từ SQLite sang Postgres chỉ là đổi URL; bài tập của module kiểm đúng
điều đó.
