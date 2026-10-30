# Hướng làm: bộ đánh giá RAG với LLM-as-judge

Bài không có code lời giải: harness và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả
của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Đơn vị chấm faithfulness | judge tách câu trả lời thành khẳng định, đánh dấu `supported` từng cái; điểm = tỉ lệ | giống RAGAS; một câu trả lời dài có một ý bịa không bị chấm "0" hay "1" cả cụm, và đọc được judge sai ở khẳng định nào |
| Định nghĩa "được ủng hộ" | ghi rõ trong prompt: đúng theo hiểu biết chung nhưng **không có trong nguồn** là `false` | thiếu câu này judge nhỏ chấm theo kiến thức của nó, đúng loại lỗi cần đo thì lại bỏ qua |
| Relevance | thang 1..5 có mô tả từng mức, `reason` trước `score` | thang nhỏ có định nghĩa ổn định hơn 0..100; viết lý do trước khi cho điểm giúp model nhỏ nhất quán hơn |
| Output | `json_schema` (Ollama `format`), vẫn bọc `try` và kiểm kiểu | schema giảm JSON hỏng nhưng không triệt tiêu (model có thể cắt giữa chừng khi hết `num_ctx`, client OpenAI-compat có thể bỏ qua schema) |
| JSON hỏng | `nan`, đếm ở `judge_nan` | điểm 0 sẽ nói "câu trả lời bịa" trong khi thật ra **chưa chấm được**; `nan` + bộ đếm cho biết trung bình dựa trên bao nhiêu câu |
| Câu từ chối | không gửi judge, tỉ lệ ở cột riêng | câu từ chối không có khẳng định nào; trộn vào faithfulness (dù cho 1 hay 0) đều làm lệch cột |
| Sinh và chấm tách nhau | câu trả lời cache theo (cấu hình, câu hỏi); `RagOutput.seconds` mang độ trễ đo lúc sinh | đổi prompt judge hay model judge không phải sinh lại; độ trễ báo cáo không bị cache làm nhỏ đi |
| Judge khác model sinh | sinh `qwen2.5:3b`, judge `qwen2.5:7b` (trên PC), có kiểm judge bằng nguồn sai và nhãn người | judge cùng model dễ dễ dãi với chính câu của nó (mục 6 lý thuyết) |
| GPU 4GB | hai pha: retrieve hết (bge-m3) rồi mới sinh (qwen2.5:3b) | xen kẽ hai model làm Ollama nạp lại model mỗi lượt, chậm gấp đôi và lẫn thời gian nạp vào độ trễ |

Bản tham chiếu không có nhãn người cho 20 câu (đó là phần việc của bạn); thay vào đó nó so hai judge với nhau, như
bảng dưới. Bạn nên làm cả hai.

Lỗi hay gặp: bắt `json.JSONDecodeError` nhưng quên `KeyError`/`TypeError` (JSON hợp lệ mà sai cấu trúc vẫn crash) hay
`llmkit.LLMError` (một lượt gateway 504 hay Ollama quá thời gian chờ làm hỏng cả lần chạy một giờ);
`isinstance(True, int)` là `True` nên `"score": true` lọt qua; lấy trung bình bằng `np.mean` làm cả cột thành `nan`
khi có một câu hỏng; gửi câu từ chối cho judge; đo độ trễ bằng thời gian gọi hàm khi câu trả lời đã cache (ra 0.0 s).

## Kết quả tham chiếu

50 câu đầu tập ghim, sinh bằng `qwen2.5:3b` theo prompt bài Intermediate 02 (`temperature = 0`), cổng 0.5. Laptop của
track (RTX 3050 4GB). Sinh 200 câu trả lời (4 cấu hình) khoảng 9 phút gồm cả pha retrieval.

| Cấu hình | recall@5 | mrr@10 | context_hit | refused | Độ trễ trung vị |
| --- | --- | --- | --- | --- | --- |
| dense · cả điều (cắt 1 500 ký tự) | 0.84 | 0.680 | 0.84 | 0.34 | 2.6 s |
| dense · khoản | 0.84 | 0.680 | 0.82 | 0.26 | 3.3 s |
| hybrid · khoản | 0.88 | 0.736 | 0.84 | 0.24 | 4.1 s |
| hybrid + rerank · khoản | 0.86 | 0.730 | 0.86 | 0.24 | 38.6 s |

Ba cột retrieval là tất định (cùng cache thì cùng số); `refused` và độ trễ phụ thuộc model và máy.

**Judge.** Do GPU của máy tham chiếu bị chương trình khác chiếm trong lúc chạy (Ollama phải đẩy một phần model sang
CPU), bảng đầy đủ được chấm bằng judge mạnh hơn qua gateway tương thích OpenAI (`OpenAICompatClient`, model
`auto/gemini-3.8-flash`, 292 lượt gọi, trung vị 6.3 giây, khoảng 1 giờ); `qwen2.5:3b` được dùng cho thí nghiệm kiểm judge.
Cùng prompt judge trong cả hai trường hợp.

| Cấu hình | faithfulness | relevance | judge_nan |
| --- | --- | --- | --- |
| dense · cả điều | 0.670 | 0.909 | 0 |
| dense · khoản | 0.682 | 0.932 | 4 |
| hybrid · khoản | 0.705 | 0.888 | 2 |
| hybrid + rerank · khoản | 0.690 | 0.941 | 3 |

`judge_nan` ở đây chủ yếu do gateway trả HTTP 504 hết lượt thử lại (client trả chuỗi rỗng, judge cho `nan`): đúng tình
huống harness phải chịu được mà không mất cả lần chạy.

**Kiểm judge bằng nguồn sai** (câu trả lời của `dense · khoản`, chấm lại với nguồn của câu hỏi kế tiếp):

| Judge | Số câu | Nguồn đúng: trung bình | Nguồn sai: trung bình | Nguồn sai mà chấm ≥ 0.5 |
| --- | --- | --- | --- | --- |
| `qwen2.5:3b` | 15 | 0.76 | 0.15 | 2 (một câu chấm 1.0) |
| `auto/gemini-3.8-flash` | 37 | 0.68 | 0.01 | 1 |

Trên 15 câu chung, hai judge chỉ đồng ý 8/15 về câu nào "mọi khẳng định đều có trong nguồn" (điểm 1.0); 3B cho điểm cao
hơn (0.76 so với 0.63 trên cùng 15 câu). Cùng hướng với bảng ở mục 6 lý thuyết: judge nhỏ dễ dãi.

Đọc kết quả:

- **Đơn vị nguồn quan trọng hơn thứ hạng**: cùng thứ hạng dense, đổi cả điều cắt cụt sang 5 khoản giảm từ chối từ 17
  xuống 13 câu, và số câu **từ chối dù điều đúng có trong nguồn** từ 10 xuống 5. `context_hit` lại hơi giảm (0.84 xuống
  0.82): 5 khoản tốt nhất trung bình chỉ đến từ khoảng 3 điều khác nhau, nên đôi khi bỏ rơi điều đúng ở hạng 4 hoặc 5.
  Recall@5 không thấy được điều này, vì nó đo thứ hạng điều, không đo thứ thật sự vào prompt: đó là lý do harness có
  cột `context_hit`.
- **Hybrid hơn dense trên 50 câu này** (recall@5 +0.04, MRR +0.056), ngược với 300 câu ở bài 01 (dense hơn hybrid ở
  MRR). 0.04 recall là 2 câu: cùng một cặp cấu hình đổi thứ tự khi đổi tập câu hỏi, đúng như cảnh báo về nhiễu của 50 câu.
- **Rerank không đáng tiền ở đây**: MRR 0.730 so với 0.736 của hybrid (trong mức nhiễu), độ trễ gấp gần 10 lần vì
  cross-encoder chạy trên CPU (khoảng 35 giây mỗi câu). Trên GPU hoặc với top-10 thay top-50 thì cần đo lại.
- **Faithfulness không phân biệt được bốn cấu hình**: 0.67 tới 0.71, chênh lệch cỡ một hai câu trả lời trên khoảng 35
  câu được chấm mỗi cấu hình. Báo cáo không được chọn cấu hình theo cột này. Nó vẫn có ích: khoảng 30% khẳng định
  không có trong nguồn là một con số tuyệt đối đáng lo. Đọc 154 khẳng định bị đánh `false` thấy ba nhóm chính: dẫn
  chiếu tự viết sai (số điều, điểm, khoản hoặc loại văn bản không khớp nguồn, như "57/2020/tt-bqp là Nghị định"), câu
  bình luận thêm không có trong nguồn ("nhằm đảm bảo quyền lợi của khách hàng"), và suy rộng quá phần nguồn nói. Relevance cao đều (0.89 tới 0.94): câu trả lời không từ chối hầu như luôn đúng
  trọng tâm, nên cột này ít thông tin ở pipeline này.
- Lưu ý chọn mẫu: cấu hình từ chối nhiều (cả điều, 34%) được chấm trên ít câu hơn và là các câu "dễ" hơn; so
  faithfulness giữa cấu hình có tỉ lệ từ chối khác nhau phải nói điều đó.
- Câu trả lời dùng `[i]` tăng khi nguồn là khoản (18 câu ở cả điều, 24 tới 28 ở các cấu hình khoản).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Harness | 15 | Cấu hình là hàm thay được, câu trả lời cache, độ trễ không bị cache làm sai, chạy lại cả bảng bằng một lệnh |
| Kiểm judge | 25 | Có thí nghiệm nguồn sai và hiệu chỉnh ít nhất 20 câu bằng nhãn của mình; báo tỉ lệ đồng ý, judge sai theo hướng nào; kết luận cột faithfulness dùng được tới đâu |
| Diễn giải trung thực | 20 | Tách chênh lệch thật khỏi nhiễu 50 câu (1 câu = 0.02); không khuyên cấu hình dựa trên chênh lệch nhỏ hơn nhiễu; nêu đánh đổi độ trễ |
| Phân tích lỗi | 15 | Ít nhất 5 câu đọc tận mắt, xếp theo cây debug ở mục 6 lý thuyết, có đếm |
| Chất lượng báo cáo | 10 | Khuyến nghị có số ở đầu, thiết lập tái lập được (model, judge, phần cứng, thời gian), có giới hạn |

Đạt từ 70 điểm. Báo cáo dùng điểm faithfulness để chọn cấu hình mà không có mục kiểm judge, hoặc dùng cùng một model
làm judge cho chính nó mà không nói giới hạn đó, không quá 50 điểm.
