# Lời giải: trắc nghiệm phỏng vấn SRE và DevOps

| Câu | Đáp án | Giải thích và cách mở rộng khi trả lời phỏng vấn |
| --- | --- | --- |
| sli-choice | b | SLI đo thứ khách cảm nhận (thành công và đủ nhanh), ở chỗ thấy được lỗi kể cả khi pod chết (load balancer). CPU, số pod, ping database là nguyên nhân hay tín hiệu nội bộ, dùng cho dashboard chẩn đoán chứ không làm SLI. Mở rộng: nói thêm SLI theo request hay theo thời gian, và ngưỡng latency lấy từ đâu |
| burn-rate-math | b | Budget 0,1%; 1,44% chia 0,1% là burn rate 14,4. Một giờ tiêu 14,4 nhân 1 chia 720 giờ, khoảng 2% budget 30 ngày: đúng ngưỡng page nhanh của SRE Workbook. Mở rộng: vì sao cần thêm cửa sổ 5 phút |
| budget-exhausted | a | Chính sách tốt dừng rủi ro mới (feature) nhưng giữ đường sửa (rollback, vá bảo mật) và chuyển công sức sang độ tin cậy. Cấm cả rollback làm sự cố dài thêm; nâng SLO khi đang trượt là phạt vô ích; bỏ qua budget thì SLO vô nghĩa |
| incident-commander | c | IC điều phối và quyết định, không tự gõ lệnh, để có người nhìn toàn cảnh và liên lạc đều đặn. Tìm người có lỗi và viết postmortem để sau sự cố. Mở rộng: kể các vai ops lead, communications lead, scribe |
| blameless | b | Postmortem không đổ lỗi hỏi "hệ thống nào cho phép lỗi này xảy ra", sửa bằng guardrail (duyệt, quyền tối thiểu, xoá mềm). Không đổ lỗi không có nghĩa là giấu sự thật: vẫn ghi đầy đủ lệnh và diễn biến |
| chaos-first-step | c | Chaos engineering là thí nghiệm: giả thuyết trạng thái ổn định đo bằng SLI, blast radius nhỏ (một service, môi trường lab hay một phần traffic), nút dừng. Bắt đầu nhỏ rồi mở rộng, như game day của bài Advanced 01 |
| littles-law | b | L bằng lambda nhân W: 400 nhân 0,05 giây là 20 kết nối đang dùng cùng lúc. Mở rộng: cộng headroom cho đỉnh và latency tăng khi tải tăng, và nhân với số replica khi tính max_connections của database |
| rightsizing-memory | b | CPU là tài nguyên nén được (thiếu thì throttle), RAM không nén được (thiếu thì OOMKilled). Vì vậy RAM lấy mức cao nhất cộng headroom. Scheduler xếp pod theo cả request CPU lẫn RAM |
| ci-least-privilege | b | OIDC cho credential ngắn hạn gắn với repo và nhánh, không có key dài hạn để lộ. Key admin trong secret, IAM user admin hay runner có instance profile admin đều cho một job bị chiếm quyền toàn tài khoản |
| behavioural | c | STAR có số liệu và điều đã thay đổi cho thấy bạn sở hữu sự cố và học từ nó. Người phỏng vấn SRE tìm người nói thẳng về lỗi, không đổ lỗi, và cải tiến hệ thống |
| pipeline-security | a, b, c, e | Quét secret, SBOM, ký image, ghim action theo SHA là bốn bước cơ bản, rẻ, chặn được các vụ phổ biến (lộ key, phụ thuộc có lỗ hổng, image giả, action bị chiếm). Quyền ghi cho mọi job ngược với least privilege |
| toil | a, c, d | Toil là việc tay, lặp lại, tự động hoá được, không tạo giá trị lâu dài, tăng theo quy mô dịch vụ. Thiết kế lại kiến trúc và viết postmortem là công việc kỹ thuật tạo giá trị lâu dài |
