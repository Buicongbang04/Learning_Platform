# Hướng làm: review PR notebook "thêm năm 2009-2010 để so YoY"

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, các vấn đề trong PR (đã đo trên dữ liệu
thật), một bản review mẫu rút gọn và rubric.

## `nbreview.py`

- **`strip_outputs`**: `copy.deepcopy(nb)`, lọc `metadata` notebook theo `KEEP_NB_META`, mỗi cell bỏ khoá trong
  `DROP_CELL_META`, cell code đặt `outputs = []`, `execution_count = None`. Chạy hai lần như một lần (idempotent) là
  điều kiện để dùng làm git filter.
- **`cell_diff`**: chuẩn hoá `source` (list → chuỗi), tạo list `(cell_type, source)`, duyệt `get_opcodes()`; khối
  `replace` ghép cặp theo vị trí, phần dư là `removed`/`added`. Diff:
  `"\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm=""))`.

Trên PR này mọi cell code đều đổi (5 `changed`) và có 1 cell thêm; diff theo cell đọc được trong một màn hình, trong khi
`git diff` thô của hai tệp JSON có output sẽ dài hàng trăm dòng.

## Các vấn đề trong PR

| # | Cell | Vấn đề | Chặn merge? | Đo trên dữ liệu thật |
| --- | --- | --- | --- | --- |
| 1 | 1 | `pd.concat` hai sheet không bỏ phần trùng 01–09/12/2010 | Có | 45 046 dòng trong khoảng đó (mỗi sheet 22 523); doanh thu 12/2010 thành 1 262 599 thay vì 823 746 GBP (+53.3%); YoY 12/2010 +52.9% thay vì −0.2% |
| 2 | 1 | Đường dẫn tuyệt đối `/home/minh/...` | Có | Không ai khác chạy được; CI không chạy được |
| 3 | 2 | Bỏ bộ lọc `C` và `Price > 0` ("hiếm") | Có | Lý do "C luôn có Quantity âm" đúng ở sheet 2010-2011 nhưng sheet 2009-2010 có 1 dòng `C` số lượng dương. Dòng giá âm (điều chỉnh nợ xấu) chỉ 5 dòng nhưng −136 552 GBP năm 2010 và −22 124 GBP tháng 8/2011: YoY 4/2011 thành −14.4% thay vì −21.1%, 7/2011 +18.6% thay vì +10.5%, **10/2011 +2.5% thay vì −0.9% (đổi dấu)** |
| 4 | 3 | `customers` đổi `nunique` → `count` | Có | Khách 11/2011: 64 545 thay vì 1 664 (đếm dòng có mã khách) |
| 5 | 3, 5 | YoY tháng 12/2011 so 9 ngày với cả tháng 12/2010 | Không chặn, phải ghi chú | −49.4% (PR) / −22.5% (sau khi sửa): cả hai đều vô nghĩa |
| 6 | 3 | `pct_change(12)` giả định không thiếu tháng | Không | Đúng trên bộ này (25 tháng liên tục), nên ghi giả định |
| 7 | 4 | Chart dùng `fig, ax`, bỏ khung | Không (tốt) | |

Bảng tham chiếu sau khi sửa (hai sheet, bỏ trùng, định nghĩa chung):

| Tháng | Doanh thu | Khách | YoY |
| --- | --- | --- | --- |
| 12/2010 | 823 746 | 885 | −0.2% |
| 4/2011 | 537 809 | 856 | −21.1% |
| 8/2011 | 759 138 | 935 | +8.9% |
| 10/2011 | 1 154 979 | 1 364 | −0.9% |
| 11/2011 | 1 509 496 | 1 664 | +2.7% |

## Review mẫu (rút gọn)

- **Tóm tắt**: PR đọc hai sheet và thêm YoY; 5 cell đổi, 1 cell thêm; ba cell đổi số liệu.
- **Chặn merge**: (1) bỏ trùng 01–09/12/2010 khi ghép; (2) bỏ đường dẫn tuyệt đối; (3) giữ nguyên bộ lọc làm sạch của
  team, lý do "hiếm" sai về số tiền; (4) `customers` trả về `nunique`.
- **Ảnh hưởng**: bảng trên, nhấn mạnh YoY 12/2010 (+52.9% → −0.2%) và YoY 10/2011 đổi dấu: đây là bảng CEO sẽ xem.
- **Không chặn**: chú thích tháng 12/2011 chưa đủ; ghi giả định của `pct_change(12)`; chart mới tốt hơn.
- **Kết luận**: Request changes; approve khi bốn điểm được sửa và mô tả PR có bảng con số trước/sau.

## Các quyết định cần cân nhắc

- **Chặn hay không**: chặn khi con số đi tới người ra quyết định bị sai; phong cách không chặn. Một review chặn vì tên
  biến trong khi bỏ qua phần trùng dữ liệu là review sai trọng tâm.
- **Kiểm lý do của tác giả bằng dữ liệu**, không bằng niềm tin: "hiếm" phải hỏi "hiếm theo dòng hay theo tiền".
- **Viết để tác giả sửa được**: mỗi vấn đề có cell, dòng, đề xuất sửa cụ thể, con số chứng minh.
- **Đề xuất phòng ngừa**: test reconcile (tổng doanh thu theo tháng của sheet 2010-2011 phải khớp bản đã chốt), đưa
  `clean_transactions` vào module dùng chung (Advanced 01), nbstripout cho repo.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| `nbreview.py` | 15 | Pass test; code ngắn, dùng `difflib`, không sửa đầu vào |
| Tìm vấn đề chặn | 30 | Đủ 4 vấn đề 1–4 (thiếu một trừ 7 điểm); không chặn vì lý do phong cách |
| Đo ảnh hưởng | 25 | Có bảng trước/sau từ dữ liệu thật, có YoY 12/2010 và ít nhất một tháng YoY đổi dấu hoặc đổi mạnh vì dòng giá âm |
| Kiểm lý do của tác giả | 10 | Nói rõ "C luôn âm" gần đúng nhưng không đủ để bỏ bộ lọc, "giá <= 0 hiếm" sai theo số tiền |
| Đề xuất sửa và phòng ngừa | 10 | Mỗi vấn đề có cách sửa; có ít nhất một biện pháp phòng ngừa (test reconcile, hàm dùng chung, CI) |
| Văn phong review | 10 | Ngắn, lịch sự, cụ thể theo cell; tách chặn/không chặn; kết luận có điều kiện approve |

## Sai lầm hay gặp

- Đọc `git diff` thô của JSON, lạc trong output và `execution_count`, bỏ sót đổi một chữ `nunique` → `count`.
- Chỉ đọc code, không chạy: "trông hợp lý" là đủ để approve một bảng YoY sai 53 điểm %.
- Chấp nhận comment của tác giả mà không kiểm ("C luôn có Quantity âm").
- Chặn vì style chart, approve phần dữ liệu.
