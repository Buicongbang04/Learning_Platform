# Lời giải: scraper lịch sự cho books.toscrape.com

## Cách làm

- `parse_price`: bỏ dấu phẩy rồi `re.search(r"\d+(?:\.\d+)?", ...)`. Không cố khớp ký hiệu tiền: ký hiệu có thể bị giải
  mã sai (`Â£`), có thể là `€` hay `GBP`; phần cần giữ là con số. Không thấy số thì báo lỗi to, đừng trả `0`.
- `parse_listing`: `BeautifulSoup(html, "lxml")` nhận cả `bytes` lẫn `str`; khi nhận `bytes` nó tự đọc thẻ
  `<meta charset="utf-8">` nên không bị lỗi `Â£`. Mỗi `article.product_pod` lấy `h3 a["title"]` (tiêu đề đầy đủ),
  class thứ hai của `p.star-rating`, chữ `In stock` trong `p.availability`, và `urljoin(page_url, href)`: `href` là
  `a-light-in-the-attic_1000/index.html`, tương đối với thư mục `catalogue/`.
- `next_page`: `select_one("li.next a")`, ghép với URL trang hiện tại.
- `robots_allows`: `RobotFileParser().parse(lines)` rồi `can_fetch(agent, url)`; `None` nghĩa là không có tệp (HTTP 4xx),
  theo RFC 9309 là không giới hạn. Lỗi 5xx khi tải `robots.txt` thì nên coi như **cấm** và thử lại sau.
- `crawl`: vòng lặp với ba điều kiện dừng (hết trang, đủ `max_pages`, gặp lại URL), `sleep` giữa hai request, gom
  dict rồi tạo DataFrame một lần, `drop_duplicates("url")`.

Notebook truyền `fetch` dùng `httpx` (User-Agent tự giới thiệu, timeout, `raise_for_status`, trả `resp.content` là
bytes). Test truyền hàm giả, nên logic crawl kiểm được mà không cần mạng: tách "tải" khỏi "xử lý" là thói quen giúp mọi
bộ thu thập dữ liệu test được.

## Con số trên website thật (30/10/2026)

| Đại lượng | Giá trị |
| --- | --- |
| `robots.txt` | HTTP 404 (không có tệp) |
| Sách / URL / tiêu đề khác nhau | 1 000 / 1 000 / 999 (*The Star-Touched Queen* có hai cuốn, giá 46.02 và 32.30) |
| Giá | 10.00 tới 59.99, trung bình 35.07, trung vị 35.98 |
| Giá trung bình theo số sao 1 → 5 | 34.56, 34.81, 34.69, 36.09, 35.37 |
| Tương quan giá - số sao | 0.028 |
| Tỉ lệ còn hàng | 100% |

## Giải thích trắc nghiệm

- **robots-404 (b)**: không có `robots.txt` (404) nghĩa là website không đặt giới hạn. Vẫn phải crawl lịch sự: nghỉ
  giữa request, User-Agent thật, không tải lại thứ đã có.
- **catalog-size (a)**: 1 000 URL nhưng 999 tiêu đề; bỏ trùng theo tiêu đề sẽ mất một cuốn có giá khác.
- **dedupe-key (d)**: định danh là thứ website dùng để phân biệt bản ghi (URL hoặc mã sản phẩm/UPC), không phải tên.
- **rating-price (a)**: 35.37 so với 34.56, chênh 0.81 GBP trên giá 35 GBP; tương quan 0.03.
- **sandbox-insight (c)**: giá và số sao ở sandbox được sinh ngẫu nhiên, nên "không có quan hệ" là tính chất của bộ
  sinh dữ liệu, không phải của thị trường. Bài học lớn hơn: trước khi kết luận, hỏi dữ liệu đến từ đâu, ai tạo ra.
- **mojibake (b)**: header là `Content-Type: text/html` không có `charset`; `requests` theo chuẩn HTTP cũ mặc định
  ISO-8859-1 cho `text/*`, nên hai byte UTF-8 của `£` thành `Â£`. Sửa: dùng `r.content` (bytes) cho BeautifulSoup, hoặc
  đặt `r.encoding = r.apparent_encoding`. `httpx` đoán UTF-8 nên không gặp lỗi này.
- **truncated-title (c)**: chữ hiển thị là `A Light in the ...` với tên dài; thuộc tính `title` có tên đầy đủ. Luôn
  so vài dòng scrape được với trang thật trên trình duyệt.
- **real-competitor (a, b, c, e)**: ToS, API chính thức, dữ liệu cá nhân (Luật Bảo vệ dữ liệu cá nhân 2025 ở Việt Nam, GDPR ở
  châu Âu), tần suất. Giả User-Agent trình duyệt để lách chặn (d) là dấu hiệu bạn đang làm điều website không muốn;
  nếu bị chặn, dừng lại và hỏi pháp chế.
