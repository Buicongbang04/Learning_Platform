# Lời giải: acceptance test chạy cùng khách

## Hướng làm

1. **Mỗi mục là một hàm độc lập** trả `{"id", "status", "detail"}` và tự bắt lỗi mạng của mình: một mục hỏng (embed tắt
   làm `/api/ask` lỗi) không được làm script dừng hay làm mục khác báo sai. Script luôn ghi `report.json` đủ 4 mục.
2. **`health` đọc `checks`**, không chỉ mã HTTP: `/healthz` trả 503 kèm `{"db": true, "llm": true, "embed": false}`;
   `detail` nêu đúng thành phần `false`. Đó là dòng đầu tiên IT khách đọc khi gọi bạn.
3. **`latency` đo đủ số mẫu cấu hình**, đếm lỗi riêng (một câu lỗi là FAIL, không phải "bỏ qua mẫu đó"), p95 theo phân vị
   nearest-rank đúng như README (với 4 mẫu, p95 là mẫu lớn nhất). Báo `p95_seconds` ra report để buổi nghiệm thu ghi lại
   con số, không chỉ PASS/FAIL.
4. **`citations` map `doc_id` → đường dẫn** bằng `GET /api/documents` (token quản trị) rồi kiểm có trích dẫn trong thư mục
   mong đợi. Không so chữ của câu trả lời: model nhỏ diễn đạt khác nhau, còn trích dẫn là thứ kiểm được.
5. **`acl` kiểm cả hai chiều**: người dùng thấy ít nhất một tài liệu, **mọi** tài liệu họ thấy nằm trong thư mục được cấp
   (bắt quyền cấp thừa), và câu hỏi thử về tài liệu ngoài quyền chỉ trích tài liệu họ thấy được (bắt rò rỉ qua `/api/ask`).
   Chỉ kiểm chiều thứ ba thì ACL cấp thừa vẫn PASS: tài liệu cấp thừa nằm trong danh sách "được thấy" nên trích dẫn của nó
   không bị coi là rò rỉ.

Mã: `acceptance.py` cạnh tệp này. Cả test ~75 s trên máy của repo.

## Ba trạng thái test dựng

| Trạng thái | health | latency | citations | acl |
| --- | --- | --- | --- | --- |
| Khoẻ, ngưỡng max(2 × mốc, 1 s) | PASS | PASS | PASS | PASS |
| `QUILLO_ACL=legal:legal/,legal:finance/,finance:finance/` (nhóm legal được cấp thừa `finance/`), ngưỡng 0,001 s | PASS | FAIL | PASS | FAIL |
| `docker compose stop embed` | FAIL (`embed`) | FAIL | FAIL | FAIL |

Trạng thái thứ hai mô phỏng lỗi cấu hình hay gặp khi IT khách sửa ACL bằng tay; ngưỡng 0,001 s chứng minh mục `latency`
thật sự so với ngưỡng thay vì luôn PASS.

## Những điều nên nói với khách ở buổi nghiệm thu

- Lần hỏi đầu chậm hơn các lần sau với **cùng** câu hỏi (llama.cpp giữ cache prompt): đo p95 bằng một câu lặp lại cho ra
  con số đẹp hơn thực tế. Bộ acceptance thật nên có nhiều câu hỏi khác nhau, và ngưỡng nên thống nhất trên cùng cách đo.
- Ngưỡng "2 × mốc đo lúc nghiệm thu" là cam kết tương đối: đổi phần cứng hay model thì đo lại mốc và ghi vào biên bản.
- Token SSO trong cấu hình là của tài khoản kiểm thử do khách cấp, hết hạn sau vài phút; script không lưu token, và
  `report.json` không chứa token hay nội dung tài liệu (chỉ đường dẫn thư mục và số đếm).

## Phương án khác

- Viết bằng pytest (mỗi mục một test) rồi xuất JUnit XML: tiện cho CI của nhà cung cấp, nhưng IT khách cần một lệnh và một
  báo cáo đọc được; nếu chọn cách này vẫn phải giữ đúng định dạng `report.json` và mã thoát của đề.
- Đo độ trễ bằng `/metrics` (`quillo_ask_seconds`) thay cho đồng hồ của script: đo đúng phía server nhưng chỉ có bucket,
  và vẫn phải gửi câu hỏi để có số liệu; bài này yêu cầu đo thời gian phía client.
