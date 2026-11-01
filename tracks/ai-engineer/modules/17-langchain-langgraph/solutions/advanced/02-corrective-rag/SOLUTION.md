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

## Kết quả của bản tham chiếu

PC của track, 2026-11-01, `qwen2.5:3b` (`temperature` 0, `seed` 0) cho cả chấm, viết lại và trả lời, dense `bge-m3` top-5,
câu 0-99 của tập ghim; RAG một lượt là cột RAG của bài Intermediate 03 (cùng chỉ mục, cùng prompt trả lời). Mỗi biến thể
CRAG chạy khoảng 7 phút. Log `.superpowers/scratch/logs/a02_crag_rw{0,1}.json`, `a02_rw*.log`, tổng hợp
`a02_summary.log`.

| | Điều đúng trong nguồn trả lời | Trích đúng | Từ chối không gọi LLM | Model tự từ chối | Lượt LLM TB | Giây trung vị |
| --- | --- | --- | --- | --- | --- | --- |
| RAG một lượt (top-5) | 82 | 27 | | 44 | 1.00 | 3.0 |
| CRAG, không viết lại | 53 | 23 | 31 (22 câu điều đúng có trong top-5) | 43 | 1.95 | 3.2 |
| CRAG, viết lại tối đa 1 lần | 53 | 23 | 31 | 44 | 2.06 | 3.3 |

Bộ chấm (`grader_agreement`, 100 câu x 5 nguồn lượt đầu): giữ trung bình 1.23 nguồn mỗi câu; precision 0.43, recall
0.65; trong các câu điều đúng có mặt trong top-5, bộ chấm giữ được nó ở 65%. Theo cặp với RAG một lượt về trích đúng: 14
câu chỉ RAG trích đúng, 10 câu chỉ CRAG trích đúng.

## Đọc kết quả

- **CRAG làm tệ hơn ở đây, và lý do đo được.** "Trích đúng" không thể vượt "điều đúng có trong nguồn trả lời", và con số
  đó tụt từ 82 xuống 53 vì bộ chấm 3B bỏ điều đúng ở 35% số câu nó có mặt. Bộ chấm chỉ đọc 700 ký tự đầu của mỗi điều; với
  điều dài, phần liên quan nằm sau.
- **Viết lại gần như không chạy.** Bộ chấm hiếm khi bỏ **hết** 5 nguồn (chỉ 5/100 câu), nên vòng sửa sai hầu như không
  kích hoạt, và cả 5 lần viết lại không đưa điều đúng vào nguồn. Lợi ích chính của CRAG trong paper (tìm lại khi
  retrieval hỏng) cần một bộ chấm biết nói "không có gì liên quan"; với bộ chấm này, hơn một nửa số nguồn nó giữ là
  nguồn sai (precision 0.43).
- **Từ chối oan.** 22 câu bị từ chối không qua LLM dù điều đúng nằm trong top-5: đây là chi phí trực tiếp của bộ chấm.
  Chúng là lỗi, không phải "từ chối đúng lúc" kiểu capstone.
- **Cái CRAG làm được**: giảm số nguồn đưa cho model trả lời (1.2 thay vì 5), nên prompt ngắn hơn; ở 10 câu CRAG trích đúng
  mà RAG không, bớt nhiễu giúp model chọn đúng nguồn.
- **Hướng sửa trước khi kết luận "CRAG không đáng"**: chấm theo khoản thay vì 700 ký tự đầu; dùng reranker cross-encoder
  (bài Intermediate 03 module 13) làm bộ chấm thay cho LLM 3B, với ngưỡng chọn trên tập train; chỉ bật vòng viết lại khi điểm
  rerank cao nhất dưới ngưỡng; đo lại bằng chính `grader_agreement`. Với model 7B trên PC, chạy lại cùng bảng để biết phần
  nào là do model nhỏ.

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
