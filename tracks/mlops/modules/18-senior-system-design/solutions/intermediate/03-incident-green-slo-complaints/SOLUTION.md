# Lời giải: SLO xanh nhưng người dùng phàn nàn

**Nguyên nhân gốc.** SLI được đo ở span `predict`, tức lời gọi model bên trong ứng dụng, không phải ở điểm người dùng thấy. Chiều
hôm đó online feature store chậm (span `features` mất 600-2 500 ms). Hệ quả:

- Gateway cắt yêu cầu sau 1 giây và trả **504** cho client, nhưng ứng dụng vẫn chạy tiếp, `predict` vẫn xong với 200 trong khoảng 25 ms.
  SLI đếm yêu cầu đó là thành công và nhanh.
- Khi hàng đợi đầy, gateway **từ chối ngay (503)** và yêu cầu không bao giờ tới ứng dụng: trace chỉ có span `gateway`. SLI bỏ qua hẳn
  các yêu cầu này, vì mẫu số chỉ gồm trace có span `predict` (19 804 thay vì 20 000).
- Độ trễ của `predict` không gồm thời gian lấy feature, nên latency SLI 100% đúng trong khi người dùng chờ cả giây.

Log ứng dụng sạch vì, nhìn từ ứng dụng, không có gì hỏng: nó trả lời thành công cho một client đã bỏ đi.

**Sửa.** Đo ở span gốc của trace (`parent is None`, ở đây là `gateway`): đó là thứ gần client nhất mà ta kiểm soát. Mẫu số là mọi yêu
cầu client gửi tới, kể cả những yêu cầu bị chặn trước khi vào ứng dụng. Tìm span gốc theo `parent` thay vì ghi cứng tên mới, để sau này
thêm một tầng proxy cũng không làm SLI lệch lần nữa. `slis.py` cạnh tệp này là bản sửa.

**Phòng lần sau.**

- Quy tắc trong design review: SLI đo ở điểm gần người dùng nhất (load balancer, gateway, hoặc client-side RUM), không ở hàm model.
  Metric nội bộ (`predict`, `features`) dùng để chẩn đoán, không dùng làm SLO.
- Đối soát định kỳ: so số yêu cầu và tỉ lệ thành công của SLI với số liệu client (mobile telemetry) hay probe tổng hợp bên ngoài; lệch quá
  1% là một alert riêng ("SLI lệch khỏi thực tế").
- Thêm SLI độ trễ cho bước lấy feature và timeout phía ứng dụng nhỏ hơn timeout của gateway, để ứng dụng biết mình đã thất bại thay vì
  làm việc cho client đã bỏ đi.

**Bài học.** "Xanh" chỉ nghĩa là "con số ta chọn đo nằm trên ngưỡng". Khi khách phàn nàn mà SLO xanh, nghi chính SLI trước khi nghi khách.
