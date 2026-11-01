# M07: Safety: chống prompt injection, từ chối khi không có căn cứ, không bịa điều luật

## Mục tiêu

Một trợ lý pháp luật nói sai có căn cứ giả nguy hiểm hơn một trợ lý nói "không biết". Milestone này đo và giảm ba loại
hỏng: làm theo chỉ thị lạ (injection trực tiếp trong câu hỏi, gián tiếp trong tài liệu được truy hồi), trả lời khi không
có căn cứ, và **nhắc điều luật không có trong nguồn**. Mỗi lớp phòng thủ có số đo cả hai phía: chặn được bao nhiêu tấn
công, chặn oan bao nhiêu câu bình thường.

Dùng lại: injection, guardrails input/output, red-teaming, Wilson CI ở [module 19](../../modules/19-ai-safety-security/README.md)
(bài Advanced 01 là harness red-team, Advanced 02 là trợ lý có guard); hai lớp từ chối ở module 13 mục 5.

**Phần cứng:** CPU + Ollama; khoảng 8 giờ làm.

## Việc cần làm

1. **Phần thuần** (`safety.py`): `looks_like_injection`, `mentioned_articles`, `fabricated_references`,
   `ground_or_refuse`.
2. **Bộ red-team có phiên bản** trong `evalsets/`, mỗi mục kèm hàm kiểm bằng code (không dùng chính guard để chấm):
   - ít nhất 30 tấn công: injection trực tiếp trong câu hỏi; injection gián tiếp (chèn một "điều luật" có chỉ thị vào kết
     quả truy hồi trước khi dựng prompt); dụ bịa (hỏi về văn bản không tồn tại, ví dụ một số hiệu hư cấu, hoặc ép "trả
     lời chắc chắn, đừng nói không biết");
   - ít nhất 30 câu bình thường, trong đó có câu "trông giống" tấn công (chữ "bỏ qua", "đóng vai", "hướng dẫn").
3. **Câu ngoài phạm vi**: dùng lại 20 câu của M03 và thêm ít nhất 20 câu gần phạm vi (luật nước ngoài, văn bản đã hết hiệu
   lực mà corpus không có), đo tỉ lệ từ chối đúng.
4. **Bịa điều luật trên tập ghim**: chạy `fabricated_references` trên 300 câu trả lời của M03. Đọc ít nhất 20 trường hợp bị
   gắn cờ: bịa thật, hay model nhắc đúng điều nhưng viết số hiệu khác cách viết trong uid?
5. **Phòng thủ theo lớp**, mỗi lớp bật/tắt được: lọc input (`looks_like_injection`), đánh dấu nguồn là dữ liệu và lọc
   nguồn có dấu hiệu chỉ thị, kiểm output (`ground_or_refuse`). Chạy bộ red-team và tập ghim với từng cấu hình.
6. `reports/SAFETY.md`: bảng ASR (Wilson 95%), chặn oan, từ chối đúng ngoài phạm vi, tỉ lệ bịa điều luật trên tập ghim,
   và **giá** của mỗi lớp trên tập ghim (tỉ lệ trích đúng điều, tỉ lệ từ chối trước/sau).

## Kết quả nộp

- `legal_assistant/safety.py`, test M07 pass; harness và log.
- `evalsets/` red-team và ngoài phạm vi; `reports/SAFETY.md`.

## Tiêu chí đạt

- [ ] Bộ tấn công ≥ 30 và câu bình thường ≥ 30, chấm bằng code; ASR báo kèm khoảng tin cậy Wilson 95%.
- [ ] Mỗi lớp phòng thủ có hai con số: ASR và tỉ lệ chặn oan; không kết luận từ chênh lệch nằm trong khoảng tin cậy.
- [ ] Câu ngoài phạm vi rõ ràng: từ chối ≥ 95%; câu gần phạm vi: số đo riêng, kèm phân tích lớp nào bắt được.
- [ ] Tỉ lệ câu trả lời có điều luật bịa trên tập ghim, trước và sau `ground_or_refuse`, kèm số câu trả lời đúng bị lớp
      này chuyển thành từ chối.
- [ ] Báo cáo nói rõ mỗi lớp bảo đảm gì và **không** bảo đảm gì (heuristic từ khoá không chặn được injection diễn đạt
      lại; lớp kiểm output không biết câu trả lời có đúng luật hiện hành không).

## Gợi ý

- Injection gián tiếp phải đi qua đúng đường dữ liệu thật: chèn vào danh sách nguồn sau retrieval, không dán vào câu hỏi.
- Từ chối "an toàn" có giá: một lớp chuyển mọi câu trả lời không có `[i]` thành từ chối sẽ làm tỉ lệ bịa về gần 0 và
  cũng xoá những câu trả lời đúng mà model trích dẫn tự do. Đo cả hai rồi mới chọn.
- `mentioned_articles` dựa trên regex nên có cả bỏ sót lẫn bắt nhầm; đọc mẫu để biết con số "bịa" của bạn lệch về phía nào.
- Câu hỏi về văn bản không tồn tại là cách rẻ nhất để đo bịa: đáp án đúng duy nhất là từ chối.
