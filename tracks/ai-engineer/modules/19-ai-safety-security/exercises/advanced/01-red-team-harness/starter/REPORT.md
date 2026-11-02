# Red-team trợ lý ngân hàng Sao Mai: kết quả và khuyến nghị

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm bảo mật: họ cần biết bạn tấn công
thế nào, phòng thủ nào giữ được, phòng thủ nào chỉ trông có vẻ giữ được, và bạn khuyên gì.

## Tóm tắt

TODO: 3–4 câu có số: ASR của cấu hình gốc và cấu hình khuyên dùng (kèm khoảng tin cậy), số câu bình thường bị chặn oan,
mục tiêu nào còn hở.

## Thiết lập

TODO: model (tên, digest, phiên bản Ollama), `temperature`, ba system prompt, 10 template, 3 mục tiêu và cách kiểm, 20
câu bình thường, guard input và output (ngưỡng classifier), phần cứng, thời gian chạy.

## Kết quả

TODO: bảng `asr_table` theo phòng thủ; bảng theo template và theo mục tiêu cho `plain` và `hardened`. Đọc bảng: chênh
lệch nào vượt khoảng tin cậy, chênh lệch nào không.

## Bypass và trace

TODO: ít nhất 3 lượt tấn công thành công dưới phòng thủ mạnh nhất hoặc vượt qua guard output, kèm câu trả lời thật và
giải thích vì sao lọt.

## Least privilege

TODO: `minimal` so với `plain` và `hardened`: mục tiêu nào biến mất theo thiết kế, mục tiêu nào không, cái giá là gì.

## Khuyến nghị và giới hạn

TODO: cấu hình đưa lên production và cổng hồi quy đặt ở đâu trong CI; việc nên làm tiếp; những gì bảng này không nói
được.
