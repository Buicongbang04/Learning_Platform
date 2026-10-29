# Thiết kế: track AI Engineer

Ngày: 2026-10-29. Nguồn: [roadmap.sh/ai-engineer](https://roadmap.sh/ai-engineer) (bản PDF ở
`roadmap/ai-engineer.pdf`), **mở rộng đáng kể** theo yêu cầu người học (xem mục 1).

## 1. Mục đích và lý do

Người học muốn trở thành **AI Engineer lão luyện**, hiểu AI từ bên trong chứ không chỉ gọi API:
hiểu layer, neuron, cách từng kiến trúc và mô hình hoạt động; và có **sản phẩm do chính mình làm**
(mô hình tự train, dự án ứng dụng dùng được trong đời sống) về NLP, computer vision, game
(reinforcement learning), agent, LangChain/LangGraph. Yêu cầu nguyên văn: "tất cả mọi thứ để trở
thành một AI Engineer lão luyện"; phần mới của ngành thì cứ thêm vào.

Roadmap.sh gần như chỉ phủ nửa "ứng dụng LLM" (gọi model qua API, RAG, agent) và lấy OpenAI làm
trung tâm, một phần đã cũ (Assistants API, DALL-E). Track này dùng roadmap làm khung cho **phần B**
và thêm **phần A** (tự xây và train model) cùng các chủ đề mới (★).

Người học: đã xong track Data Engineer và track AI & Data Scientist (có module 13 Deep Learning:
MLP, CNN, LSTM, Transformer encoder trên FashionMNIST). Python/pandas/SQL vững. Đọc tiếng Việt, giữ
thuật ngữ tiếng Anh.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Lấp placeholder `tracks/ai-engineer` thành track `active`, đúng `CONTENT_SPEC.md` (kể cả bài
  notebook và trắc nghiệm `quiz.yaml`).
- Phủ mọi node và mục con trong PDF roadmap (thay phần đã cũ bằng tương đương hiện hành, ghi chú
  rõ trong README module), cộng phần mở rộng ở mục 4.
- Mỗi module phần A có ít nhất một bài Advanced là **dự án portfolio** chạy thật trên dữ liệu thật.
- Một capstone lớn xuyên phần B: Trợ lý pháp luật tiếng Việt (mục 8).

**Ngoài phạm vi**
- Dạy lại nội dung module 13 track DS và toán ML (module 01 DS): trỏ sang, chỉ nhắc ngắn khi cần.
- MLOps hạ tầng sâu (Kubernetes, CI/CD cho model, feature store): để cho track `mlops`/`devops`.
  Module 20 chỉ phủ phần đặc thù LLM (serving, eval, observability, chi phí).
- Train model lớn (pretrain LLM > ~200M tham số): không, phần cứng không cho phép.

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Nội dung chỉ dừng ở định nghĩa, không có quyết định thực tế (khi nào dùng, đánh đổi, lỗi hay gặp).
- Bài chỉ "gọi thư viện" mà không hiểu bên trong ở phần A: các kiến trúc cốt lõi (backprop,
  attention, GPT mini, DQN…) phải tự cài đặt trước rồi mới dùng thư viện.
- Bắt buộc trả phí: mọi bài phải làm được miễn phí trên máy người học.
- Test phụ thuộc GPU, mạng, LLM thật hay bộ dữ liệu đầy đủ.
- Phá vỡ track DE, DS hoặc app hiện có (kể cả môi trường CPU hiện tại của laptop).

## 3. Ràng buộc

**Phần cứng**
- Laptop: RTX 3050 Laptop 4GB, 16 core, 31GB RAM, đã cài Ollama. Đây là nơi chạy app và test.
- PC: RTX 3060 **12GB**, 128GB RAM. Dùng cho train nặng: GPT mini, diffusion, RL dài, fine-tune
  QLoRA model 7–8B, GRPO, chạy LLM local 8–14B.
- Mỗi bài ghi rõ yêu cầu phần cứng trong README: `CPU`, `GPU 4GB` hoặc `GPU 12GB (PC)`, kèm thời
  gian chạy ước tính. Bài `GPU 12GB` phải có đường lui nhỏ hơn (model/dữ liệu nhỏ) để chạy trên
  laptop, kết quả kém hơn cũng được.

**Môi trường Python**
- `pyproject.toml` hiện ghim `torch` bản CPU. Không phá điều đó. Cài đặt GPU (torch CUDA,
  bitsandbytes, vLLM, các thư viện fine-tune) đi qua một cấu hình riêng có hướng dẫn trong README
  track (ví dụ dependency group/extra hoặc môi trường uv riêng). Cách cụ thể: builder quyết, miễn
  `uv run pytest` trên laptop vẫn chạy như cũ.
- Dependency phần B dùng chung (client LLM, vector DB nhúng, LangChain/LangGraph…) thêm vào
  `pyproject.toml` như thường; ưu tiên thư viện chạy được CPU.

**LLM: local-first** (quyết định của Claude, người học không phản đối)
- Mặc định gọi LLM local qua Ollama. API trả phí (Claude, OpenAI, Gemini) là tùy chọn.
- Code bài tập gọi LLM qua một lớp mỏng dùng chung để đổi provider bằng cấu hình (biến môi trường),
  kể cả trỏ Ollama sang PC qua LAN (`OLLAMA_HOST`). Thiết kế lớp này: builder quyết.
- Test không gọi LLM thật: dùng LLM giả lập (trả lời xác định theo kịch bản) để kiểm logic agent,
  RAG, parse output. Chất lượng thật của LLM được đo trong notebook / bài Advanced.

**Nội dung**
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo (link
  trong PDF roadmap + paper/tài liệu gốc); `interview.md` ≥12 câu, có câu system design / case.
- Khoảng 7 bài/module (3 Basic, 2–3 Intermediate, 2 Advanced). Starter fail hoặc skip, không lỗi cú
  pháp; `SOLUTION=1` pass với Basic và Intermediate; Advanced có `SOLUTION.md` (hướng làm + rubric).
- Lĩnh vực đổi rất nhanh: khi soạn, builder kiểm phiên bản thư viện và model hiện hành (tháng
  10/2026), ghi ngày kiểm trong README module. Module 22 Quantum ghi rõ "cập nhật dần".

## 4. Danh sách module (đã chốt)

★ = ngoài roadmap.sh.

**Phần A: hiểu và tự xây mô hình**

| # | id | Nội dung |
| --- | --- | --- |
| 00 | `00-introduction` | AI Engineer là gì, vs ML Engineer, AI vs AGI, vai trò, tác động lên sản phẩm, bức tranh ngành |
| 01 | `01-nn-from-scratch` ★ | Neuron, layer, activation, loss, backprop tự viết bằng numpy, optimizer, init |
| 02 | `02-pytorch-deep-dive` ★ | Train trên GPU, mixed precision, normalization, residual, debug khi train hỏng, profiling bộ nhớ |
| 03 | `03-computer-vision` ★ | LeNet → ResNet → ViT, transfer learning, detection (YOLO), segmentation |
| 04 | `04-nlp-sequence-models` ★ | Tokenization (BPE), word2vec, RNN/LSTM, seq2seq, attention |
| 05 | `05-transformers-llm-architecture` ★ | Tự dựng GPT mini; BERT vs GPT; kiến trúc LLM hiện đại: RoPE, GQA, KV cache, MoE, Mamba/SSM; scaling laws |
| 06 | `06-generative-models` ★ | Autoencoder, VAE, GAN, diffusion |
| 07 | `07-reinforcement-learning` ★ | MDP, Q-learning, DQN, policy gradient, PPO, Gymnasium, giới thiệu RLHF |
| 08 | `08-interpretability` ★ | Probing, attention analysis, logit lens, activation patching, sparse autoencoder |

**Phần B: ứng dụng LLM (khung roadmap.sh)**

| # | id | Nội dung |
| --- | --- | --- |
| 09 | `09-llms-and-open-models` | Pre-trained models (lợi ích, giới hạn, context length, cut-off), model đóng/mở phổ biến, Hugging Face (Hub, Tasks, Inference, Transformers.js), Ollama, inference & sampling |
| 10 | `10-quantization` ★ | int8/int4/fp8, PTQ vs QAT, GPTQ, AWQ, GGUF/llama.cpp, bitsandbytes; đo đánh đổi độ chính xác / tốc độ / VRAM |
| 11 | `11-llm-apis-prompting` | Chat Completions-style API, token, đếm và quản lý token, pricing, prompt engineering, structured output, function calling, playground |
| 12 | `12-embeddings-vector-db` | Embeddings, use cases (semantic search, classification, recommendation, anomaly), sentence-transformers, vector DB (Chroma, FAISS, Qdrant, pgvector…), indexing, similarity search |
| 13 | `13-rag` | RAG use cases, RAG vs fine-tuning, chunking, retrieval, hybrid search, reranking, generation có trích dẫn, đánh giá RAG, SDK trực tiếp vs LangChain vs LlamaIndex |
| 14 | `14-fine-tuning-llm` | SFT, LoRA/QLoRA, DPO, chuẩn bị dữ liệu, khi nào nên fine-tune |
| 15 | `15-reasoning-models` ★ | Chain-of-thought, test-time compute, reasoning models, RL with verifiable rewards (GRPO), distillation, synthetic data |
| 16 | `16-ai-agents` | Agent use cases, ReAct, tool use, agent tự viết không framework, context engineering ★, MCP/A2A ★, memory dài hạn ★, computer-use ★, coding agent ★ |
| 17 | `17-langchain-langgraph` ★ | LangChain (LCEL), LangGraph: state, graph, memory/checkpoint, multi-agent, human-in-the-loop |
| 18 | `18-multimodal` | Vision (image understanding), speech-to-text (Whisper), text-to-speech, sinh ảnh, video understanding, LangChain/LlamaIndex cho multimodal |
| 19 | `19-ai-safety-security` | Prompt injection, bảo mật & privacy, bias & fairness, moderation, end-user IDs, adversarial testing / red-teaming, ràng buộc input/output, guardrails |
| 20 | `20-evaluation-production` ★ | Evals, LLM-as-judge, observability, serving (vLLM), speculative decoding, prompt caching, chi phí/độ trễ; development tools (AI code editors, code completion) |
| 21 | `21-ai-system-design` ★ | Đóng khung bài toán AI, chọn kiến trúc (prompt / RAG / fine-tune / agent), case phỏng vấn |
| 22 | `22-quantum-ml` ★ | Mở rộng, cập nhật dần: qubit, mạch lượng tử, variational circuit, quantum kernel trên simulator (PennyLane hoặc Qiskit), đánh giá thẳng thắn hiện trạng |

Topic con chi tiết, tên và nội dung từng bài: builder quyết, miễn phủ đủ các mục trên và mục con
trong PDF.

## 5. Dự án portfolio trong bài Advanced (đã chốt)

Bắt buộc có (đặt ở module tương ứng, builder có thể thêm):
- GPT mini tiếng Việt tự train từ số 0 (05), sau đó quantize và so sánh (10).
- Detector hoặc segmentation fine-tune trên bộ ảnh thật, kèm app nhỏ chạy webcam (03).
- Agent chơi game bằng DQN/PPO (Atari hoặc tương tự), quay video kết quả (07).
- Diffusion nhỏ sinh ảnh theo class (06).
- Reasoning model mini: GRPO cải thiện model nhỏ ở bài toán có đáp án kiểm được, có số liệu trước/sau (15).
- **Trợ lý tài chính cá nhân đa phương thức** (18): chụp hóa đơn → đọc bằng vision (bộ hóa đơn
  Việt Nam thật, ví dụ MC-OCR), phân loại chi tiêu, hỏi đáp bằng giọng (Whisper + TTS), agent lập
  báo cáo tháng.
- **Coding/research agent** (16 hoặc 17): đọc tài liệu và repo, trả lời hoặc sửa code, có bộ task
  kiểm chứng được (test pass/fail).

## 6. Notebook, chấm điểm, test

Như track DS: `testkit.Exercise.notebook()` đã có; bài thực nghiệm dùng notebook, bài thuần logic
dùng `.py`; bài notebook có `quiz.yaml`. Test dùng model và dữ liệu cực nhỏ, chạy CPU, không mạng,
không LLM thật. Kết quả train trên bộ thật (độ chính xác, điểm game, recall RAG) được kiểm trong
notebook hoặc chấm rubric ở Advanced.

**Phân cấp theo phần cứng** (quyết định của Claude): notebook lời giải Basic và Intermediate phải
chạy hết trên laptop (CPU / GPU 4GB, LLM local tối đa cỡ `qwen2.5:3b`, embedding `bge-m3` hoặc
`nomic-embed-text`, đều đã có sẵn trong Ollama trên laptop). Việc chỉ chạy được trên PC 12GB
(`qwen2.5:7b` trở lên, QLoRA 7B, GRPO, diffusion…) chỉ nằm ở bài Advanced, hoặc ở cell "mở rộng"
không chấm trong notebook.

**Module 00 và 22** (quyết định của Claude): không bắt buộc dự án portfolio (yêu cầu ở mục 2 áp
cho 01–08). 00 là module khái niệm, khoảng 4–5 bài nhẹ. 22 bản đầu đủ lý thuyết + interview,
khoảng 5 bài trên simulator, cập nhật dần sau.

## 7. Dữ liệu

Dữ liệu thật càng nhiều càng tốt, ưu tiên bộ tiếng Việt khi hợp lý và bộ có nhãn để chấm được.
Mỗi bộ có script tải trong `data/` (cùng phong cách hiện có), ghi vào `data/raw/<bộ>/`, ghi nguồn
và giấy phép, thêm vào bảng ở `data/README.md`. Builder kiểm còn tải được và giấy phép trước khi
dùng, được thay bằng bộ tương đương. Gợi ý: Wikipedia tiếng Việt (GPT mini), bộ CV chuẩn (CIFAR,
COCO subset, bộ ảnh thật cho detection), Gymnasium/ALE (RL), GSM8K hoặc tương tự (reasoning),
Zalo AI Legal Text Retrieval (RAG/capstone), MC-OCR (hóa đơn).

Model: dùng model mở tải từ Hugging Face / Ollama; ghi rõ kích thước và VRAM cần.

## 8. Capstone: "Trợ lý pháp luật tiếng Việt" (đã chốt)

Hệ thống hỏi đáp pháp luật tiếng Việt: RAG + agent (LangGraph), trả lời kèm trích dẫn điều luật,
chạy local. Dữ liệu chính: Zalo AI Legal Text Retrieval (câu hỏi có nhãn điều luật liên quan) để
chấm retrieval bằng số. Nếu bộ này không tải được hợp lệ, builder chọn bộ hỏi đáp pháp luật tiếng
Việt có nhãn tương đương và ghi lý do.

Milestone gắn module (`after`), code ở `capstone/project/`:
1. Dữ liệu, chuẩn hóa văn bản luật, baseline BM25, đo recall@k (sau 12)
2. Retrieval bằng embedding + vector DB, hybrid, reranking, so baseline (sau 12/13)
3. RAG sinh câu trả lời có trích dẫn, đánh giá độ trung thực (sau 13)
4. Quantize model và chạy local hiệu quả (sau 10)
5. Fine-tune embedding hoặc LLM (QLoRA) trên dữ liệu luật, so trước/sau (sau 14)
6. Agent LangGraph: tách câu hỏi, tra cứu nhiều bước, hỏi lại khi thiếu thông tin (sau 17)
7. Safety: chống prompt injection, từ chối khi không có căn cứ, không bịa điều luật (sau 19)
8. Eval suite, observability, serve và đo chi phí/độ trễ (sau 20)
9. Tài liệu system design của chính hệ thống (sau 21)

Thứ tự và `after` cụ thể: builder quyết sao cho mỗi milestone chỉ cần kiến thức các module trước.

## 9. Cách giao (đã chốt)

1. Hạ tầng: cấu hình môi trường GPU riêng, lớp gọi LLM dùng chung + LLM giả lập cho test,
   script tải dữ liệu cho module mẫu, `track.json` (status `active`, `source` trỏ roadmap),
   `README.md` track với sơ đồ mermaid, capstone README.
2. **Hai module mẫu: `01-nn-from-scratch`** (đại diện phần A) **và `13-rag`** (đại diện phần B:
   lớp LLM, LLM giả lập, Ollama, dữ liệu luật; làm nền cho capstone). Đầy đủ lý thuyết, interview,
   bài tập, lời giải, quiz. Người học duyệt văn phong, độ khó, trải nghiệm.
3. Sau khi duyệt mới soạn hàng loạt các module còn lại và capstone milestones.

**Môi trường lúc soạn (người học đã trả lời)**
- Builder chỉ truy cập được laptop. Hai module mẫu đủ chạy trên laptop. Trước khi soạn các module
  cần kiểm số liệu trên 12GB (05, 06, 07, 10, 14, 15 và milestone capstone tương ứng), builder báo
  người học để setup truy cập PC (SSH hoặc `OLLAMA_HOST`). Chưa có thì kiểm bằng phiên bản thu nhỏ
  trên laptop, còn quiz của bài 12GB chỉ hỏi kiến thức, không hỏi số liệu chưa kiểm.
- Người học sẽ tạo Hugging Face token và đăng ký Zalo AI / MC-OCR. Script tải đọc token từ biến
  môi trường hoặc cache chuẩn, không commit token. Builder đưa hướng dẫn từng bước (việc chỉ người
  học làm được) trước khi cần tới dữ liệu đó; chưa có thì dừng phần đó, không tự thay bộ khác.
- Ollama trên laptop đã có: `qwen2.5:3b`, `qwen2.5:7b`, `bge-m3`, `nomic-embed-text`.
- API trả phí: người học có tài khoản Gemini và OmniRoute (gateway gọi được nhiều API AI). Khi nội
  dung hoặc việc kiểm chứng cần gọi API thật, builder báo người học và đưa hướng dẫn setup từng
  bước (key đặt trong biến môi trường, không commit). Lớp gọi LLM chung nên hỗ trợ Gemini và
  endpoint OpenAI-compatible (OmniRoute) bên cạnh Ollama.

## 10. Để builder quyết

Cấu trúc lớp gọi LLM và LLM giả lập; cách tách môi trường GPU; tên và nội dung bài tập; thư viện
cụ thể mỗi module (miễn phổ biến trong ngành và còn được duy trì); thứ tự soạn sau module mẫu.
