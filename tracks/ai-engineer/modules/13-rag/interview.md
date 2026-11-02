# Câu hỏi phỏng vấn: RAG

## RAG là gì, giải quyết vấn đề gì của LLM? Khi nào bạn KHÔNG dùng RAG?

RAG (Retrieval-Augmented Generation, Lewis et al. 2020) tìm vài đoạn tài liệu liên quan tới câu hỏi rồi đưa vào prompt,
yêu cầu LLM chỉ trả lời dựa trên đó và trích nguồn. Nó xử lý ba giới hạn của LLM đứng một mình: **knowledge cut-off**
(văn bản mới chỉ cần thêm vào index), **không có dữ liệu riêng** (index nằm trong hạ tầng của bạn, lọc được theo quyền),
và **không kiểm chứng được** (mỗi ý trỏ về một đoạn nguồn).

Không dùng RAG khi:

- Thứ thiếu là **hành vi** chứ không phải kiến thức (định dạng, văn phong, kỹ năng): prompt tốt hơn hoặc fine-tune.
- Tài liệu **vừa context** và ít câu hỏi (một hợp đồng, một báo cáo): long context + prompt caching đơn giản hơn và
  không có lỗi retrieval.
- Câu hỏi cần **tổng hợp toàn kho** ("có bao nhiêu văn bản nhắc tới thuế"): retrieval chỉ trả top-$$k$$, đây là việc
  của truy vấn có cấu trúc trên metadata hoặc GraphRAG.
- Dữ liệu **thời gian thực** từ hệ thống khác (tồn kho, giá): gọi tool/API trực tiếp.

Ứng viên tốt nói thêm hệ quả quan trọng nhất: chất lượng câu trả lời bị chặn trên bởi retrieval. Đoạn đúng không có
trong top-$$k$$ thì model giỏi đến đâu cũng chỉ còn từ chối hoặc bịa.

## RAG hay fine-tuning? Một khách hàng muốn "fine-tune model trên toàn bộ văn bản luật để nó trả lời luật". Bạn tư vấn gì?

Tách hai câu hỏi: thiếu **kiến thức** hay thiếu **hành vi**. Fine-tune trên văn bản luật để "nhồi" kiến thức gần như luôn
sai hướng:

- Không trích được nguồn: kiến thức tan vào trọng số, luật sư không kiểm được câu trả lời.
- Lỗi thời ngay khi luật đổi; mỗi lần cập nhật phải train lại.
- Model vẫn bịa ở chỗ nhớ không chắc, và bịa với giọng tự tin của dữ liệu fine-tune.
- Không phân quyền được theo người dùng.

Tư vấn: RAG cho kiến thức (61 425 điều luật Zalo là khoảng 20 triệu token, không context nào chứa nổi, nên long context
cũng loại). Fine-tune chỉ ở chỗ có lợi đo được: fine-tune **embedding model** trên cặp (câu hỏi, điều luật) của split
train để retrieval tốt hơn, hoặc fine-tune generator để luôn trả lời theo khuôn "Căn cứ điểm a khoản 2 Điều ... thì ...".
Hai thứ kết hợp được, và quyết định dựa trên tập đánh giá chứ không dựa trên cảm giác.

## Bạn chọn chunk size thế nào?

Không có con số đúng cho mọi corpus; có **quy trình**:

1. **Nhìn phân phối độ dài và cấu trúc** trước. Zalo Legal: trung vị 829 ký tự một điều nhưng p99 là 7 510 và dài nhất
   252 881. Chọn theo trung vị thì 10% đuôi dài hỏng âm thầm.
2. **Ưu tiên ranh giới tự nhiên**: văn bản luật cắt theo Khoản, khoản dài thì theo Điểm; Markdown theo heading; code theo
   hàm. Mỗi chunk là một đơn vị nghĩa và có địa chỉ trích dẫn.
3. **Giới hạn trên** là context của embedding model và "độ mờ" của vector: Ollama chạy `bge-m3` cắt im lặng ở 4 096 token
   (khoảng 16 000 ký tự tiếng Việt), và một vector cho cả chục khoản là trung bình mờ của chục ý.
4. **Giới hạn dưới**: chunk quá nhỏ mất ngữ cảnh ("Mức phạt từ 800 000 đồng" không nói phạt vì gì). Giải bằng cách ghép
   tiêu đề Điều và số hiệu văn bản vào mỗi chunk, không phải bằng chunk to hơn.
5. **Đo**: chạy recall@k, MRR trên tập đánh giá cố định với vài cấu hình (ví dụ cả điều, theo khoản, cố định 500 ký tự),
   đồng thời nhìn số token đưa vào prompt.

Vùng khởi đầu cho tiếng Việt: 300 tới 1 000 ký tự (khoảng 80 tới 250 token), overlap 10 tới 20% nếu cắt cố định. Overlap
$$O = S/2$$ gần như nhân đôi số vector theo $$\lceil (L - O)/(S - O) \rceil$$ mà không tăng thông tin.

## Vì sao với văn bản luật, hybrid (BM25 + dense) thường tốt hơn dense thuần?

Hai nhánh hỏng ở chỗ khác nhau:

- **Dense** giỏi diễn đạt khác chữ cùng nghĩa ("bằng lái" và "giấy phép lái xe"), yếu với thứ cần khớp chính xác: số hiệu
  văn bản ("100/2019/NĐ-CP"), con số, tên cơ quan, thuật ngữ pháp lý hiếm mà embedding model ít gặp khi train.
- **BM25** khớp chính xác và có IDF tự hạ trọng số từ phổ biến ("quy", "định" có trong 78 tới 85% số điều, IDF 0.16 tới 0.25),
  nhưng không biết đồng nghĩa.

Văn bản luật có nhiều thứ thuộc loại thứ hai, câu hỏi người dân lại hay diễn đạt kiểu thứ nhất, nên hai nhánh bổ sung cho
nhau. Fuse bằng **RRF** $$\sum_r \frac{1}{60 + \mathrm{rank}_r(d)}$$ vì nó chỉ dùng thứ hạng, không phải chuẩn hoá hai thang
điểm khác nhau. Trên lát cắt 100 câu của module: BM25 âm tiết MRR@10 0.686, dense `bge-m3` 0.751, hybrid 0.773;
thêm bigram âm tiết vào nhánh BM25 thì hybrid lên 0.825 và R@1 từ 0.64 (dense) lên 0.74. Ứng viên tốt nói thêm hybrid không
tự động thắng: RRF với một nhánh yếu có thể kéo thứ hạng xuống, nên đo từng cấu hình.

Câu hỏi tiếp hay gặp: tiếng Việt tách âm tiết hay tách từ cho BM25? Âm tiết là baseline chạy ngay nhưng mất nghĩa từ ghép
("bằng" trong "bằng lái" lẫn với giới từ "bằng"); thêm bigram âm tiết hoặc tách từ (pyvi, VnCoreNLP) và **đo**, với điều kiện
tài liệu và câu hỏi đi qua cùng một tokenizer.

## Giải thích recall@k, MRR và nDCG. Khi nào dùng cái nào?

- **Recall@k**: tỉ lệ tài liệu đúng lọt vào top-$$k$$. Trả lời "đoạn đúng có tới được prompt không", và là **trần** của mọi
  bước sau (rerank, LLM).
- **MRR@k**: trung bình $$\frac{1}{\mathrm{rank}}$$ của tài liệu đúng đầu tiên. Hợp khi mỗi câu có một đáp án chính (Zalo trung
  bình khoảng 1 điều một câu) và khi prompt chỉ chứa vài nguồn đầu.
- **nDCG@k**: $$\sum_i \frac{\mathrm{rel}_i}{\log_2(i+1)}$$ chia cho giá trị lý tưởng. Tính cả vị trí lẫn nhiều tài liệu đúng,
  dùng được với nhãn nhiều mức.

Ví dụ: đúng là {A, B}, hệ thống trả [C, A, D, B, E] thì Recall@3 = 0.5, MRR = 0.5, nDCG@5 = 1.0616 / 1.6309 = 0.6509.

Ứng viên senior nói thêm: chọn $$k$$ của metric **khớp với $$k$$ thật** đưa vào prompt; báo cáo theo từng nhóm câu hỏi chứ không
chỉ trung bình; qrels thường **thiếu** (đoạn khác cũng trả lời được nhưng không được gán nhãn), nên metric thấp chưa chắc
hệ thống sai, phải đọc mẫu.

## Cross-encoder reranker khác bi-encoder thế nào? Có nên luôn rerank không?

Bi-encoder embed câu hỏi và tài liệu **độc lập** nên tài liệu tính trước được, tìm trong triệu vector mất vài mili giây.
Cross-encoder đưa **cặp** (câu hỏi, tài liệu) vào cùng một Transformer, attention chạy qua lại hai bên, chính xác hơn nhưng
không tính trước được gì: mỗi câu hỏi tốn $$K$$ lượt forward cho $$K$$ ứng viên. Vì vậy thiết kế chuẩn là hai tầng: retrieval
rẻ lấy top 50 tới 100, cross-encoder xếp lại còn 3 tới 8.

Số đo trong module (rerank top-20 hybrid, 100 câu Zalo Legal): `bge-reranker-v2-m3` nâng R@1 từ 0.66 lên 0.71, MRR@10 từ
0.773 lên 0.782, tốn 0.59 giây mỗi câu trên GPU 4GB fp16 nhưng 14 giây trên CPU. `qwen2.5:3b` chấm điểm từng đoạn thì kéo MRR
xuống 0.599 và mất 15.6 giây mỗi câu.

Không luôn rerank: khi recall@$$K$$ còn thấp thì rerank không cứu được (trần của nó là recall@$$K$$); khi ngân sách độ trễ chặt
thì đổi $$K$$, cắt độ dài tài liệu, chạy GPU trước khi bỏ hẳn. LLM nhỏ làm reranker thì chậm hơn cross-encoder nhiều lần
mà không chính xác hơn.

## Làm sao bắt LLM trích dẫn đúng, và làm sao biết trích dẫn đúng?

Phía prompt:

- Đánh số nguồn `[1]..[k]`, mỗi nguồn kèm số hiệu văn bản và tiêu đề Điều; yêu cầu ghi `[số]` sau mỗi ý. Không bắt model
  chép số hiệu văn bản: model nhỏ chép sai rất thường, còn số thứ tự thì code map ngược được.
- Câu từ chối cố định để code nhận ra.
- Ít nguồn, nguồn tốt nhất đặt đầu ("lost in the middle").

Phía code (đây là phần hay bị quên):

- Parse `[i]`, **bỏ số ngoài 1..k** (model có thể viết `[7]` khi chỉ có 5 nguồn), bỏ trùng, map về id điều luật.
- Câu trả lời không có trích dẫn nào mà cũng không phải câu từ chối: đánh dấu để xem lại hoặc hỏi lại.
- Đo **citation accuracy**: với từng cặp (câu, nguồn được trích), nguồn đó có thật sự ủng hộ câu không (judge hoặc người).

Trích dẫn đúng định dạng chưa có nghĩa là đúng nội dung: model có thể gắn `[2]` vào một ý mà nguồn 2 không nói.

## Làm sao đo hallucination của hệ RAG?

Trong RAG, hallucination được định nghĩa theo **faithfulness** (groundedness): khẳng định trong câu trả lời có được nguồn
ủng hộ không. Câu đúng sự thật nhưng không có trong nguồn vẫn tính là không faithful, vì người dùng không kiểm được.

Cách đo:

1. Tách câu trả lời thành các khẳng định nguyên tử (bằng LLM).
2. Với từng khẳng định, hỏi judge "nguồn có ủng hộ không" (nhị phân), hoặc dùng model NLI.
3. Faithfulness = tỉ lệ khẳng định được ủng hộ; hallucination rate = tỉ lệ câu trả lời có ít nhất một khẳng định không được
   ủng hộ.

Kèm theo: tập câu hỏi **ngoài phạm vi** để đo từ chối (hệ không bịa khi corpus không có đáp án), và citation accuracy.

Điều kiện để tin con số: judge được **hiệu chỉnh** với 30 tới 50 câu người chấm, judge mạnh hơn hoặc khác họ model được chấm,
thang điểm nhỏ có định nghĩa. Trong module, judge `qwen2.5:3b` chấm 5/5 "hoàn toàn có trong nguồn" cho 2 trên 13 câu trả
lời đi kèm nguồn **không liên quan**, nghĩa là nó bỏ sót đúng loại lỗi cần bắt; `qwen2.5:7b` chấm cả 13 trường hợp đó 1 điểm.

## RAG trả lời sai. Bạn debug từ đâu: retrieval hay generation?

Từ **retrieval**, vì nó rẻ để kiểm và là trần của mọi thứ phía sau. Cần trace của câu hỏi đó (top-k kèm điểm từng nhánh,
prompt cuối, câu trả lời):

1. **Đoạn đúng có trong top-k đưa vào prompt không?**
   - Không, và cũng không có trong top-100 của nhánh nào: lỗi chunking/index. Đoạn bị cắt mất, quá dài nên embedding bị
     truncate, sai Unicode (NFD), tokenizer index khác tokenizer query, tài liệu chưa được index, bị lọc nhầm bởi ACL hoặc
     metadata.
   - Có trong top-100 nhưng không trong top-k: lỗi xếp hạng. Thêm hybrid, rerank, tăng $$k$$.
2. **Có trong prompt, nhưng câu trả lời sai:**
   - Model từ chối: prompt quá khắt khe, hoặc model quá nhỏ để suy luận (đoạn chỉ trả lời gián tiếp).
   - Model bịa thêm: faithfulness. Siết prompt, ít nguồn hơn, model lớn hơn.
   - Model hiểu sai: chunk thiếu ngữ cảnh (không có tiêu đề Điều, khoản dẫn chiếu sang điều khác không được kéo theo).
3. **Câu hỏi không có đáp án trong corpus**: vấn đề là ngưỡng từ chối, không phải retrieval.

Sau khi sửa, thêm câu đó vào tập đánh giá (regression test) và chạy lại cả tập: sửa một câu thường làm hỏng câu khác.

## LLM-as-judge có đáng tin không? Dùng thế nào cho đúng?

Mở rộng được nhưng có lỗi đã biết: thiên vị vị trí khi so A/B, thiên vị câu trả lời dài, thiên vị model cùng họ, không ổn
định giữa các lần gọi, và judge nhỏ phân biệt kém. Trong module, cho 13 câu trả lời đi kèm nguồn của câu hỏi khác, judge `qwen2.5:3b` vẫn chấm 3 câu từ 3 điểm trở lên
(hai câu 5/5), judge `qwen2.5:7b` chấm cả 13 câu 1 điểm.

Dùng cho đúng:

- Thang nhỏ có định nghĩa từng mức (hoặc nhị phân), output JSON có schema, temperature 0.
- Hiệu chỉnh với người chấm trên 30 tới 50 câu: tỉ lệ đồng ý, tương quan. Không đạt thì không dùng con số.
- Judge mạnh hơn model được chấm; đổi chỗ A/B và lấy trung bình; chấm nhiều lần.
- Kiểm **khả năng phân biệt**: đưa cặp "câu trả lời + nguồn sai" vào, judge phải chấm thấp.
- Dùng judge để **so tương đối** giữa hai cấu hình trên cùng tập, ít tin giá trị tuyệt đối; luôn đọc mẫu.

## Bảo mật đa người dùng: làm sao để người dùng A không đọc được tài liệu của người dùng B qua RAG?

Nguyên tắc: **lọc quyền trong retrieval**, không phải trong prompt. Nếu tài liệu B đã vào context, không chỉ thị nào đảm bảo
model không lộ nó.

- Mỗi chunk mang metadata quyền: `tenant_id`, nhóm, mức mật, kế thừa từ tài liệu gốc lúc index.
- Câu truy vấn luôn kèm **filter bắt buộc** theo quyền của người hỏi, áp **trong** truy vấn vector và BM25 (pre-filter), lấy
  từ phiên đăng nhập phía server, không lấy từ input người dùng.
- Cẩn thận post-filter: lấy top-k rồi mới lọc thì có thể còn 0 kết quả, hoặc lộ qua số lượng và độ trễ. Vector DB hiện đại hỗ
  trợ filtered ANN; multi-tenant mạnh thì tách collection/namespace theo tenant.
- Quyền đổi (nhân viên nghỉ, tài liệu chuyển mật) phải được đồng bộ vào index; cache câu trả lời phải có khoá theo quyền,
  nếu không người B nhận câu trả lời cache của A.
- Embedding và log cũng là dữ liệu nhạy cảm: vector có thể bị đảo ngược một phần ra văn bản; trace chứa nội dung tài liệu.
- Prompt injection qua tài liệu (module 19): tài liệu do người dùng tải lên có thể chứa chỉ thị; RAG không được kích hoạt
  hành động có tác dụng phụ dựa trên nội dung đó.

Kiểm bằng test tự động: với mỗi vai trò, chạy bộ câu hỏi nhắm vào tài liệu của vai trò khác, khẳng định không chunk nào trái
quyền xuất hiện trong context.

## Thiết kế hệ thống: RAG cho 1 triệu văn bản nội bộ, p95 dưới 2 giây.

Làm rõ trước: văn bản dài bao nhiêu (giả sử trung bình 5 trang, cỡ 10 chunk mỗi văn bản, tức 10 triệu chunk), bao nhiêu câu
hỏi mỗi giây ở giờ cao điểm, có phân quyền không, tần suất cập nhật, ngôn ngữ, ngân sách.

**Ngân sách độ trễ** (p95, xếp theo đường đi của câu hỏi):

| Bước | Ngân sách | Ghi chú |
| --- | --- | --- |
| Embed câu hỏi | 30 ms | model embedding trên GPU, batch theo request đồng thời |
| BM25 + ANN song song, có filter quyền | 80 ms | HNSW cho 10 triệu vector 1 024 chiều: float32 cỡ 40 GB, dùng quantization (int8/PQ) hoặc shard |
| RRF + rerank top-30 | 150 ms | cross-encoder trên GPU, cắt 512 token |
| LLM tới token đầu tiên | 600 ms | prompt cỡ 3 000 token; streaming nên người dùng thấy chữ sớm |
| Sinh câu trả lời | phần còn lại | 2 giây thường tính tới **token đầu** hoặc câu trả lời ngắn; nói rõ với người hỏi |

**Kiến trúc**: pipeline index bất đồng bộ (queue, idempotent theo `doc_id` + hash nội dung, chỉ embed lại chunk đổi); search
engine hỗ trợ hybrid và filter (OpenSearch/Elasticsearch, Qdrant, Weaviate, hoặc Postgres + pgvector ở quy mô nhỏ hơn);
dịch vụ embedding và reranker riêng có autoscale; LLM qua gateway có fallback model; cache câu hỏi lặp (khoá theo quyền);
trace mọi request.

**Chất lượng**: tập đánh giá cố định, đo recall@k và faithfulness trước mỗi lần đổi model, chunk, prompt. Ứng viên tốt chỉ ra
điểm nghẽn thật: embed lần đầu 10 triệu chunk (ở tốc độ 27 tới 60 đoạn/giây đo trên laptop của track là 2 tới 4 ngày; cần GPU server và batch lớn),
và LLM chiếm phần lớn p95.

## Thiết kế hệ thống: trợ lý pháp luật cho người dân, văn bản luật thay đổi hằng tuần. Bạn xử lý hiệu lực văn bản thế nào?

Bài toán đặc thù của luật: câu trả lời đúng **tại một thời điểm**. Nghị định 46/2016 về xử phạt giao thông đã bị thay bằng
100/2019, rồi 168/2024; trả lời theo văn bản đã hết hiệu lực là sai dù trích dẫn chính xác.

- **Metadata bắt buộc** cho mỗi văn bản và chunk: ngày ban hành, ngày hiệu lực, ngày hết hiệu lực, trạng thái, quan hệ "sửa
  đổi / thay thế / hướng dẫn" tới văn bản khác.
- Retrieval mặc định **lọc văn bản còn hiệu lực** tại ngày hỏi; cho phép hỏi "theo quy định năm 2020" bằng cách đổi ngày lọc
  (query rewriting trích ngày từ câu hỏi).
- Khoản "được sửa đổi bởi" cần đồ thị quan hệ giữa văn bản (đây là chỗ GraphRAG hoặc truy vấn đồ thị có ích), để khi retrieve
  một điều đã bị sửa thì kéo theo điều sửa nó.
- Cập nhật hằng tuần: pipeline index tăng dần, đổi trạng thái hiệu lực không cần embed lại; versioning index để rollback.
- Câu trả lời ghi rõ "theo văn bản X, có hiệu lực từ ...", và từ chối hoặc khuyên hỏi luật sư với câu hỏi về vụ việc cụ thể.
- Đánh giá: tập câu hỏi có đáp án phụ thuộc thời điểm, kiểm hệ không trích văn bản hết hiệu lực.

## Thiết kế hệ thống: chatbot hỗ trợ khách hàng trên tài liệu sản phẩm, nhiều lượt hội thoại, chi phí phải thấp. Bạn thiết kế thế nào?

- **Query rewriting** theo lịch sử hội thoại: "thế còn gói cao cấp?" phải thành câu hỏi độc lập trước khi retrieve. Dùng model
  nhỏ, rẻ cho bước này.
- **Router**: câu chào hỏi, câu ngoài phạm vi, câu cần dữ liệu tài khoản (gọi API, không phải RAG), câu hỏi tài liệu. Không gọi
  retrieval và LLM lớn cho mọi tin nhắn.
- **Cache** hai tầng: cache câu trả lời theo câu hỏi đã chuẩn hoá (FAQ lặp rất nhiều), và prompt caching cho system prompt dài.
- Prompt gọn: 3 tới 5 chunk sau rerank thay vì 20; model nhỏ cho câu dễ, model lớn khi router hoặc độ tin cậy thấp.
- **Từ chối và chuyển người**: dưới ngưỡng retrieval hoặc khi khách bực, chuyển nhân viên kèm tóm tắt hội thoại.
- **Đo**: tỉ lệ giải quyết không cần người, thumbs up/down, faithfulness trên mẫu, chi phí mỗi hội thoại; phản hồi xấu được đưa
  vào tập đánh giá.
- Tài liệu sản phẩm đổi theo phiên bản: metadata phiên bản, lọc theo sản phẩm khách đang dùng.

## Roadmap nhắc "OpenAI Assistant API" như một cách làm RAG. Hiện nay bạn dùng gì thay thế, và khi nào chọn RAG managed thay vì tự dựng?

Assistants API (2023) cho upload file, OpenAI tự chunk, embed, lưu vector store và retrieval qua tool `file_search`. OpenAI đã
thay nó bằng **Responses API** và Conversations API (2025), với tool `file_search` trên vector store; Assistants API đã ngừng
ngày 26/8/2026 theo trang deprecations của OpenAI. Tương đương ở nhà khác: Gemini File Search, Vertex AI RAG Engine, Bedrock Knowledge Bases, Azure AI Search; Anthropic cho
gửi tài liệu kèm citations hoặc search result blocks do bạn tự retrieve.

Chọn managed khi: cần ra sản phẩm nhanh, tài liệu được phép lên cloud, chất lượng mặc định đạt trên tập đánh giá của bạn. Tự
dựng khi: cần chunking theo cấu trúc (Điều/Khoản/Điểm), tokenizer tiếng Việt, hybrid và rerank tuỳ chỉnh, dữ liệu không được
rời hạ tầng, hoặc chi phí lưu trữ theo dung lượng quá cao ở quy mô lớn. Dù chọn gì, đánh giá cả hai bằng **cùng một** tập câu
hỏi và cùng thước đo.
