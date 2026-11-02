# M03: RAG có trích dẫn điều, khoản và đánh giá độ trung thực

## Mục tiêu

Sinh câu trả lời **chỉ dựa trên nguồn** và **trích được tới khoản**, từ chối khi thiếu căn cứ, rồi đo bằng số ba điều:
câu trả lời có trích đúng điều luật trong qrels không, từ chối có đúng lúc không, và mọi khẳng định có nằm trong nguồn
không (faithfulness). Phần sửa quan trọng nhất so với module 13 và 17 là **đơn vị nguồn**: module 17 (bài
Intermediate 03) đo được gần một nửa số câu bị từ chối, và trong 31 câu RAG từ chối dù điều đúng có trong prompt, 22 câu
có điều đúng dài hơn 1 500 ký tự, tức phần trả lời rất có thể nằm sau chỗ cắt. Ở đây nguồn là khoản có địa chỉ.

Dùng lại [module 13](../../modules/13-rag/README.md): prompt có nguồn đánh số, câu từ chối cố định, hai lớp từ chối
(mục 5, bài Intermediate 02), faithfulness bằng judge tách khẳng định và cách kiểm judge bằng nguồn sai (mục 6, bài
Advanced 01), cây debug "retrieval hay generation".

**Phần cứng:** CPU + Ollama (`qwen2.5:3b`, `bge-m3`), GPU 4GB; khoảng 8 tới 10 giờ làm. Một lượt 300 câu với hai cấu
hình là khoảng 600 lời gọi model sinh và vài trăm lời gọi judge.

## Việc cần làm

1. **Đơn vị nguồn** (`chunking.py`): `split_clauses` tách điều theo khoản, khoản dài tách tiếp theo điểm, mỗi passage
   mang `label` ("khoản 2", "khoản 2 điểm a") và mở đầu bằng tiêu đề điều. Đếm số passage vẫn dài hơn giới hạn bạn
   cắt trong prompt.
2. **Prompt và trích dẫn** (`citations.py`): `build_messages`, `parse_citations`, `is_refusal`, `cited_uids`. Dòng đầu
   mỗi nguồn có số hiệu văn bản, số điều và địa chỉ khoản để người đọc kiểm được; model chỉ cần viết `[i]`, code tự map
   ngược về điều.
3. **Một lượt RAG** (`rag.py`): `answer` với cổng điểm (lớp 1, không gọi LLM) rồi một lời gọi LLM (lớp 2: chỉ thị trong
   prompt).
4. **Chọn nguồn cho prompt**: retrieval tốt nhất của M02 lấy vài điều, tách khoản, xếp khoản theo cosine với câu hỏi
   (embed khoản bằng `bge-m3`, cache theo nội dung), giữ top-5 khoản. Giữ thêm một cấu hình đối chứng: 5 **điều** đầu
   của cùng retrieval, mỗi điều cắt ở 1 500 ký tự (cách của module 13 và 17).
5. **Bộ câu ngoài phạm vi** trong `evalsets/`: ít nhất 20 câu tự viết, nửa rõ ràng ngoài lĩnh vực (giá vàng, nấu ăn),
   nửa "gần phạm vi" (luật nước ngoài). Ngưỡng `min_score` chọn từ phân phối điểm của tập dev (M02) và bộ này, không từ
   tập ghim.
6. **Chạy hai pha** trên 300 câu ghim và bộ ngoài phạm vi: retrieve và embed hết, rồi mới sinh (`qwen2.5:3b`,
   `temperature = 0`); cache câu trả lời theo (cấu hình, câu hỏi), lưu độ trễ đo lúc sinh.
7. **Chấm** (`judge.py`): `judge_faithfulness` cho mọi câu không từ chối; `rag_summary` cho mỗi cấu hình. **Kiểm judge**
   trước khi tin nó: chấm lại 30 câu trả lời với nguồn của câu hỏi khác (điểm phải gần 0), và tự gán nhãn ít nhất 30 câu.
8. **Phân tích lỗi** theo cây debug mục 6 module 13: ít nhất 20 câu (từ chối dù có điều đúng, trích sai điều, trả lời
   không có `[i]`, câu judge chấm thấp), xếp loại, có đếm.
9. `reports/RAG.md`: bảng hai cấu hình, ngoài phạm vi, phân phối điểm cổng, kiểm judge, phân tích lỗi, khuyến nghị.

## Kết quả nộp

- `legal_assistant/{chunking,citations,rag,judge}.py`, test M03 pass.
- `scripts/m03_rag.py` (các pha retrieve, generate, judge, report), cache và log.
- `evalsets/` câu ngoài phạm vi; `reports/RAG.md`.

## Tiêu chí đạt

- [ ] Hai cấu hình (5 khoản và 5 điều cắt 1 500 ký tự) trên cùng 300 câu ghim, cùng retrieval, cùng model và prompt.
- [ ] Cấu hình khoản trích đúng điều (`cited_correct`) ở ít nhất 55% câu ghim với `qwen2.5:3b` (bản tham chiếu 60.3%),
      và cao hơn cấu hình cả điều theo số câu thắng ròng.
- [ ] Từ chối dù điều đúng có trong nguồn (`refused_with_hit`) thấp hơn cấu hình cả điều; báo cáo kiểm giả thuyết độ dài
      (bao nhiêu câu loại này có điều đúng dài hơn 1 500 ký tự).
- [ ] Câu ngoài phạm vi: từ chối ít nhất 19/20, và báo riêng bao nhiêu câu do cổng, bao nhiêu do LLM.
- [ ] Faithfulness báo cùng `judge_nan`, số câu được chấm, và kết quả kiểm judge (nguồn sai, nhãn của bạn); báo cáo nói
      rõ điểm judge dùng được tới đâu.
- [ ] Mọi chênh lệch đọc theo số câu; không chọn cấu hình theo chênh faithfulness nhỏ hơn vài câu.

### Số tham chiếu

Bản cài đặt của người soạn, PC của track (RTX 3060 12GB dùng chung với một tiến trình khác), Ollama `qwen2.5:3b`
(mặc định, `temperature = 0`) và `bge-m3`. Retrieval: RRF(BM25 bigram, dense) của M02, lấy 5 điều. Cấu hình khoản: tách 5
điều đó bằng `split_clauses` (`max_chars = 1500`), giữ 5 khoản cosine cao nhất; 28 trên 1 600 khoản đưa vào prompt (320 câu kể cả ngoài phạm vi) vẫn dài hơn 1 500 ký
tự và bị cắt. Cổng `min_score = 0.5` (ngưỡng của module 13, không chọn trên tập ghim). Pha retrieve gồm embed khoản mất
khoảng 7 phút; pha sinh khoảng 30 phút cho 640 câu trả lời.

| 300 câu ghim | 5 điều, cắt 1 500 ký tự | 5 khoản |
| --- | --- | --- |
| Điều đúng có trong nguồn (`context_hit`) | 0.900 | 0.873 |
| Từ chối | 0.243 | **0.153** |
| Từ chối dù điều đúng có trong nguồn | 56 câu | **28 câu** |
| Có ít nhất một trích dẫn `[i]` hợp lệ | 0.580 | **0.720** |
| Trích đúng điều (`cited_correct`) | 0.437 | **0.603** |
| Độ chính xác trích dẫn (`citation_precision`) | 0.642 | 0.622 |
| Trả lời (không từ chối) mà không có `[i]` hợp lệ | 53 câu | 38 câu |
| Độ trễ sinh p50 / p95 | 1.8 s / 4.5 s | 1.8 s / 6.0 s |
| 100 câu ghim đầu: câu trả lời không từ chối được chấm | 74 | 85 |
| Faithfulness trung bình (judge `qwen2.5:3b`) | 0.847 | 0.750 |
| Mọi khẳng định có trong nguồn (điểm 1.0) | 50 / 74 | 45 / 85 |
| `judge_nan` | 0 | 0 |

- **Đơn vị nguồn quyết định**: theo cặp, 102 câu trích đúng ở cả hai cấu hình, 79 câu chỉ đúng với khoản, 29 câu chỉ
  đúng với cả điều: thắng ròng 50 câu, vượt xa nhiễu. Ở cấu hình cả điều, 45 trên 56 câu từ chối dù có điều đúng có
  điều đúng dài hơn 1 500 ký tự: chẩn đoán của module 13 và 17 đứng vững trên 300 câu.
- **Cái giá**: điều đúng có mặt trong nguồn ít hơn một chút (262 so với 270 câu), vì 5 khoản tốt nhất trung bình chỉ đến từ
  2.86 điều khác nhau; khoản dài hơn cũng làm p95 độ trễ sinh tăng.
- **Ngoài phạm vi**: cả hai cấu hình từ chối 20/20, nhưng cổng điểm chỉ chặn 6/20; 14 câu còn lại là LLM từ chối. Điểm
  khoản cao nhất của các câu luật nước ngoài nằm trong khoảng 0.56 tới 0.66, chồng lên phân phối của câu thật (thấp nhất
  0.53, phân vị 5% là 0.62): không có ngưỡng nào tách được hai nhóm, lớp 2 là bắt buộc.
- 18 tới 19 câu trả lời mỗi cấu hình nhắc bằng chữ một điều không có trong nguồn: M07 sẽ đo và xử lý loại lỗi này.
- **Faithfulness: đọc thận trọng.** Judge là `qwen2.5:3b`, cùng model sinh câu trả lời, chạy trên 100 câu ghim đầu (159
  lượt chấm, trung vị 10 giây mỗi lượt trên GPU dùng chung). Kiểm bằng nguồn sai (30 câu trả lời của cấu hình khoản, chấm
  lại với nguồn của câu kế tiếp): trung bình 0.77 với nguồn đúng, 0.25 với nguồn sai, nhưng 9/30 lượt nguồn sai vẫn được
  chấm từ 0.5 trở lên. Judge phân biệt được trung bình mà dễ dãi với từng câu, cùng hướng với module 13. Bản tham chiếu
  **không** có nhãn người, nên không có kappa: đó là phần việc của bạn (và của M08).
- Trên 69 câu cả hai cấu hình đều trả lời, judge chấm cấu hình khoản thấp hơn ở 27 câu, cao hơn ở 8 câu (trung bình 0.741
  so với 0.857). Bản tham chiếu chưa tìm ra nguyên nhân: có thể câu trả lời theo khoản chi tiết hơn (nhiều khẳng định
  hơn, nhiều chỗ để sai), có thể judge 3B chấm khác khi nguồn ngắn; với judge đã thấy dễ dãi như trên, chênh lệch này
  cần judge mạnh hơn và nhãn người trước khi kết luận. Điều chắc chắn hơn: chọn cấu hình theo trích đúng điều (thắng ròng
  50 câu, đo bằng code) chứ không theo điểm judge này.

## Gợi ý

- Cache khoản đã embed theo nội dung (hash văn bản), vì cùng một điều xuất hiện trong top-5 của nhiều câu hỏi.
- `cited_uids` đếm theo điều vì qrels gán nhãn ở mức điều; `label` của khoản vẫn nên hiện trong câu trả lời cho người đọc.
- Câu trả lời đúng nội dung nhưng viết "Theo Điều 5 Nghị định ..." thay cho `[i]` không được tính là có trích dẫn. Đừng
  nới regex để tăng số: sửa ở prompt (ví dụ mẫu) hoặc structured output, rồi đo lại.
- Judge cùng model với model sinh thường dễ dãi; thí nghiệm nguồn sai cho bạn thấy dễ dãi tới đâu với chi phí 30 lời gọi.
  Muốn judge mạnh hơn: `qwen2.5:7b` trên PC hoặc một API (module 13 bài Advanced 01, module 20 mục 2).
