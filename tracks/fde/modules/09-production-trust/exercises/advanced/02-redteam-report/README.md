---
title: "Báo cáo red-team prompt injection gửi công ty luật"
level: advanced
services: []
files:
  - path: starter/redteam-report.md
    note: Khung báo cáo; bạn viết vào đây
run: []
---

## Mục tiêu

Trưởng phòng CNTT của công ty luật đọc báo chí về "AI bị lừa bằng tài liệu" và hỏi thẳng: "hệ thống của các anh có bị
không, nặng tới đâu, chúng tôi phải làm gì?". Câu trả lời là một báo cáo red-team: kết quả thật trên hệ thống của họ, xếp
mức độ theo rủi ro **của họ**, tách việc của nhà cung cấp với việc của khách, và nói thẳng phần rủi ro còn lại sau khi đã
giảm thiểu. Báo cáo này sẽ được đọc bởi người không viết code và được chuyển cho bộ phận tuân thủ.

## Đề bài

Dùng kết quả của bài basic 02 (`tests/fixtures/attacks.json`, `answers.json` và kết quả `grade` của bạn; tốt hơn nữa là
một lần chạy bộ tấn công của bạn trên quillo thật trong lab) và bối cảnh sau:

- Công ty luật, 300 người dùng, quillo 1.1.0 trên k3s, `llm-small`, SSO + ACL theo thư mục (`legal/`, `finance/`).
- Tài liệu vào quillo qua connector đồng bộ từ file share; hợp đồng do **đối tác bên ngoài** gửi qua email được thư ký lưu
  vào share đó. Câu trả lời của quillo được dán vào email gửi khách hàng của công ty luật và vào wiki nội bộ (hiển thị
  markdown).
- Máy chủ không ra internet; máy trạm của nhân viên thì có.

Viết `starter/redteam-report.md` (tiếng Việt, ~1000–1500 từ chưa tính bảng và phụ lục) gồm: tóm tắt cho lãnh đạo (≤ 150
từ); phạm vi và phương pháp (hệ thống, model, bộ tấn công, số lần chạy, giới hạn của phương pháp); các phát hiện, mỗi
phát hiện có kỹ thuật, bằng chứng (đã che, không chứa nội dung tài liệu thật), mức độ có lý do theo bối cảnh trên, đường
tấn công thực tế ở công ty luật; khuyến nghị tách **nhà cung cấp** / **khách**, có ưu tiên; rủi ro còn lại; kế hoạch
kiểm lại.

Không có test tự động; tự chấm theo rubric. Bài mẫu ở `solutions/`.

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và không có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Tóm tắt lãnh đạo nói được: có bị không, nặng tới đâu, cần làm gì, trong ≤ 150 từ không thuật ngữ | 2 |
| Phương pháp tái lập được (bộ tấn công, seed hoặc tệp, model, `top_k`, số lần chạy) và nêu giới hạn (mẫu nhỏ, model nhỏ, chấm bằng canary) | 3 |
| Mỗi phát hiện có bằng chứng cụ thể đã che và tỉ lệ dưới dạng số tuyệt đối (k/n) | 3 |
| Mức độ suy ra từ bối cảnh khách (ai đưa tài liệu vào, câu trả lời đi đâu, máy nào ra internet), không chỉ từ kỹ thuật | 4 |
| Khuyến nghị tách hai bên, khả thi, có ưu tiên; phía sản phẩm nêu được thay đổi cụ thể | 4 |
| Rủi ro còn lại nói thẳng, không hứa "đã khắc phục hoàn toàn" | 2 |
| Kế hoạch kiểm lại gắn với thay đổi (model, prompt, bản phát hành) | 2 |

Lỗi loại trừ: kết luận "an toàn" từ một lần chạy 0 tấn công thành công; khuyến nghị duy nhất là "đổi model lớn hơn";
báo cáo chứa nội dung tài liệu của khách hay câu hỏi thật của người dùng.

## Gợi ý

### Gợi ý 1

Đọc từng câu trả lời bị xếp `compromised` và hỏi: model đã *làm theo* tài liệu, hay chỉ *lặp lại* nó? Với người nhận
câu trả lời, khác biệt đó có quan trọng không?

### Gợi ý 2

Vẽ đường đi của một tài liệu từ email của đối tác tới màn hình của khách hàng công ty luật. Mỗi chỗ một người hay một hệ
thống có thể chặn là một khuyến nghị.
