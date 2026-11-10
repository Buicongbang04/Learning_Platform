# Hướng dẫn chấm: runbook lab serverless trên AWS thật

`aws/` và `RUNBOOK.md` cạnh tệp này là một lời giải qua test. Rubric chấm runbook và cấu hình như một reviewer đọc trước khi cho phép chạy
trên tài khoản thật.

## Hướng làm

1. **Vẽ trần chi phí trước khi viết tài nguyên**: mỗi đường tiền có thể chạy mất kiểm soát (request, Lambda, retry, log) cần một van:
   quota và throttling của API, `maximum_concurrency`, DLQ sau 3 lần, retention 7 ngày, budget alarm.
2. **Cửa vào không cần Lambda**: API Gateway REST gửi thẳng vào SQS bằng integration `AWS`; ít một function, ít cold start, API trả 202 ngay.
   HTTP API (v2) rẻ hơn nhưng không có usage plan và API key, và LocalStack community không có.
3. **Runbook viết cho người khác chạy lúc 2 giờ sáng**: mỗi khối lệnh tự kiểm đúng tài khoản; plan lưu ra tệp và apply đúng tệp đó; bước
   kiểm có kết quả mong đợi; bước dọn có lệnh kiểm "không còn gì"; mục sự cố cho biết tắt van nào trước.
4. **Bản local**: cùng luồng chạy được trên máy ở bài Intermediate 01; test của bài này chỉ plan.

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Ước tính chi phí | 2 | Giả định rõ (region, lượng, thời gian), đơn giá có nguồn, nói đúng Free Tier hay credit, chỉ ra khoản rủi ro thật (thứ chạy không dừng) |
| Trần chi phí trong cấu hình | 2 | Budget có ACTUAL và FORECASTED; quota, throttling, `maximum_concurrency`, DLQ, retention đều có và khớp với runbook |
| An toàn khi triển khai | 2 | Credential ngắn hạn, kiểm tài khoản trước mỗi lệnh ghi, plan lưu tệp được review rồi apply đúng tệp; không `-auto-approve`; không in API key hay secret ra log |
| Kiểm tra được | 1 | Có lệnh và kết quả mong đợi cho đường thành công, đường bị từ chối (không key) và DLQ |
| Dọn và xác minh | 2 | `tofu destroy` cộng lệnh liệt kê theo tiền tố hay tag; nói tài nguyên ngoài state (log group tự tạo); kiểm Cost Explorer hôm sau |
| Xử lý sự cố | 1 | Thứ tự tắt van khi chi phí tăng (chặn nguồn gọi, tắt mapping, rồi điều tra); xử lý DLQ bằng redrive chứ không xoá |

## Lỗi hay gặp

- `tofu apply -auto-approve` trên tài khoản thật, hay apply không lưu plan nên thứ chạy khác thứ đã review.
- Budget coi như cầu dao: nó chỉ gửi email, chậm tới vài giờ.
- Quên `api_key_required` ở method: usage plan có mà ai cũng gọi được.
- Lambda tự tạo log group trước khi tofu tạo (do `depends_on` thiếu): log group không nằm trong state, destroy để lại và giữ log mãi.
- Integration `HTTP` tới URL tuỳ ý cho "tiện": biến API thành proxy mở; chỉ dùng integration tới dịch vụ AWS đã biết.
