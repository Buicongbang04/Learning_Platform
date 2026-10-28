# Lời giải: Báo cáo trạng thái đơn hàng bằng Bash

## Cách làm

1. **Kiểm tra tham số trước tiên.** `[[ $# -lt 1 ]]` rồi in `Usage:` ra stderr (`>&2`) và `exit 2`.
   Quy ước Unix: 2 là "dùng sai lệnh", 1 là lỗi chung, 0 là thành công. Scheduler (cron, Airflow
   `BashOperator`) chỉ nhìn exit code để biết task fail.
2. **Kiểm tra tệp** bằng `[[ ! -f "$file" ]]`. Luôn quote `"$file"`: test có tên file chứa dấu
   cách, thiếu quote là Bash tách thành hai tham số.
3. **Tìm cột theo tên**: `head -n 1 | tr ',' '\n' | grep -nx 'order_status' | cut -d: -f1`.
   `grep -n` in số dòng, `-x` khớp nguyên dòng (tránh khớp `order_status_old`). Khi không thấy,
   `grep` trả 1 và `set -e` + `pipefail` sẽ dừng script ngay, nên thêm `|| true` rồi tự kiểm tra
   biến rỗng để in thông điệp rõ ràng.
4. **Đếm**: `awk -F, -v c="$col" 'NF > 0 {print $c}'` lấy cột theo biến và bỏ dòng trống;
   `sort | uniq -c` đếm (uniq chỉ gộp dòng liền kề, nên phải sort trước); `sort -k1,1nr -k2,2` sắp
   theo số giảm dần rồi theo tên; `awk` cuối đổi định dạng thành `status,count`.
5. **Tách luồng**: CSV ra stdout, `total=` và lỗi ra stderr. Nhờ vậy `report.sh f.csv > out.csv`
   cho file sạch.

## Những chi tiết đáng chú ý

- `export LC_ALL=C`: thứ tự `sort` phụ thuộc locale; cố định để kết quả giống nhau trên mọi máy.
- `tr -d '\r'` giúp chịu được file tạo trên Windows (CRLF), lỗi rất hay gặp khi nhận file từ đối
  tác.
- Script chỉ đúng với CSV "đơn giản". CSV có `"Sao Paulo, SP"` trong ngoặc kép sẽ bị `awk -F,` cắt
  sai. Khi đó dùng công cụ hiểu CSV:

  ```bash
  duckdb -csv -c "SELECT order_status, count(*) AS count FROM read_csv_auto('$file')
                  GROUP BY 1 ORDER BY 2 DESC, 1"
  ```

## Mở rộng

- Thêm tham số `-s <status>` bằng `getopts` để chỉ in một trạng thái.
- Chạy định kỳ bằng cron và nối log: `0 6 * * * /opt/report.sh /data/orders.csv > /data/report.csv 2>> /var/log/report.log`.
- Kiểm tra script bằng `shellcheck report.sh`.
