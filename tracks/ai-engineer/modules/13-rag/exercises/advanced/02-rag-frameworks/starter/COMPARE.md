# SDK trực tiếp hay LangChain cho RAG pháp luật

TODO: viết theo khung trong README của bài (ít nhất 400 từ). Người đọc là đồng nghiệp sắp chọn cách viết cho dự án
RAG tiếp theo: họ cần số liệu đo trên cùng pipeline, không cần cảm nhận chung về framework.

## Tóm tắt

TODO: 2–3 câu: bạn khuyên cách nào cho pipeline này, dựa trên số nào, và khi nào khuyến nghị đổi.

## Thiết lập

TODO: pipeline (retrieve hai tầng, prompt, cổng), 50 câu nào, model, phần cứng, phiên bản `langchain-core`,
`langchain-ollama`, Ollama; cách bạn bảo đảm so công bằng (cùng nguồn, cùng prompt, xen kẽ thứ tự gọi).

## Kết quả

TODO: bảng so hai bản: số dòng code (phần riêng và phần dùng chung), độ trễ trung vị phần sinh, chi phí riêng của
framework đo bằng LLM giả, số câu trả lời giống hệt nhau, có trích dẫn / trích đúng điều / từ chối, số gói phụ thuộc
thêm vào. Đọc bảng: chênh lệch nào có ý nghĩa, chênh lệch nào là nhiễu.

## Trải nghiệm viết và debug

TODO: chỗ nào LangChain giúp (ghép bước, callback, debug, tích hợp sẵn), chỗ nào cản (kiểu dữ liệu `Document`,
`RunnableBranch`, lỗi khó đọc, tài liệu đổi theo phiên bản). Kể một lỗi thật bạn gặp khi viết `build_chain` và cách
bạn lần ra nó.

## Khuyến nghị

TODO: chọn gì cho pipeline này và vì sao; những điều kiện làm bạn đổi lựa chọn (nhiều tool, agent, streaming, đội lớn,
yêu cầu kiểm soát prompt chặt); và điều gì bảng của bạn không đo được.
