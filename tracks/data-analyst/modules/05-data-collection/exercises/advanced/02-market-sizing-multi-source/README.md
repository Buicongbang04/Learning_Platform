---
title: Ghép doanh số nội bộ với World Bank để chọn thị trường châu Âu - nối tên nước, độ phủ, memo
level: advanced
services: []
files:
  - path: starter/market_sizing.ipynb
    note: 2 hàm TODO + phân tích trong cell explore (Excel thật + World Bank API)
  - path: starter/MEMO.md
    note: Memo 6 mục cho Sales Director
  - path: tests/test_market_sizing.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/05-data-collection/exercises/advanced/02-market-sizing-multi-source/starter/market_sizing.ipynb
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/advanced/02-market-sizing-multi-source -q
---

## Mục tiêu

Làm trọn một câu hỏi cần hai nguồn: dữ liệu nội bộ và dữ liệu công khai qua API. Phần khó là chỗ nối (tên nước khác
nhau, phần không nối được), đo độ phủ trước khi tin bảng ghép, nhận ra chỉ số "doanh thu theo nước" bị vài khách lớn
chi phối, và ghi nguồn đủ để người khác lấy lại đúng số.

## Đề bài

Tháng 12/2011, Sales Director hỏi: *"Ngoài Anh, năm 2012 nên dồn ngân sách marketing vào nước châu Âu nào?"*

- Nội bộ: `online-retail-ii` (UCI, CC BY 4.0), sheet `Year 2010-2011`, doanh thu dòng hợp lệ tháng 1–11/2011 theo
  `Country`, số khách, phần doanh thu của khách lớn nhất.
- Công khai: World Bank Indicators API v2 (CC BY 4.0, không cần key): danh sách nước, `SP.POP.TOTL`, `NY.GDP.PCAP.CD`
  năm 2011.

Mở `starter/market_sizing.ipynb`:

1. `match_countries(names, wb_countries, aliases)`: nối tên nội bộ với mã ISO3 của World Bank (alias trước, rồi khớp tên
   không phân biệt hoa thường), alias sai mã thì `ValueError`.
2. `coverage(revenue, matched)`: phần doanh thu nối được, tên không nối được theo thứ tự doanh thu.
3. Chạy và sửa các cell `explore`: quyết định alias, kiểm độ phủ, lấy chỉ số World Bank (lưu JSON thô kèm
   `lastupdated`), dựng bảng xếp hạng châu Âu, biểu đồ. Được thêm chỉ số của riêng bạn.
4. Viết `starter/MEMO.md` 6 mục theo thứ tự có sẵn, 300–1 000 từ.

## Tiêu chí đạt

- Test pass: `match_countries` đúng thứ tự và `method` trên dữ liệu nhỏ, bắt alias sai mã; `coverage` đúng; MEMO đủ mục,
  không còn TODO.
- Bảng ghép nối được hơn 99.9% doanh thu 01–11/2011; tên không nối được chỉ còn những tên không phải một nước.
- Nội dung phân tích và memo chấm theo rubric trong `SOLUTION.md` (đạt từ 70/100).

## Gợi ý

### Gợi ý 1

In danh sách tên nội bộ không khớp nguyên văn với World Bank trước khi viết alias. Mỗi alias là một quyết định: `EIRE`
là Ireland; `European Community` không phải một nước, nối nó với một nước bất kỳ là bịa.

### Gợi ý 2

Trước khi gọi một nước là "thị trường", xem có bao nhiêu khách và khách lớn nhất chiếm bao nhiêu phần doanh thu. Một
nước có 3 khách là một danh sách tài khoản, không phải một thị trường để chạy quảng cáo.
