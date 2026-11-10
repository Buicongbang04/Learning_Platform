# M05: Fine-tune embedding (hoặc LLM bằng QLoRA) trên dữ liệu luật, so trước/sau

## Mục tiêu

Trả lời câu hỏi mọi trưởng nhóm sẽ hỏi: fine-tune có đáng tiền ở hệ này không. Bạn fine-tune **embedding model** cho
retrieval (khuyên dùng) hoặc LLM sinh câu trả lời bằng QLoRA, trên split train, rồi so trước/sau trên đúng 300 câu ghim
với cùng pipeline. Kết luận "không đáng" là kết luận tốt nếu số nói vậy.

Dùng lại: contrastive learning và InfoNCE ở [module 12](../../modules/12-embeddings-vector-db/README.md); LoRA, QLoRA,
chuẩn bị dữ liệu, khi nào fine-tune ở [module 14](../../modules/14-fine-tuning-llm/README.md). Bài Advanced 02 module 14
đã đo trên chính tập ghim: Qwen2.5-0.5B SFT closed-book chỉ trích đúng điều ở 2/300 câu, so với 130/300 của BM25 top-1.
Vì vậy milestone này **không** lặp lại "dạy LLM nhớ luật"; chỗ fine-tune có cơ hội là embedding và cách đọc nguồn.

**Phần cứng:** GPU 12GB (PC) cho `bge-m3` (568M tham số); laptop GPU 4GB dùng embedding nhỏ hơn (ví dụ
`intfloat/multilingual-e5-small`) và so trước/sau của chính model đó. Khoảng 8 tới 12 giờ làm; embed lại corpus sau
fine-tune là phần tốn máy nhất (module 13: 45 phút cho `bge-m3` trên laptop).

## Việc cần làm

1. **Dữ liệu** (`finetune_data.py`): `training_pairs` từ split train; `hard_negatives` từ top-k BM25 hoặc hybrid của
   M01, M02 (thử cả `skip_same_law`). Chạy `check_no_leak(train, tập ghim)`: với dữ liệu gốc nó **phải báo lỗi** (M01 đã
   đếm số câu trùng). Quyết định bỏ những câu nào khỏi train, ghi vào báo cáo, rồi chạy lại cho tới khi qua.
2. **Tách dev**: giữ lại một phần split train (ví dụ 300 câu) làm dev cho early stopping và chọn siêu tham số. Tập ghim
   chỉ dùng để báo cáo cuối.
3. **Fine-tune embedding**: loss kiểu InfoNCE với mẫu âm trong lô (ví dụ `MultipleNegativesRankingLoss` của
   sentence-transformers), có và không có hard negative. Ghi số bước, thời gian, VRAM.
4. **Đo trước/sau**: embed lại corpus bằng model mới (cache riêng, không ghi đè cache cũ), chạy lại dense và hybrid của
   M02 trên tập ghim. Báo cáo R@1, R@10, MRR@10, số câu thắng/thua theo cặp so với model gốc.
5. (Tuỳ chọn) **QLoRA cho LLM đọc nguồn**: SFT trên (câu hỏi, các khoản đã truy hồi, câu trả lời có trích dẫn) và đo
   bằng harness M03 trên 100 câu. Câu trả lời mẫu để train lấy từ đâu, có bị lẫn câu ghim không, là câu hỏi bạn phải
   trả lời trong báo cáo.
6. **Kết luận chi phí**: thời gian train, thời gian embed lại, dung lượng, và việc phải embed lại toàn bộ mỗi khi đổi
   model. So với cải tiến rẻ hơn đã có (bigram cho BM25 ở M01, hybrid ở M02).

## Kết quả nộp

- `legal_assistant/finetune_data.py`, test M05 pass; script train và đo, log.
- `reports/FINETUNE.md`: dữ liệu (số cặp, số câu bị loại vì trùng), cấu hình train, bảng trước/sau trên tập ghim và dev,
  phân tích theo cặp, chi phí, khuyến nghị.

## Tiêu chí đạt

- [ ] `check_no_leak` qua trên dữ liệu train cuối cùng; báo cáo ghi số câu đã loại và lý do.
- [ ] Trước/sau đo trên **cùng** 300 câu ghim, cùng pipeline (cùng chuẩn hoá, cùng `k`, cùng cách tính hybrid).
- [ ] Siêu tham số và điểm dừng chọn trên dev, không trên tập ghim.
- [ ] Mức thay đổi được nói bằng số câu thắng/thua; chỉ gọi là "cải thiện" khi số câu thắng ròng từ khoảng 6 câu trở
      lên (0.02 trên 300 câu), còn lại là "trong mức nhiễu".
- [ ] Có bảng chi phí (train, embed lại, lưu trữ) và khuyến nghị dùng hay không dùng, kể cả khi kết quả âm.

## Gợi ý

- Câu hỏi train nào có cùng `query-id` với câu ghim? Nhãn của chúng ở hai split có giống nhau không? Câu trả lời quyết
  định đó là rò rỉ nhãn hay chỉ rò rỉ câu hỏi, và cả hai đều không được để trong train.
- Hard negative cùng văn bản với điều đúng (điều liền kề của cùng nghị định) nhiều khi cũng "đúng một phần"; đẩy chúng
  ra xa có thể làm hỏng câu khác. Đo cả hai cách.
- Batch lớn hơn nghĩa là nhiều mẫu âm trong lô hơn; trên GPU nhỏ, gradient caching hoặc giảm độ dài tối đa của đoạn
  văn bản là đòn bẩy trước khi giảm batch.
- Nếu model sau fine-tune tốt hơn trên dev mà không hơn trên tập ghim, tin tập ghim, và tìm khác biệt giữa hai tập (phân
  bố văn bản, loại câu hỏi).
