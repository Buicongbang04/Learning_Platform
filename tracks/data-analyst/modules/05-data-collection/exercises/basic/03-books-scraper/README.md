---
title: Scraper lịch sự với BeautifulSoup - danh mục books.toscrape.com
level: basic
services: []
files:
  - path: starter/books_scraper.ipynb
    note: 5 hàm TODO; cell explore crawl website sandbox thật
  - path: tests/test_books_scraper.py
    note: Không sửa; test dùng 2 trang HTML đã lưu, không gọi mạng
run:
  - uv run jupyter lab tracks/data-analyst/modules/05-data-collection/exercises/basic/03-books-scraper/starter/books_scraper.ipynb
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/basic/03-books-scraper -q
---

## Mục tiêu

Viết một scraper nhỏ đúng cách: parse HTML bằng BeautifulSoup theo cấu trúc trang, ghép URL tương đối, kiểm
`robots.txt`, nghỉ giữa các request, có giới hạn và chống lặp; rồi biết khi nào số scrape được **không** đủ để kết
luận.

## Đề bài

[books.toscrape.com](https://books.toscrape.com) là nhà sách giả do Zyte (Scrapinghub) dựng để luyện scraping: 1 000
sách trên 50 trang danh mục; tên sách thật, còn giá, số sao, tồn kho là dữ liệu giả. `tests/fixtures/page-1.html` và
`page-50.html` là trang đầu và trang cuối, lưu nguyên bytes ngày 30/10/2026.

Team pricing muốn theo dõi giá đối thủ; bạn dựng bản mẫu trên sandbox. Mở `starter/books_scraper.ipynb`:

1. `parse_price(text)`: số trong chuỗi giá, chịu được `£`, `Â£`, dấu phẩy hàng nghìn.
2. `parse_listing(html, page_url)`: `title` (đầy đủ, từ thuộc tính `title`), `price`, `rating` 1–5, `in_stock`, `url`
   tuyệt đối của từng sách.
3. `next_page(html, page_url)`: URL trang kế tiếp hoặc `None`.
4. `robots_allows(robots_txt, url, agent)`: dùng `urllib.robotparser`, `None` (không có tệp) là cho phép.
5. `crawl(fetch, start_url, max_pages, delay, sleep)`: theo nút next, nghỉ `delay` giây giữa các request, dừng ở trang
   cuối, ở `max_pages`, hoặc khi gặp lại URL đã tải; bỏ trùng theo `url`.
6. Chạy các cell `explore`: kiểm `robots.txt`, crawl cả danh mục (khoảng 1–2 phút), so giá theo số sao. Báo cáo bài
   học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên hai trang đã lưu pass: trang 1 có 20 sách, sách đầu là *A Light in the Attic* giá 51.77, 3 sao; tổng giá
  trang 1 là 760.97; trang 50 không có trang kế; `crawl` nghỉ đúng một lần giữa hai trang, dừng ở `max_pages`, không
  lặp vô hạn khi trang trỏ ngược lại.
- Trên website thật: 1 000 sách, 1 000 URL, 999 tiêu đề khác nhau.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`soup.select("article.product_pod")` trả danh sách thẻ sách. Trong mỗi thẻ: `pod.select_one("h3 a")["title"]`,
`pod.select_one("p.star-rating")["class"]` là list như `["star-rating", "Three"]`.

### Gợi ý 2

`crawl`: giữ một `set` các URL đã tải; vòng `while url and url not in seen and len(seen) < max_pages`. Gọi `sleep` ở
đầu vòng nếu `seen` đã có phần tử. Gom mọi dict vào một list rồi tạo DataFrame một lần ở cuối.
