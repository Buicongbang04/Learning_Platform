# Lời giải: Corrective RAG

Bài này không có một đáp án duy nhất. Phần dưới là hướng làm, các quyết định cần cân nhắc, kết quả của bản tham chiếu
(chạy ngoài repo, cùng điều kiện với bài Intermediate 03), và rubric chấm.

## Hướng làm

**`crag.py`.** `decide_next`: còn nguồn được giữ thì `"answer"`; không còn mà `rewrites < max_rewrites` thì `"rewrite"`;
còn lại `"refuse"`. `grader_agreement`: duyệt từng lượt chấm, chỉ xét các uid đã đưa cho bộ chấm; đếm giữ-đúng, giữ-sai,
bỏ-đúng; mẫu số 0 thì `None`; `gold_kept_rate` chỉ tính các lượt mà điều đúng **có mặt** trong nguồn được chấm (lượt không
có điều đúng thì bộ chấm không có gì để giữ).

**Đồ thị.** State: `question`, `query`, `hits`, `relevant`, `rewrites`, `graded` (reducer `operator.add`, mỗi lượt chấm
một bản ghi `{"round", "uids", "relevant"}`), `answer`, `sources`, `citations`, `llm_calls` (cộng). Node:

- `retrieve`: `index.search(query, 5)`.
- `grade`: **một** lượt LLM chấm cả 5 nguồn (mỗi nguồn 700 ký tự đầu), structured output `Grades(relevant: list[int])`
  bằng `function_calling`; lọc số ngoài `1..5`. Chấm từng nguồn một lượt chính xác hơn nhưng gấp 5 lần lượt LLM.
- `decide_next` làm cạnh có điều kiện tới `answer`, `rewrite` hoặc `refuse`.
- `rewrite`: structured output `Rewrite(query)` với prompt "viết lại bằng thuật ngữ văn bản luật"; lỗi thì giữ câu hỏi.
- `answer`: `build_answer_messages` của bài Intermediate 03 chỉ với các nguồn được giữ; `refuse`: câu từ chối, không gọi
  LLM.

**Quyết định cần cân nhắc.**

- **Bộ chấm lỗi thì sao.** Giữ hết (an toàn cho recall, CRAG suy biến thành RAG một lượt) hay bỏ hết (an toàn cho
  "không bịa", nhiều câu bị từ chối oan). Bản tham chiếu giữ hết.
- **Chấm trên bao nhiêu chữ.** Điều luật dài (Điều 5 Nghị định 100/2019 dài hơn 15 000 ký tự); 700 ký tự đầu thường chỉ là
  phần mở đầu, phần trả lời nằm sâu hơn, nên bộ chấm bỏ oan điều đúng. Chấm theo khoản (module 13 mục 2) là hướng sửa.
- **Từ chối là hành vi đúng** khi không có căn cứ (capstone), nhưng từ chối oan một câu có điều đúng trong top-5 là lỗi
  của bộ chấm. Đếm riêng hai loại.

PLACEHOLDER_A02_RESULTS

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt khi |
| --- | --- | --- |
| `crag.py` | 10 | Test xanh |
| Đồ thị CRAG đúng | 15 | Vòng retrieve, grade, rewrite có ngân sách; trả lời chỉ từ nguồn được giữ; từ chối không gọi LLM; mọi lượt chấm được ghi |
| Thí nghiệm công bằng | 20 | RAG một lượt và ít nhất hai biến thể CRAG trên đúng 100 câu ghim, cùng model, cùng chỉ mục, cùng prompt trả lời; kết quả lưu ra tệp |
| Đo bộ chấm | 20 | `grader_agreement` cho mỗi biến thể; nối "trích trúng" của CRAG với tỉ lệ giữ điều đúng của bộ chấm |
| Phân tích lỗi | 20 | Ít nhất 5 câu CRAG tệ hơn RAG một lượt, đọc nguồn và lý do; tách từ chối oan với từ chối đúng |
| Kết luận | 15 | Gắn với số và chi phí (lượt LLM, giây); nói rõ khi nào CRAG đáng dùng cho capstone và cần sửa gì trước |

Trừ điểm nặng: chọn ngưỡng hay prompt bằng cách nhìn kết quả trên chính 100 câu đánh giá rồi báo con số trên chính chúng;
chỉ báo "trích trúng" mà không báo từ chối.
