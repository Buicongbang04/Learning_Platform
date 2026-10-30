---
title: Top 3 sản phẩm mỗi quốc gia và phân nhóm ABC (Pareto) bằng window function
level: basic
services: []
files:
  - path: starter/top3_per_country.sql
    note: 1 TODO - top-N theo nhóm
  - path: starter/pareto.sql
    note: 1 TODO - running total, nhóm A/B/C
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_ranking.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/basic/02-top-products-pareto/starter/run_query.py top3_per_country.sql
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/basic/02-top-products-pareto -q
---

## Mục tiêu

Trả lời hai câu hỏi của team mua hàng bằng SQL: "mỗi thị trường bán chạy nhất mặt hàng nào?" (top-N theo
nhóm) và "bao nhiêu mặt hàng làm ra 80% doanh thu, nên tập trung tồn kho vào đâu?" (Pareto, running total,
phân nhóm ABC), đồng thời nhận ra các "mặt hàng" không phải hàng hoá trước khi chúng lọt vào báo cáo.

## Đề bài

Bảng `online_retail` như bài Basic 01 (bộ `online-retail-ii`, hai sheet, dữ liệu gốc). Cả hai truy vấn dùng:

- **Kỳ**: 12 tháng đủ gần nhất, `invoice_date` từ `2010-12-01` (tính) tới trước `2011-12-01`.
- **Dòng hợp lệ** như định nghĩa chung; doanh thu = `quantity * price`.
- **Chỉ hàng hoá**: `stock_code` bắt đầu bằng 5 chữ số (`22423`, `85123A`). Các mã như `POST` (phí gửi),
  `DOT` (phí dotcom), `M` (điều chỉnh tay), `C2` (phí vận chuyển), `BANK CHARGES`, `AMAZONFEE` là phí hoặc điều
  chỉnh, không phải sản phẩm.

1. **`top3_per_country.sql`**: với mỗi `country`, 3 mặt hàng doanh thu cao nhất. Hoà doanh thu thì `stock_code`
   nhỏ hơn đứng trước, mỗi nước **tối đa 3 dòng**. Cột: `country, rnk` (1, 2, 3), `stock_code`, `revenue` (làm
   tròn 2), `share_of_country` (doanh thu mặt hàng / tổng doanh thu **hàng hoá** của nước đó trong kỳ, làm tròn
   4). Sắp theo `country, rnk`.
2. **`pareto.sql`**: mọi mặt hàng có bán trong kỳ (gộp mọi nước), sắp doanh thu giảm dần (hoà: `stock_code`
   nhỏ trước). Cột: `stock_code`, `revenue`, `rnk` (1, 2, 3... không trùng), `cum_share` (doanh thu luỹ kế tới
   hết mặt hàng này / tổng, làm tròn 4), `abc_class`:
   - `A` nếu luỹ kế **trước** mặt hàng này < 80% (mặt hàng làm tổng vượt mốc 80% vẫn là A),
   - `B` nếu luỹ kế trước < 95%,
   - `C` còn lại.

Sau khi test pass, chạy thêm vài biến thể (bỏ điều kiện hàng hoá, đổi `row_number` thành `rank`) bằng
`run_query.py` rồi làm phần trắc nghiệm trong app.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: đúng kỳ (mốc đầu tính, mốc cuối không), bỏ phí, bỏ dòng huỷ và giá 0, hoà xử lý
  đúng, tỉ trọng tính trên cả nước chứ không trên top 3, ABC theo luỹ kế trước.
- Trên bộ thật: 38 nước, 114 dòng top 3, không còn mã phí; mặt hàng số 1 ở UK là `22423` (137 735.07 GBP, 1.7%
  doanh thu hàng hoá UK); 3 897 mặt hàng, trong đó 834 nhóm A.
- Trắc nghiệm: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Window function không đặt trong `WHERE` được (WHERE chạy trước khi window được tính). Tính `rnk` trong CTE rồi
lọc ở ngoài, hoặc dùng `QUALIFY rnk <= 3` của DuckDB. Tỉ trọng của nước: `revenue / sum(revenue) OVER
(PARTITION BY country)`, tính **trước** khi lọc top 3.

### Gợi ý 2

Luỹ kế: `sum(revenue) OVER (ORDER BY revenue DESC, stock_code ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT
ROW)`. Không ghi `ROWS`, frame mặc định là `RANGE` và hai mặt hàng cùng doanh thu sẽ nhận cùng luỹ kế. Luỹ kế
trước mặt hàng = luỹ kế tới mặt hàng - doanh thu của nó. Lọc mã hàng hoá: `regexp_matches(stock_code,
'^[0-9]{5}')`.
