# Lời giải: sandbox AWS có budget alarm, bản kiểm local

Lời giải: `aws/` (cấu hình) và `COST.md`. Bản này đã qua test plan trên LocalStack; phần chạy thật trên AWS là tuỳ chọn.

## Quyết định

- **Tài khoản sandbox riêng.** Lỗi trong sandbox không bao giờ chạm production; có thể đặt SCP của Organization chặn loại instance
  lớn và region lạ, là lớp bảo vệ mạnh hơn mọi validation trong code.
- **Validation là hàng rào đầu, không phải duy nhất.** `instance_type` trong danh sách nhỏ, budget ≤ 10 USD, `ami_id` đúng dạng.
  Người có quyền vẫn có thể sửa code; SCP và budget là lớp sau.
- **Không có thứ tính tiền theo giờ khi không dùng.** Không NAT gateway (khoảng 32 USD/tháng chỉ để tồn tại), không IP public (IPv4
  public tính tiền từ 2024), không load balancer. Instance trong subnet private; muốn vào máy thì dùng SSM Session Manager (cần
  VPC endpoint, cũng tính giờ) hay chỉ kiểm bằng console output. Bài này dừng ở "tạo được, destroy được".
- **IMDSv2 và ổ mã hoá** là mặc định đúng, không tốn thêm tiền.
- **Tag `ExpiresOn` và `Owner`** qua `default_tags`: người khác biết của ai, khi nào xoá được; script dọn hằng ngày lọc theo tag.
- **Budget = cảnh báo, không phải phanh.** Dữ liệu chi phí trễ tới 24 giờ; budget action (tự áp IAM policy hay dừng instance) có
  nhưng cần cấu hình riêng. Cảnh báo `FORECASTED` báo sớm hơn `ACTUAL`.
- **Chi phí ước tính trước khi apply.** Bảng tay như `COST.md`, hay Infracost đọc plan JSON và in chênh lệch chi phí ngay trong PR.

## Bản local và giới hạn của nó

`tofu plan` trên LocalStack kiểm được cấu trúc: tài nguyên nào, thuộc tính gì, tag, validation. Nó không kiểm được: AMI có tồn tại
không, quota, quyền IAM thật, giá. Đó là lý do có bước chạy thật trong tài khoản sandbox, và lý do test end-to-end của IaC luôn cần
một môi trường thật nhỏ.

## Rubric tự chấm phần chạy thật (không bắt buộc)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Chuẩn bị | 20 | Tài khoản sandbox riêng, MFA, quyền hẹp, kiểm `sts get-caller-identity` trước apply |
| Ước tính và budget | 20 | COST.md có số, budget tạo trước tài nguyên, email xác nhận đã nhận |
| Apply có kiểm soát | 20 | `plan -out` rồi apply đúng plan; xem lại plan trước khi gõ yes |
| Dọn | 25 | `tofu destroy` cùng ngày, lệnh kiểm in rỗng, Cost Explorer hôm sau không còn phát sinh theo tag |
| Ghi chép | 15 | Ghi chi phí thật so với ước tính và một điều học được |
