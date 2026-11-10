# Lời giải: bộ lọc path cho CI và CT

Xem `ci.yml` và `ct.yml` cạnh tệp này.

- **Liệt kê đầu vào thật của model, không đoán.** Một model là hàm của code, tham số và dữ liệu; `params.yaml`, `data.dvc` (con
  trỏ tới dữ liệu) và `train.py` là đầu vào của lớp CT. Thiếu một mục thì thay đổi đó đi qua mà không ai train lại, và không có lỗi
  nào cho bạn biết.
- **Hai workflow giao nhau có chủ đích.** `train.py` và `gate.py` vừa là code (cần lint, test) vừa là đầu vào của huấn luyện, nên
  cả hai chạy. Đây là chỗ hai lớp nối nhau, và test có ca riêng cho nó.
- **`src/**` chứ không phải `src/*`.** `*` dừng ở dấu `/`; `**` đi sâu vào thư mục con.
- **Path filter cho `pull_request` cũng cần**, nếu không PR sửa tham số không được kiểm trước khi merge. Cái giá: một check "bắt
  buộc" mà workflow không chạy sẽ chặn merge mãi ở trạng thái chờ. Nếu bạn bật branch protection, dùng một job tổng hợp luôn
  chạy, hoặc không đặt bắt buộc cho check có path filter.
- **`act` không đánh giá `paths`.** Bảng trong test là mô phỏng; nó đúng với luật GitHub đã mô tả nhưng không thay một lần
  thử trên GitHub thật (tuỳ chọn, xem README module).
- `-j train` chạy riêng một job để vòng lặp phát triển ngắn; `--dryrun` kiểm cấu trúc mà không chạy lệnh.
