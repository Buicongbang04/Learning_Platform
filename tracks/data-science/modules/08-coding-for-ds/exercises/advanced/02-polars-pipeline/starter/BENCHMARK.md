# pandas, polars hay DuckDB cho bảng điểm seller?

Người đọc: team data đang cân nhắc chuyển các notebook pandas chậm sang công cụ khác.

## 1. Cách đo

TODO: máy (CPU, RAM), phiên bản thư viện, dữ liệu (Olist thật nhân lên bao nhiêu lần), đo cái gì
(đọc CSV, biến đổi, cả hai), đo bao nhiêu lần, lấy min hay median và vì sao.

## 2. Kết quả

TODO: bảng thời gian và bộ nhớ đỉnh của ba cách (pandas đã vector hoá, polars lazy, DuckDB SQL) ở ít
nhất hai cỡ dữ liệu.

## 3. Đọc kết quả

TODO: chênh lệch đến từ đâu (đa luồng, projection/predicate pushdown, Arrow, không tạo bản sao)?
Có trường hợp nào pandas vẫn là lựa chọn đúng?

## 4. Khuyến nghị

TODO: chọn gì cho team, với điều kiện nào; chi phí chuyển đổi (học API mới, thư viện vẽ, sklearn
nhận gì) và cách chuyển dần.
