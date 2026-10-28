# Lời giải: Bảng aggregate theo ngày và kiểm tra số khớp nguồn

Xem `aggregate.py` cùng thư mục.

## Build idempotent

- Câu `INSERT … SELECT` aggregate ở grain `(order_date, customer_state)` với cùng bộ lọc trạng thái như các metric
  khác. Hằng `VALID_STATUS_FILTER` dùng chung cho build và reconcile, nên hai phía không thể lệch định nghĩa.
- Trước khi insert, xoá đúng khoảng ngày sẽ tính lại. Cặp `DELETE` + `INSERT` nằm trong một transaction: nếu insert
  lỗi thì rollback, bảng giữ dữ liệu cũ. Chạy lại bao nhiêu lần cũng ra cùng kết quả, đó là **idempotency**.
- Chỉ đụng tới `[start, end]` giúp xử lý **late-arriving data** rẻ: lịch chạy hằng ngày có thể build lại 3 ngày gần
  nhất để bắt đơn đến muộn.
- Trên warehouse thật, cùng ý tưởng là `MERGE`, `INSERT OVERWRITE PARTITION` (Spark/Hive), hoặc dbt incremental với
  `incremental_strategy='delete+insert'`.

## Reconcile

- Hai CTE aggregate về grain ngày. `FULL OUTER JOIN` + `COALESCE(…, 0)` bắt cả ngày có trong nguồn mà aggregate
  chưa có (đơn đến muộn) và ngày có trong aggregate mà nguồn đã mất (dữ liệu bị xoá hoặc sửa).
- So revenue bằng dung sai vì `DOUBLE` có sai số làm tròn. Số đơn là số nguyên nên so bằng `!=`.
- Trả danh sách ngày lệch, không chỉ một cờ `ok`, để người trực biết build lại ngày nào.

## Trong production

- Chạy reconcile ngay sau build, như một bước của DAG. Lệch thì fail task và alert, không để dashboard hiện số sai.
- Lưu kết quả reconcile vào bảng audit (`run_id`, khoảng ngày, chênh lệch) để theo dõi xu hướng.
- Có thể diễn đạt cùng kiểm tra bằng dbt test (`dbt_utils.equality`, test tuỳ biến) hoặc Great Expectations.
