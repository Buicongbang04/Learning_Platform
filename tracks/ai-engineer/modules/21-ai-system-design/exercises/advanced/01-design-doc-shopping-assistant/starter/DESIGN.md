# Design doc: Trợ lý mua sắm và chăm sóc khách hàng cho sàn ChợViệt

Tác giả: TODO · Ngày: TODO · Trạng thái: bản nháp

## 1. Bối cảnh và phạm vi

TODO: vấn đề kinh doanh, người dùng, việc trợ lý làm và KHÔNG làm (non-goals).

## 2. Yêu cầu và chỉ số thành công

TODO: yêu cầu chức năng, phi chức năng (SLO độ trễ, sẵn sàng, ngân sách, dữ liệu cá nhân), chỉ số kinh doanh,
sản phẩm và hệ thống; ngưỡng ship.

## 3. Ước lượng

TODO: giải thích từng giả định trong assumptions.yaml, dán bảng render_table(estimate(...)) ở đây, rồi đọc bảng:
API hay self-host, nút thắt nằm ở đâu, ngày flash sale thì sao.

## 4. Chọn kiến trúc

TODO: prompt / RAG / fine-tune / agent / workflow cho từng loại yêu cầu, kèm lý do và phương án bị loại.

## 5. Kiến trúc tổng thể

TODO: sơ đồ mermaid các thành phần và luồng một request.

## 6. Thiết kế chi tiết

TODO: retrieval sản phẩm và chính sách, tool tra đơn hàng, router/cascade, cache, fallback, prompt, xử lý hội thoại.

## 7. Đánh giá và vận hành

TODO: bộ eval offline, eval online, observability, cảnh báo, quy trình đổi model/prompt.

## 8. An toàn và quyền riêng tư

TODO: dữ liệu cá nhân, prompt injection (đánh giá sản phẩm là nội dung do người dùng viết), phân quyền tool, guardrails.

## 9. Rủi ro và đánh đổi

TODO: các rủi ro lớn nhất, đánh đổi đã chọn, điều gì khiến bạn đổi quyết định.

## 10. Lộ trình triển khai

TODO: MVP, các giai đoạn, tiêu chí đi tiếp ở mỗi giai đoạn.
