# Lời giải: đọc Terraform cho ML

1. **idle-cost (a, c, e)**: endpoint, NAT gateway và notebook đang chạy tính tiền theo giờ dù không có request. `aws_sagemaker_model`, `aws_sagemaker_endpoint_configuration` và `aws_iam_role` chỉ là khai báo, không có đồng hồ chạy; endpoint_config chỉ "kích hoạt" tiền khi một endpoint dùng nó.
2. **biggest-idle (b)**: hai instance `ml.m5.xlarge` chạy 730 giờ mỗi tháng. Dù giá thay đổi theo vùng và thời điểm, hai máy cỡ đó chạy liên tục là khoản lớn nhất trong tệp; notebook `ml.t3.medium` nhỏ hơn nhiều, bucket tính theo GB, budget gần như miễn phí.
3. **preview-destroy (c)**: `terraform plan -destroy` in kế hoạch xoá mà không xoá. `destroy -auto-approve` xoá luôn; `apply -refresh-only` chỉ đồng bộ state; `state rm` làm Terraform **quên** resource (nó vẫn chạy và tính tiền).
4. **what-is-managed (d)**: `terraform state list`. Biết state giúp phân biệt thứ Terraform sẽ dọn với thứ nằm ngoài nó.
5. **bucket-not-empty (a)**: S3 từ chối xoá bucket còn object; `force_destroy = true` hoặc làm rỗng trước. Xoá tệp state làm bạn mất khả năng dọn: tài nguyên vẫn còn, chỉ Terraform không biết.
6. **manual-leftovers (c)**: destroy chỉ chạm resource trong state. Endpoint tạo tay ở console vẫn chạy; đây là lý do tag lab và kiểm console/CLI sau khi dọn.
7. **budget-effect (d)**: budget mặc định chỉ **thông báo**. Chặn chi tiêu cần thêm budget action hay cơ chế tự dọn, và có độ trễ hàng giờ tới vài ngày trong dữ liệu chi phí. Không bao giờ coi budget alarm là phanh.
8. **ttl-tag (b)**: tag cho phép quy chi phí, tìm thứ mồ côi và viết script dọn chỉ động tới resource có đúng tag của lab. AWS không tự xoá theo `ttl`; đó chỉ là quy ước mà script hay người dọn đọc.

Nối sang bài sau: bài lab dọn (trung cấp 03) biến các lệnh này thành kế hoạch dọn có thể kiểm tĩnh.
