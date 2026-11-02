# M09: Tài liệu system design của chính hệ thống

## Mục tiêu

Viết design doc của trợ lý pháp luật như ở vòng system design phỏng vấn AI Engineer, nhưng có lợi thế không ứng viên nào
có: mọi con số là số **bạn đã đo** ở M01 tới M08. Tài liệu trả lời: hệ thống phục vụ ai, yêu cầu gì, kiến trúc nào và vì
sao, chi phí và năng lực ra sao khi lên quy mô, rủi ro nào còn mở, và lộ trình tiếp.

Dùng lại khung đóng bài toán, ước lượng capacity/chi phí và design doc 10 mục của
[module 21](../../modules/21-ai-system-design/README.md) (bài Advanced 01 cho khung, Advanced 02 cho cách review).

**Phần cứng:** CPU; khoảng 6 tới 8 giờ làm.

## Việc cần làm

1. **Bối cảnh giả định** (ghi rõ là giả định): ai dùng (người dân hỏi luật, cán bộ tư pháp xã, luật sư), bao nhiêu người
   dùng mỗi ngày, ngân sách, ràng buộc dữ liệu (văn bản công khai, câu hỏi có thể chứa PII).
2. **Ước lượng bằng code**: dùng hàm của bài Intermediate 01 / Advanced 01 module 21 với số đo thật của bạn (token mỗi
   câu từ trace M08, độ trễ, công suất đo dưới tải, VRAM của M04) để tính số request đỉnh, số GPU hoặc chi phí API,
   chi phí tháng. Bảng sinh từ code, dán nguyên văn.
3. **Design doc** `reports/DESIGN.md` theo 10 mục của module 21 (bối cảnh, yêu cầu, ước lượng, chọn kiến trúc, kiến
   trúc tổng thể, thiết kế chi tiết, đánh giá và vận hành, an toàn và quyền riêng tư, rủi ro và đánh đổi, lộ trình),
   ít nhất 2 sơ đồ mermaid. Mỗi quyết định trỏ về milestone đã đo nó (ví dụ "hybrid với BM25 bigram, không rerank: M02").
4. **Những điều chưa giải quyết**: ngày hiệu lực văn bản (corpus không có), cập nhật văn bản mới (index lại phần nào), nhãn
   qrels chỉ một điều mỗi câu, trách nhiệm pháp lý của câu trả lời. Với mỗi điều: rủi ro, cách giảm, cách đo.
5. **Tự review** theo rubric của bài Advanced 02 module 21 (hoặc nhờ một người khác review), sửa, ghi lại thay đổi.
6. Viết lại `project/README.md` thành README portfolio: tóm tắt hai câu, sơ đồ, bảng con số chính có link, Decisions,
   giới hạn.

## Kết quả nộp

- `reports/DESIGN.md`, bảng ước lượng sinh từ code, ghi chú review.
- `project/README.md` bản portfolio.

## Tiêu chí đạt

- [ ] Đủ 10 mục, ít nhất 1 500 từ, ít nhất 2 sơ đồ mermaid hợp lệ.
- [ ] Mọi con số hoặc lấy từ log của M01–M08 (có trỏ tới), hoặc sinh từ code ước lượng với giả định ghi rõ; không có số
      tính nhẩm chép tay.
- [ ] Mỗi lựa chọn kiến trúc lớn (retrieval, đơn vị trích dẫn, mức quantize, fine-tune hay không, agent khi nào,
      guardrail nào) có phương án bị loại và lý do bằng số.
- [ ] Có mục rủi ro nói rõ hệ thống **không** bảo đảm gì (hiệu lực văn bản, tư vấn pháp lý thay luật sư).
- [ ] README portfolio: người đọc trong 3 phút biết hệ thống làm gì, tốt tới đâu (con số chính), và chạy lại thế nào.

## Gợi ý

- Viết mục "Chọn kiến trúc" như một bảng so phương án (prompt thuần, RAG, fine-tune, agent) với cột số liệu của chính
  bạn; người phỏng vấn hỏi lại đúng ở đây.
- Khi lên quy mô, thứ đổi đầu tiên thường không phải model mà là retrieval (index lại, lọc theo hiệu lực, phân quyền) và
  vận hành (eval theo lịch, cổng hồi quy).
- Đọc lại kết luận âm của chính bạn (rerank, fine-tune, agent cho câu một ý): chúng là phần đáng tin nhất của tài liệu.
