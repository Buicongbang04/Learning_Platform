# Lời giải: cổng promotion thành job, secret không lộ

Xem `gate.py` và `ct.yml` cạnh tệp này.

- **Cổng là mã thoát.** CI không đọc lý do, nó đọc exit code. `sys.exit(1)` làm bước, job, rồi workflow đỏ; `needs` làm job sau
  không chạy. Cổng chỉ in cảnh báo mà thoát 0 là loại lỗi nguy hiểm nhất: pipeline xanh, model xấu lên production.
- **Tách `decide` thuần khỏi `main`.** Hàm thuần test được bằng 11 ca không cần runner; `main` chỉ làm phần đọc tệp và đặt mã thoát.
  Cùng ý với `decide_promotion` ở module 04.
- **Giá trị không hữu hạn không bao giờ đạt.** Mọi phép so sánh với NaN đều `False`; viết điều kiện "đạt" dương (`mae <=
  ngưỡng`) thì NaN tự rơi vào nhánh từ chối, viết điều kiện "từ chối" (`mae > ngưỡng`) thì NaN lọt qua. Kiểm `isfinite`
  tường minh vẫn rõ hơn.
- **Không champion thì chỉ kiểm challenger hợp lệ.** Model đầu tiên cần một đường đi, nhưng nó vẫn phải có số đo hợp lệ.
- **Bước `deploy` tự kiểm secret.** Secret rỗng (chưa cấu hình, fork) không được tạo ra một lần deploy "thành công" giả. Dùng
  `env:` ở cấp bước thay cho `${{ secrets.X }}` nhúng thẳng vào dòng lệnh: giá trị không xuất hiện trong lệnh được in ra và
  shell tự quản lý nó.
- **Cơ chế che là lưới đỡ, không phải hàng rào.** Runner chỉ che chuỗi khớp nguyên văn. `${REGISTRY_TOKEN:0:10}` hay
  `base64` cho ra chuỗi khác và lọt log. Quy tắc: không in secret, kể cả khi gỡ lỗi; kiểm bằng grep log, như test.
- **`permissions: contents: read`** ở cấp workflow: job này không cần ghi vào repo.
