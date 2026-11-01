# M06: Agent LangGraph: tách câu hỏi, tra cứu nhiều bước, hỏi lại khi thiếu thông tin

## Mục tiêu

Biến pipeline RAG một lượt của M03 thành một agent chỉ đi đường dài khi đáng: câu hỏi nhiều vế được tách và tra từng vế,
câu hỏi thiếu dữ kiện (ví dụ mức phạt giao thông không nói loại xe) được **hỏi lại** trước khi tra, câu hỏi một ý thì
không tốn thêm lượt LLM nào. Đo agent với RAG một lượt trên cùng bộ câu hỏi, bằng bộ chấm không dùng LLM.

Đây là bản đầy đủ của bài Intermediate 03 [module 17](../../modules/17-langchain-langgraph/README.md) (đồ thị, `Send`,
reducer, `interrupt`, checkpoint SQLite). Bài đó đo trên PC của track: agent có điều đúng cho **cả hai vế** ở 34/50 câu
hai vế so với 7/50 của RAG một lượt, nhưng trên 100 câu thường thì tốn gấp đôi lượt LLM mà không hơn, và cả hai cách đều
từ chối khoảng 45% câu, phần lớn vì đơn vị nguồn là cả điều cắt ở 1 500 ký tự. Bạn có M03 (nguồn là khoản có địa chỉ)
nên phải làm tốt hơn ở chỗ đó.

**Phần cứng:** CPU + Ollama (`qwen2.5:3b`, `bge-m3`); khoảng 8 tới 10 giờ làm, mỗi lượt đo vài trăm lời gọi model.

## Việc cần làm

1. **Phần thuần** (`agent.py`): `merge_hits` (reducer), `AgentState`, `parse_sub_questions`, `next_step`. Test M06 có
   một `StateGraph` thật để kiểm reducer được nối đúng.
2. **Đồ thị** (script hoặc notebook của bạn): node lập kế hoạch (structured output: các vế, thiếu dữ kiện gì), node hỏi
   lại (`interrupt`), node tra từng vế (song song bằng `Send`, retrieval của M02 + chọn khoản của M03), node trả lời
   (prompt và trích dẫn của M03), cạnh có điều kiện dùng `next_step`. Thiếu dữ kiện do **code** quyết định từ output có
   cấu trúc, không để model tự viết câu hỏi lại tuỳ ý. Checkpoint SQLite; giới hạn số bước.
3. **Bộ câu hỏi** trong `evalsets/` (có phiên bản):
   - S1: 100 câu đầu tập ghim (câu thường);
   - S2: ít nhất 50 câu hai vế ghép từ hai câu ghim khác văn bản, nhãn là hợp hai tập điều đúng;
   - S3: ít nhất 20 câu thiếu dữ kiện tự viết, mỗi câu kèm bản đủ dữ kiện và câu trả lời của "người dùng giả" cho lượt
     hỏi lại.
4. **Đo**: với RAG một lượt (M03) và agent, trên S1, S2, S3: điều đúng có trong nguồn, trích đúng điều (S2: đúng cả hai
   vế), từ chối, từ chối dù có điều đúng, số lượt LLM trung bình, độ trễ trung vị và p90. Trên S3 thêm: hỏi lại đúng
   (câu thiếu), hỏi thừa (bản đủ).
5. **Định tuyến**: nếu agent không hơn RAG ở S1, thêm luật định tuyến (câu một ý đi RAG một lượt) và đo lại cả ba bộ.
6. `reports/AGENT.md`: sơ đồ đồ thị (mermaid), ba bảng, phân tích lỗi (ít nhất 10 câu), khuyến nghị.

## Kết quả nộp

- `legal_assistant/agent.py`, test M06 pass; đồ thị và script đo, log.
- `evalsets/` cho S2, S3; `reports/AGENT.md`.

## Tiêu chí đạt

- [ ] Ba bộ câu hỏi, cùng bộ chấm không dùng LLM, cùng retrieval, cho cả RAG một lượt và agent.
- [ ] S2: agent có điều đúng cho cả hai vế ở nhiều câu hơn RAG một lượt, số câu cụ thể có trong báo cáo.
- [ ] S3: tỉ lệ hỏi lại đúng trên câu thiếu và tỉ lệ hỏi thừa trên bản đủ được báo riêng; hỏi thừa không quá 1/10 bản đủ.
- [ ] S1: với định tuyến, agent không tốn thêm lượt LLM cho câu một ý và không kém RAG một lượt quá 3 câu ở "điều đúng
      trong nguồn".
- [ ] Tỉ lệ từ chối dù có điều đúng trong nguồn trên S1 thấp hơn rõ so với module 17 (31/100 với RAG một lượt, nguồn cả
      điều cắt 1 500 ký tự), có số cụ thể; nếu không, phân tích chỉ ra vì sao.
- [ ] Dừng ở câu hỏi lại, mở kết nối SQLite mới, đi tiếp được (chứng minh bằng log).

## Gợi ý

- Một vế tra với hạn mức nguồn riêng, rồi gộp: nếu gộp xong mới cắt top-k chung, vế "nặng" lại chiếm hết chỗ như RAG
  một lượt.
- Đọc output kế hoạch bằng `json_schema`, nhưng vẫn chịu được JSON hỏng (`parse_sub_questions` trả cả câu).
- Đo số lượt LLM bằng cách đếm lời gọi (bọc client, hoặc `FakeLLM.calls` trong test), không ước lượng.
- Câu thiếu dữ kiện mà model "tự đoán" loại xe thay vì hỏi lại là lỗi khó thấy nhất: bộ S3 có bản đủ và bản thiếu của
  cùng câu để bắt nó.
