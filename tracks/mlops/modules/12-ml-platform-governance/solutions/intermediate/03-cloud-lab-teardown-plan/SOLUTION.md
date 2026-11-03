# Lời giải: kế hoạch dọn lab cloud

Mã trong `teardown.py`. Vì sao thiết kế như vậy:

- **Dọn theo tag của lab, không theo tên, vùng hay loại.** Một script "xoá mọi endpoint tên bắt đầu bằng `ml-lab`" sẽ xoá cả endpoint của đồng nghiệp hay của lab khác trong cùng tài khoản. Tag `lab=<id>` do chính lab đặt lúc tạo (Terraform `local.tags`, bài đọc IaC) là bằng chứng sở hữu duy nhất đủ mạnh. Tài nguyên giống tên nhưng thiếu tag chỉ được **cảnh báo**, người dùng tự quyết. So tiền tố có ranh giới `lab + "-"`: `ml-lab-70-eta` không phải của lab `ml-lab-7`.
- **Kiểm mọi chuỗi trước khi sinh lệnh.** Tên, vùng và resource group đều đi vào một dòng shell; `x; rm -rf /` hay `$(...)` là lệnh khác, và vì script dry-run vẫn được bash phân tích, một `region` độc chạy ngay cả khi chỉ in. Kiểm riêng tên mà bỏ vùng là để ngỏ đúng cái cửa đó. Danh sách cho phép (`SAFE_NAME`) chặt hơn việc cố escape, và tài nguyên của lab khác không thể làm hỏng kế hoạch của bạn vì chỉ tài nguyên của lab mới bị kiểm.
- **Thứ tự theo phụ thuộc.** Endpoint trước endpoint-config trước model (xoá model khi endpoint còn dùng bị từ chối); notebook phải stop, **đợi** tới `Stopped` (`aws sagemaker wait notebook-instance-stopped`; lệnh stop trả về ngay khi còn `Stopping`) rồi mới delete; bucket và resource group cuối cùng vì thứ gì đó có thể còn ghi vào chúng trong lúc tắt serving.
- **Mặc định dry-run.** Người chạy script lúc mệt mỏi đọc output "DRY-RUN" trước, rồi mới `DRY_RUN=0`. Một cờ an toàn mặc định bật rẻ hơn mọi quy trình review.
- **Lỗi một bước không dừng cả script.** Dừng ở bước lỗi để lại endpoint đắt nhất phía sau vẫn chạy. Chạy hết, ghi `FAILED`, thoát khác 0 để người dùng biết còn việc.
- **Vì sao chấm bằng CLI giả.** Không có tài khoản cloud trong test; CLI giả kiểm được **lệnh nào được gọi, theo thứ tự nào, khi nào** (phần dễ sai nhất), không kiểm được cờ có hợp lệ với bản CLI hiện tại. Giới hạn này nằm trong đề; đối chiếu tài liệu nhà cung cấp trước khi chạy thật.

Chi phí ẩn cần ghi vào checklist lab: NAT gateway (tính theo giờ cộng theo GB), endpoint quên tắt, notebook đang chạy, bucket và log còn lại, snapshot/EBS của notebook, egress dữ liệu, và cùng một dịch vụ ở vùng khác. Budget alarm chỉ báo, dữ liệu chi phí trễ hàng giờ tới ngày, nên lab vẫn cần quy tắc "dọn trước khi ngủ".
