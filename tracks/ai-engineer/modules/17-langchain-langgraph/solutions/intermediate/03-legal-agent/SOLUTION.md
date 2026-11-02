# Lời giải: agent pháp luật bằng LangGraph

## Cách làm

**Hàm nhỏ.**

- `search_query`: thông tin bổ sung rỗng hoặc đã có trong vế thì giữ nguyên vế; ngược lại
  `f"{part.rstrip(' ?')} đối với người điều khiển {extra}?"`. Cách ghép này đo được (mục "Dò thiết kế" bên dưới).
- `select_sources`: với từng vế, sắp evidence của vế đó theo `(-score, uid)`, bỏ uid đã chọn, **rồi** cắt `per_part`.
  Cắt trước khi bỏ trùng thì vế sau mất chỗ khi một điều đã được vế trước chọn. Mỗi vế một hạn mức riêng là điểm khác
  quan trọng nhất so với RAG một lượt: một vế có điểm cao không chiếm hết chỗ của vế kia.
- `build_answer_messages`, `parse_citations`: như bài Intermediate 02 module 13 (số hiệu văn bản ở đầu mỗi nguồn, chỉ
  nhận `[i]` trong `1..n`, bỏ trùng).

**`make_planner`.** `llm.with_structured_output(Plan, method="json_schema")` bọc trong `try`; `None` hay exception đều
rơi về `parts=[question]`, `missing=[]`. `missing = [VEHICLE_SLOT]` khi `traffic_fine and vehicle == "không nói"`: model
chỉ trả các trường hẹp, code quyết định. Vẫn đếm một lượt gọi khi model lỗi, vì chi phí là thật.

**`route_after_plan`, `clarify`.** Hỏi lại khi có `missing` và `asked` chưa bật; ngược lại một `Send("retrieve",
{"part": p, "clarification": ...})` cho mỗi vế. `clarify` gọi `interrupt`, lưu câu trả lời và bật `asked`; cạnh ra của nó
dùng lại `route_after_plan`, nên sau khi hỏi đồ thị đi thẳng tới tra cứu, không lập kế hoạch lại. Chỉ hỏi một lần: người
dùng có thể không biết hoặc không muốn trả lời, và một agent hỏi đi hỏi lại tệ hơn một câu trả lời chung chung.

**`make_retriever`.** Gắn `part` **gốc** (không phải câu truy vấn đã ghép) vào evidence, để `select_sources` tìm lại theo
vế. Reducer `merge_evidence` của bài Basic 02 gộp các nhánh song song.

**`make_answerer`.** Không có nguồn thì từ chối không gọi LLM. Câu hỏi gửi cho bước trả lời mang theo thông tin bổ sung
trong ngoặc, để model biết người dùng đi xe gì. Trích dẫn map ngược số `[i]` về uid.

**`build_legal_agent`, `run_question`.** Bốn node; `plan` và `clarify` cùng định tuyến bằng `route_after_plan`.
`run_question` lặp: `invoke`, đọc `get_state(config).interrupts`, resume bằng `reply_fn` nếu có. Mỗi câu hỏi một thread
mới: chạy câu thứ hai trên cùng thread thì evidence của câu trước vẫn ở trong state và reducer gộp nó vào câu sau.

## Dò thiết kế (trước khi chốt lời giải)

Ba quyết định của bài đến từ số đo trên PC của track (`qwen2.5:3b`, `temperature` 0, `seed` 0, GPU dùng chung, log
`.superpowers/scratch/logs/i03_planner_tuning.log`, `i03_query_variants.log`):

**Schema của kế hoạch.** Đếm số câu bị đánh dấu "thiếu thông tin" trên 10 câu S3 thiếu loại xe, bản đủ thông tin của
chúng, 10 câu hai vế đầu của S2 và 15 (hoặc 20) câu đầu của tập ghim:

| Schema, prompt | method | Thiếu loại xe | Đủ loại xe | Hai vế | Câu thường |
| --- | --- | --- | --- | --- | --- |
| `missing: list[str]` tự do, không ví dụ | `function_calling` | 1/10 | 7/10 | 6/10 | 6/15 |
| như trên | `json_schema` | 0/10 | 3/10 | 2/10 | 0/15 (nhưng tách gần mọi câu thành 2 vế) |
| `missing` tự do, 4 ví dụ | `json_schema` | 0/10 | 0/10 | 3/10 | 0/15 |
| `traffic_fine` + `vehicle: Literal`, ví dụ | `json_schema` | 7/10 | 0/10 | 1/10 | 4/20 |
| như trên, định nghĩa `traffic_fine` hẹp (bản của bài) | `json_schema` | 6/10 | 0/10 | 0/10 | 2/20 |

Trường chữ tự do cho kết quả gần như ngược (hỏi câu đã đủ, bỏ câu thiếu). Ép sang `bool` + `Literal` và để code suy ra
quyết định thì dùng được. Model vẫn **bịa** loại xe ở 4/10 câu thiếu ("xe máy" khi câu không nói), nên không hỏi; và gắn
"xe máy" cho cả các câu nói rõ "ô tô" (không sao với bài này vì code chỉ đọc "không nói"). `function_calling` với schema
mới lỗi parse 3/10 câu hai vế.

**Cách ghép câu trả lời của người dùng vào truy vấn**, đo riêng retrieval (top-5 dense, 10 câu x 2 loại xe):
`"<câu> (xe máy)"` 14/20, `"<câu> xe máy"` 17/20, `"xe máy: <câu>"` 15/20, `"Người điều khiển xe máy <câu>"` 19/20,
`"<câu> đối với người điều khiển xe máy?"` 19/20, câu không có loại xe 8/20. Bản đầu của lời giải dùng dạng ngoặc và lập
kế hoạch lại sau khi hỏi; model biến câu trả lời của người dùng thành một vế rác ("Thông tin bổ sung: xe máy") và chỉ 2/7
câu được hỏi tìm ra điều đúng (log `i03_run_v1_partial.log`). Bản cuối không lập kế hoạch lại và ghép theo văn phong điều
luật.

## Kết quả thật

PC của track, 2026-11-01, `qwen2.5:3b` + `bge-m3` (cache module 13), checkpointer SQLite, GPU dùng chung. Log
`i03_run.log`, `i03_s{1,2,3}.json`, tổng hợp `i03_summary.log`. Cả notebook gọi model khoảng 510 lượt, chạy khoảng 25 đến 40 phút tuỳ mức GPU bị chiếm. Chạy lại chính notebook lời
giải qua `nbconvert` (log `nb_i03_executed.ipynb`) cho **đúng** các số đếm ở ba bảng dưới; chỉ thời gian khác (trung vị S1
2.1 s và 4.3 s, S2 2.5 s và 6.0 s, lúc GPU ít bị chiếm hơn).

**S3, 10 câu thiếu loại xe** (người dùng giả trả lời "xe máy" hoặc "ô tô"):

| | Hỏi lại | Điều đúng trong nguồn | Trích đúng điều |
| --- | --- | --- | --- |
| RAG một lượt (câu thiếu, top-5) | không có | 4/10 | 0/10 |
| Agent | 6/10 | 6/10 (3 trong 6 câu đã hỏi) | 1/10 |
| Agent trên bản đủ thông tin | 0/10 (không hỏi thừa) | 8/10 | |
| RAG trên bản đủ thông tin | | 9/10 | |

**S1, 100 câu thường:**

| | Điều đúng trong nguồn | Trích đúng | Từ chối | Lượt LLM TB | Giây trung vị (p90) |
| --- | --- | --- | --- | --- | --- |
| RAG một lượt (top-5) | 82 | 27 | 44 | 1.00 | 3.0 (7.4) |
| Agent (mỗi vế 3 nguồn) | 78 | 32 | 45 | 2.00 | 5.4 (10.1) |

Agent tách 0/100 câu (đúng: câu thường chỉ một ý), hỏi thừa 3 câu (rừng phòng hộ, biển báo hiệu, sửa biển báo: "mức phạt"
nhưng không phải lỗi của người lái xe). Theo cặp: chỉ agent có điều đúng 1 câu, chỉ RAG 5 câu, vì agent giữ 3 nguồn còn RAG
giữ 5.

**S2, 50 câu hai vế** (RAG top-6 = số nguồn tối đa của agent):

| | Cả hai vế có điều đúng | Số vế có điều đúng (/100) | Trích đúng cả hai vế | Lượt LLM TB | Giây trung vị |
| --- | --- | --- | --- | --- | --- |
| RAG một lượt | 7/50 | 51 | 2 | 1.00 | 3.1 |
| Agent | 34/50 | 81 | 2 | 2.00 | 7.7 |

Agent tách 45/50 câu thành 2 vế, 5 câu không tách (cả hai cách đều 0/5 "cả hai vế" trên 5 câu đó); hỏi lại 5 câu (một vế
là câu phạt giao thông không nói loại xe, như câu gốc của tập ghim).

## Đọc kết quả

- **Agent đáng tiền ở đúng hai chỗ nó được thiết kế cho.** Câu hai vế: một truy vấn embedding cho cả câu bị vế "nặng" kéo
  về một phía, nên RAG chỉ có đủ nguồn cho cả hai vế ở 7/50 câu; tách và tra từng vế với hạn mức riêng nâng lên 34/50.
  Câu thiếu loại xe: hỏi lại rồi tra đúng văn phong đưa điều đúng vào nguồn ở 6/10 câu so với 4/10.
- **Câu một ý thì không.** Agent tốn gấp đôi lượt LLM, gần gấp đôi thời gian, và có ít điều đúng hơn một chút vì giữ 3
  nguồn thay vì 5. Bản production nên **định tuyến**: câu một ý đi RAG một lượt (hoặc agent giữ 5 nguồn khi chỉ có một vế),
  chỉ câu nhiều vế hay thiếu dữ kiện mới đi đường agent.
- **Nguồn đúng chưa phải câu trả lời đúng.** Trích đúng thấp ở mọi cột (27 và 32/100 ở S1, 2/50 cả hai vế ở S2) và gần
  một nửa câu bị từ chối: ở S1 RAG từ chối 31 câu, agent 29 câu **dù điều đúng có trong nguồn**. Phần lớn trường hợp khớp
  với lỗi đơn vị nguồn của mục 5 module 13: trong 31 câu RAG từ chối dù có điều đúng, 22 câu có điều đúng dài hơn 1 500
  ký tự (agent: 23/29); tỉ lệ từ chối là 22/44 khi điều đúng dài và 9/38 khi ngắn (log `refusal_length_split.log`). Với
  điều dài (Điều 5, Điều 6 Nghị định 100/2019 dài hơn 12 000 ký tự), phần trả lời rất có thể nằm sau chỗ cắt và model khi
  đó **đúng** khi từ chối; chúng tôi không kiểm từng câu xem phần trả lời có thật sự nằm sau chỗ cắt không, và 9 câu điều
  ngắn bị từ chối là lỗi của bước trả lời. Sửa trước hết ở retrieval (chọn khoản, như bài Intermediate 02 module 13), không ở
  đồ thị. Đó là việc của capstone milestone 3 và 6.
- **Hỏi lại có giá của nó.** 3/100 câu thường bị hỏi thừa; model bịa loại xe ở một số câu thiếu nên không hỏi. Một bộ đo
  riêng cho hỏi lại (câu thiếu và bản đủ của chúng) là bắt buộc, vì tỉ lệ đúng tổng không cho thấy hai lỗi này.
- 10 câu S3 là ít: mỗi câu là 10 điểm phần trăm. Đủ để thấy chiều, không đủ để báo con số chính xác.

