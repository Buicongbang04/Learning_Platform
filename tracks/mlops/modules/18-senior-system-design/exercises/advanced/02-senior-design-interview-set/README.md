---
title: Bộ đề system design mức senior - recommendation, search ranking, LLM platform
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Luyện ba vòng phỏng vấn ML system design mức senior, mỗi vòng 45 phút, theo cùng một khung trả lời. Mục tiêu không phải thuộc một
kiến trúc mẫu mà là dẫn dắt cuộc trò chuyện: hỏi lại yêu cầu, chọn chỉ số, đặt baseline, vẽ hai đường online và offline, nói rõ đánh
đổi và cách vận hành. Hai đề realtime còn lại (fraud, ETA) nằm ở bài Advanced 01.

## Đề bài

Làm từng đề như một buổi phỏng vấn thật: bấm giờ 45 phút, nói to hoặc viết ra giấy, vẽ sơ đồ tay, rồi mới mở rubric. Mỗi đề nộp một
tệp `answer-<đề>.md` (tối đa 2 trang) gồm: câu hỏi làm rõ bạn đã hỏi và giả định bạn chọn, chỉ số offline và online, baseline, sơ đồ
kiến trúc, ước tính dung lượng, ba đánh đổi lớn nhất, SLO và cách vận hành, rủi ro.

**Đề A: gợi ý sản phẩm trang chủ cho sàn thương mại điện tử.** 50 triệu người dùng hoạt động tháng, 20 triệu sản phẩm, 5 000 yêu cầu
trang chủ mỗi giây lúc đỉnh, p99 dưới 200 ms cho toàn trang. Doanh thu từ gợi ý khoảng 30% GMV. Người bán mới phàn nàn sản phẩm của họ
không bao giờ xuất hiện. Đội pháp chế lo ngại gợi ý lặp lại các mặt hàng nhạy cảm.

**Đề B: xếp hạng kết quả tìm kiếm.** Cùng sàn ở đề A: 1 500 truy vấn mỗi giây, p99 dưới 300 ms, 60% truy vấn là truy vấn đuôi dài
(xuất hiện dưới 10 lần một tháng). Hiện dùng BM25 cộng vài luật tăng hạng thủ công. Dữ liệu huấn luyện là log click có thiên lệch
vị trí. Đội kinh doanh muốn đẩy sản phẩm quảng cáo mà không làm hỏng mức liên quan.

**Đề C: nền tảng LLM nội bộ cho 30 đội.** Mỗi đội muốn chatbot, tóm tắt, RAG trên tài liệu nội bộ. Ngân sách GPU cố định (16 GPU loại
24 GB tại chỗ cộng một hạn mức API bên ngoài mỗi tháng). Một số tài liệu chứa dữ liệu cá nhân không được rời khỏi hạ tầng công ty.
Đội bảo mật lo prompt injection và rò rỉ dữ liệu giữa các đội. Lãnh đạo muốn biết mỗi đội tốn bao nhiêu.

Không có test tự động. Tự chấm từng đề bằng rubric trong `SOLUTION.md`, tốt nhất nhờ một người đóng vai người phỏng vấn và hỏi các câu
"đào sâu" trong rubric.

## Tiêu chí đạt

- Mỗi đề đạt ít nhất 70/100 điểm rubric.
- Trong 5 phút đầu của mỗi đề bạn đã hỏi ít nhất 3 câu làm rõ và chốt một chỉ số thành công có số.
- Mỗi đề có ít nhất một chế độ hỏng được nói rõ cách phát hiện và cách giảm thiểu, và một đánh đổi được lượng hoá bằng tiền hoặc độ trễ.
- Bạn nói được giới hạn của câu trả lời: chỗ nào là giả định, chỗ nào cần dữ liệu thật hay kinh nghiệm vận hành mà bạn chưa có.

## Gợi ý

### Gợi ý 1

Dùng khung ở mục 6 README module theo đúng thứ tự, và nói ra thứ tự đó với người phỏng vấn để họ theo được. Phần lớn ứng viên mất điểm vì
nhảy thẳng vào kiến trúc model trước khi chốt chỉ số và baseline.

### Gợi ý 2

Đề A và B dùng chung kiến trúc nhiều tầng (sinh ứng viên rồi xếp hạng); khác nhau ở tín hiệu (lịch sử người dùng hay truy vấn) và thiên
lệch trong nhãn. Đề C không phải bài toán model mà là bài toán nền tảng: cổng vào chung, cô lập dữ liệu, hạn mức, đo chi phí theo đội, đánh
giá và guardrail.
