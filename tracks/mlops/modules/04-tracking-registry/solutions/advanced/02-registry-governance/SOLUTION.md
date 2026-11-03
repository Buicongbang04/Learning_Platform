# Lời giải: registry dùng chung cho nhiều đội

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo chất lượng lập luận.

## Các quyết định cốt lõi

- **Một server dùng chung, tên có tiền tố đội.** MLflow OSS không có namespace thật; tiền tố trong tên và prefix trong object
  storage là cách rẻ nhất để vừa nhìn thấy chủ sở hữu vừa cô lập ở tầng lưu trữ. Phương án khác: mỗi đội một server (cô lập
  mạnh, đội vận hành 2 người phải nuôi 4 hệ thống; không có cái nhìn chung cho kiểm toán).
- **Quyền promote tách khỏi quyền train.** DS không đặt được `champion`; chỉ tài khoản CI sau khi cổng promotion đạt mới đặt.
  Đây là cách trả lời kiểm toán "ai duyệt, dựa trên gì": tag quyết định trên version là bằng chứng, tài khoản dịch vụ làm
  người ký.
- **Trung thực về cơ chế.** MLflow OSS có basic auth và quyền theo experiment/model ở bản mới, nhưng phần lớn thiết kế thực
  tế đặt proxy + SSO phía trước và dựa vào quy ước. Một thiết kế ghi "bị chặn bởi MLflow" mà thực ra chỉ là quy ước thì
  mất điểm.
- **Backup cả hai nửa.** Backend (Postgres) và artifact (object storage) phải khôi phục về cùng thời điểm; chỉ backup một
  nửa cho ra registry trỏ vào artifact không còn. Nêu RTO/RPO bằng số và diễn tập.
- **Điều kiện thoát.** Không dùng "khi lớn hơn" mà nêu ngưỡng đo được (số đội, tỉ lệ thời gian vận hành, nhu cầu RBAC mịn).

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Đáp ứng kiểm toán | 20 | Có chuỗi chứng cứ: run (lineage) → version (tag quyết định) → người ký (tài khoản dịch vụ + audit log) |
| Cô lập đội giá cước | 15 | Cô lập ở object storage và proxy, không chỉ bằng quy ước; nêu giới hạn của MLflow OSS |
| Quy ước đặt tên và metadata | 15 | Đủ bảng, mỗi dòng có lý do; alias bị giới hạn |
| Quyền theo vai trò, cơ chế thực thi trung thực | 15 | Phân biệt chặn thật và quy ước; vai trò CI có token ngắn hạn |
| Vận hành: backup, retention, nâng cấp | 20 | RPO/RTO bằng số, backup nhất quán hai nửa, retention có ngoại lệ cho kiểm toán, diễn tập khôi phục |
| Rủi ro, điều kiện thoát | 15 | Điểm sự cố chung và cách giảm nhẹ, ngưỡng cụ thể để chuyển sang dịch vụ quản lý |

Lỗi hay gặp: viết "dùng RBAC" mà không nói cái gì thực thi nó; quên rằng service production phụ thuộc vào registry lúc
khởi động; retention xoá mất artifact mà kiểm toán cần.
