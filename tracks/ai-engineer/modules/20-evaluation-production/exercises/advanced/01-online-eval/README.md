---
title: Eval online - A/B, interleaving, statistical power và drift trên Zalo Legal
level: advanced
services: []
files:
  - path: starter/online.ipynb
    note: 6 hàm TODO, phần mô phỏng tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo cho trưởng nhóm
  - path: tests/test_online.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/20-evaluation-production/exercises/advanced/01-online-eval/starter/online.ipynb
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/advanced/01-online-eval -q
---

## Mục tiêu

Trả lời câu hỏi mà mọi đội ra mắt thay đổi cho người dùng thật phải trả lời: **cần bao nhiêu người dùng để thấy một hồi quy**,
và cách đo nào thấy nhanh nhất. Bạn dựng hai phiên bản retriever (một bản có lỗi cắt câu hỏi), đo khác biệt offline theo
cặp, mô phỏng người dùng click theo mô hình cascade để vẽ đường power của A/B test và interleaving, rồi xem một thay đổi phía
người dùng (gõ không dấu) phá retrieval và phát hiện nó bằng drift.

## Đề bài

**Phần cứng:** CPU · ~300 phút

Thời gian trên là thời gian làm bài (thiết kế, code, chạy, viết báo cáo). Embed 900 câu hỏi qua Ollama `bge-m3` mất khoảng
một phút trên GPU; mô phỏng power vài phút trên CPU. Cần cache `bge-m3.npy` của module 13.

1. Trong `starter/online.ipynb`, cell chấm điểm: `team_draft_interleave`, `interleave_outcome`, `cascade_clicks`,
   `ab_sample_size`, `sign_test_pvalue`, `psi`, đúng mô tả trong notebook (thứ tự gọi RNG là một phần của đặc tả).
2. Phần `explore` là thiết kế của bạn, theo năm bước gợi ý trong notebook: thứ hạng A/B, offline theo cặp, mô phỏng power
   (tham số click mặc định, 300 thí nghiệm mỗi mức người dùng, lưới 100 tới 6 400), drift (MRR khi gõ không dấu, PSI của
   đặc trưng bạn chọn), so `ab_sample_size` với mô phỏng.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt** để trưởng nhóm quyết định trong 5 phút:

- Mở bằng **khuyến nghị có số**, ví dụ minh hoạ với số bịa: "lỗi cắt câu hỏi bị eval offline 300 câu bắt được (khoảng
  tin cậy của hiệu không chứa 0); online, A/B cần khoảng X người dùng, interleaving khoảng Y; nên chặn ở offline".
- Đường power của hai phương pháp (bảng hoặc hình) và **giải thích vì sao** chúng khác nhau, gồm cả lý do interleaving ở đây
  lợi ít hay nhiều so với con số "10 tới 100 lần" hay được trích.
- Mục **giả định của mô phỏng**: mô hình click, tham số, người dùng là câu hỏi lấy lại có hoàn lại từ 300 câu; kết luận nào
  nhạy với giả định nào.
- Mục **drift**: MRR khi gõ không dấu, đặc trưng và ngưỡng PSI bạn đề xuất, PSI giữa hai tập "bình thường" để làm mốc.
- **Giới hạn**: người dùng mô phỏng, một cặp hệ thống, một bộ dữ liệu.

## Tiêu chí đạt

- `team_draft_interleave` đúng ví dụ có đồng xu cho trước, chỉ tung đồng xu khi hai đội bằng nhau, giữ thứ tự xếp hạng
  của mỗi đội, chuyển lượt khi một đội hết phần tử; trên 400 cặp ngẫu nhiên đội chọn trước là A khoảng một nửa.
- `cascade_clicks` gọi RNG đúng số lần và đúng thứ tự; tỉ lệ click khớp tham số.
- `ab_sample_size` đúng hai giá trị tính tay (1 094 và 388) và tăng khoảng bốn lần khi chênh lệch giảm một nửa;
  `sign_test_pvalue` khớp `scipy.stats.binomtest`; `psi` đúng ví dụ và hữu hạn khi có bin rỗng.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Tính trước ma trận thứ hạng top-10 của cả hai hệ thống cho 300 câu và lưu ra đĩa; mô phỏng chỉ cần chỉ số câu hỏi và hai
danh sách id, không cần gọi model nữa. Ước tỉ lệ thành công thật của mỗi hệ thống bằng một mô phỏng rất lớn (vài trăm nghìn
người dùng) trước khi so với `ab_sample_size`.

### Gợi ý 2

Interleaving chỉ có tín hiệu ở những câu hỏi mà hai hệ thống trả khác nhau; đếm xem bao nhiêu câu như vậy và số lượt hoà.
Với drift, một đặc trưng rẻ, tính được trên từng câu hỏi mà không cần model (ví dụ tỉ lệ ký tự mang dấu tiếng Việt) thường
đủ để bắt đúng loại thay đổi này; giải thích vì sao embedding drift cũng bắt được nhưng đắt hơn.
