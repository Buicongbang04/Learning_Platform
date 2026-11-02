# AI Engineer track: 21 module còn lại + capstone — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện track `ai-engineer`: soạn 21 module còn lại (00, 02–12, 14–22) cùng chuẩn với hai module mẫu 01 và 13, và capstone "Trợ lý pháp luật tiếng Việt" gồm 9 milestone.

**Architecture:** Không đổi app hay testkit. **Task 0** thêm một lần mọi dependency (`pyproject.toml` gốc cho thư viện chạy CPU; `setup/gpu/pyproject.toml` cho thư viện chỉ chạy GPU) và mọi bộ dữ liệu (registry `data/download_dataset.py`) cho cả giai đoạn. Sau đó mỗi module là một task độc lập (thư mục riêng), chạy **song song 3–4 module**, mỗi module trong worktree + nhánh riêng tách từ `ai-engineer`, merge về từng module một. Module task không sửa tệp dùng chung; thiếu gì thì báo controller (thêm qua một commit nhỏ trên `ai-engineer` rồi module rebase). Task cuối là capstone.

**Tech Stack:** như giai đoạn 1–2 (`llmkit`, `testkit`, `setup/gpu`), cộng thư viện theo từng module ở bảng dưới.

**Spec:** `docs/superpowers/specs/2026-10-29-ai-engineer-track-design.md`. Plan giai đoạn 1–2: `docs/superpowers/plans/2026-10-29-ai-engineer-phase1-2.md`. Người học yêu cầu (2026-10-30) làm hết track không dừng chờ duyệt mẫu.

**Mẫu chuẩn (gold standard):** `tracks/ai-engineer/modules/01-nn-from-scratch/` (phần A) và `tracks/ai-engineer/modules/13-rag/` (phần B). Mọi module mới đọc module mẫu cùng phần trước khi viết và đạt cùng chuẩn: độ sâu, văn phong, đề bài, `SOLUTION.md`, quiz, cách test.

## Global Constraints

- Đúng `CONTENT_SPEC.md` (cấu trúc, frontmatter, 4 heading đề bài, notebook không output, `quiz.yaml` + `quiz-answers.yaml` cho mọi bài notebook, quy tắc độ dài đáp án, LaTeX `$$...$$`).
- Mỗi module: `README.md` 5–8 phần `## ` (phần cuối tài liệu tham khảo; link phải tồn tại — kiểm bằng `curl -sIL` khi có mạng), ≥2 mermaid hợp lệ, mọi khối ` ```python ` chạy được; `interview.md` ≥12 câu, ≥2 câu case/system design; khoảng 7 bài (3 Basic, 2–3 Intermediate, 2 Advanced; module 00 khoảng 4–5 bài nhẹ, module 22 khoảng 5 bài). Ít nhất 2 bài notebook mỗi module (trừ 00, 21).
- Tiếng Việt, giữ thuật ngữ tiếng Anh; chuẩn "AI Engineer lão luyện": khi nào dùng, đánh đổi, lỗi hay gặp, con số đo thật. Phần A: tự cài đặt cốt lõi trước rồi mới dùng thư viện.
- **Không lộ lời giải**: README lý thuyết và starter không chứa code giải bài tập của chính module (bài học từ module 01).
- Dòng đầu `## Đề bài`: `**Phần cứng:** <CPU | GPU 4GB | GPU 12GB (PC)> · ~<N> phút`. Basic/Intermediate (kể cả notebook lời giải và cell `explore`) chạy hết trên laptop: CPU / GPU 4GB, LLM tối đa `qwen2.5:3b`, embedding `bge-m3`. Việc cần 12GB chỉ ở Advanced hoặc cell mở rộng không chấm, luôn có đường lui nhỏ hơn cho laptop.
- Test: offline, không GPU (`CUDA_VISIBLE_DEVICES=""` vẫn chạy), không LLM thật (`llmkit.FakeLLM`), mỗi bài < 30 giây, không cần bộ dữ liệu đầy đủ (`ex.dataset` tự skip). Starter: FAIL/SKIP, không ERROR. `SOLUTION=1`: Basic/Intermediate PASS; Advanced chỉ `SOLUTION.md` (hướng làm + rubric có điểm) và tự SKIP, nhưng có ít nhất một hàm được test trên fixture; builder kiểm Advanced bằng bản tham chiếu ngoài repo (workspace), không commit.
- Mọi con số trong lý thuyết, quiz `data`, ngưỡng test phải lấy từ lần chạy thật với seed ghim. numpy trên laptop: `os.environ.setdefault("OMP_NUM_THREADS", "4")` trước khi import numpy/torch trong notebook.
- Dữ liệu thật; mỗi bộ mới vào registry (nguồn, giấy phép) + bảng `data/README.md`; ưu tiên bộ tiếng Việt khi hợp lý; tải thử thật trước khi dùng; không commit dữ liệu tải về hay mẫu trích từ bộ giấy phép chưa rõ. Model mở tải từ HF/Ollama, ghi kích thước và VRAM.
- Dependency: phát hành ≥ 2 tuần trước ngày làm; thư viện chạy CPU vào `pyproject.toml` gốc (torch giữ bản CPU), thư viện chỉ chạy GPU (bitsandbytes, vLLM, flash-attn…) vào `setup/gpu/pyproject.toml`. Sau mỗi thay đổi dependency: `SOLUTION=1 uv run pytest tracks -q` không giảm số pass.
- Cần thứ chỉ người học cấp (truy cập PC, API key, đăng ký dữ liệu như MC-OCR): báo controller (status NEEDS_CONTEXT) kèm hướng dẫn từng bước cho người học; trong lúc chờ dùng phiên bản thu nhỏ trên laptop, quiz của bài đó chỉ câu `knowledge`.
- Không sửa `testkit.py`, `llmkit.py` (trừ sửa lỗi có test), app, track DE/DS, module 01/13 (trừ link chéo). Commit tiếng Việt, không Co-Authored-By, stage theo đường dẫn.

## Review Focus

1. Tên tệp/cột trong registry khác thực tế → cell `explore` lỗi dù test xanh. Mỗi module chạy trọn notebook lời giải bằng `uv run jupyter nbconvert --to notebook --execute --stdout <nb> > /dev/null`.
2. Thư viện nặng (transformers, ultralytics, gymnasium, diffusers, langchain…) import ở top-level test làm test chậm/lỗi offline (tải model). Test chỉ dùng model tí hon tự khởi tạo hoặc fixture; mọi tải model nằm trong cell `explore`.
3. Con số trong lý thuyết lệch với output thật / quiz. Đối chiếu mọi con số với lần chạy thật.
4. Hai module nói khác nhau cùng khái niệm (tokenizer, perplexity, RAG metrics, LoRA rank/alpha). Dùng định nghĩa của module đi trước và trỏ link.
5. Bài cần 12GB thiếu đường lui laptop → người học không có PC bị kẹt. Mỗi bài `GPU 12GB (PC)` ghi rõ cấu hình nhỏ cho laptop.

---

### Task 0: Dependency và bộ dữ liệu dùng chung cho cả giai đoạn

**Files:** `pyproject.toml`, `uv.lock`, `setup/gpu/pyproject.toml`, `setup/gpu/uv.lock`, `data/download_dataset.py` (chỉ thêm vào `DATASETS`, thêm loại nguồn nếu cần kèm test), `data/README.md`, `tests/test_download_dataset.py`.

**Interfaces (Produces):** tên bộ dữ liệu trong `DATASETS` mà Task 1–22 dùng qua `ex.dataset("<tên>")`, và dependency import được. Ghi bảng "bộ dữ liệu ↔ module" và "thư viện ↔ module" vào `data/README.md` và vào báo cáo để controller đưa cho từng module task.

- [ ] **Step 1:** Với mỗi dòng của bảng module (cột dữ liệu), chọn bộ thật cụ thể, kiểm giấy phép, **tải thử thật** vào `data/raw/<tên>/`, đếm dòng/ảnh, ghi số. Bộ cần đăng ký/token (MC-OCR, gated HF) → ghi lại, báo controller, không tự thay. Bộ có sẵn trong thư viện (torchvision, gymnasium, sklearn) không cần registry nhưng ghi vào bảng. Model lớn không tải ở bước này.
- [ ] **Step 2:** Thêm dependency chạy CPU vào root (gợi ý: gymnasium[classic-control,box2d], ale-py, opencv-python-headless, ultralytics, peft, trl, datasets, accelerate, diffusers, tiktoken, tokenizers, langchain-core, langchain-ollama, langgraph, faiss-cpu, chromadb, qdrant-client, lancedb, mcp, faster-whisper, pennylane, opentelemetry-sdk, llama-cpp-python hoặc gguf, imageio[ffmpeg]) — giữ torch +cpu từ index pytorch-cpu, phiên bản ≥ 2 tuần tuổi; thư viện chỉ GPU (bitsandbytes, vLLM nếu cài được trên driver 550) vào `setup/gpu`. Gói nào không cài được thì ghi lại và chọn thay thế.
- [ ] **Step 3:** `uv run python -c "import …"` cho mọi gói mới; `uv run python -c "import torch; print(torch.__version__)"` có `+cpu`; `uv run pytest tests -q` PASS; `SOLUTION=1 uv run pytest tracks -q` không giảm (DE+DS 1662 pass + AI Engineer hiện có).
- [ ] **Step 4:** Commit `"data: dependency và bộ dữ liệu thật cho giai đoạn 3 track AI Engineer"`.

### Task 1–21: Mỗi module một task

**Files (module `<id>`):** `tracks/ai-engineer/modules/<id>/README.md`, `interview.md`, `exercises/{basic,intermediate,advanced}/<NN-slug>/{README.md,starter/*,tests/*,quiz.yaml}`, `solutions/...` (+ `SOLUTION.md`, `quiz-answers.yaml`); có thể sửa `pyproject.toml`, `uv.lock`, `setup/gpu/pyproject.toml`, `setup/gpu/uv.lock`, `data/download_dataset.py` (chỉ thêm vào `DATASETS`), `data/README.md`, `tests/test_download_dataset.py` (nếu thêm loại nguồn).

**Quy trình mỗi task:**
- [ ] **Step 1:** Đọc module mẫu cùng phần, `CONTENT_SPEC.md`, `track.json` (summary/topics của module), README track, module đi trước liên quan. Thêm dependency/bộ dữ liệu cần, tải thử thật.
- [ ] **Step 2:** Viết `README.md` + `interview.md`; chạy mọi khối python.
- [ ] **Step 3:** Viết bài tập: README + starter + test → starter FAIL/SKIP không ERROR.
- [ ] **Step 4:** Lời giải + `SOLUTION.md` + quiz → `SOLUTION=1` PASS; nbconvert mọi notebook lời giải; `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` PASS; Advanced kiểm bằng bản tham chiếu ngoài repo.
- [ ] **Step 5:** `uv run pytest tracks/ai-engineer/modules/<id> -q` (FAIL/SKIP only), `SOLUTION=1 …` PASS, `cd app && pnpm build` OK. Commit `"AI Engineer module <NN>: <tên ngắn>"`.

**Nội dung bắt buộc theo module** (topic chi tiết theo `track.json`; bài portfolio theo spec §5; dữ liệu là gợi ý, builder kiểm tải được và giấy phép, được thay bộ tương đương có ruling):

| Task | Module | Bắt buộc có | Dữ liệu / model gợi ý | Phần cứng |
| --- | --- | --- | --- | --- |
| 1 | `00-introduction` | AI vs AGI, AI Engineer vs ML Engineer, vai trò, inference vs training, bức tranh model/sản phẩm; bài nhẹ: ước lượng chi phí/độ trễ inference, đọc model card, đếm token | model card HF, giá API công bố | CPU |
| 2 | `02-pytorch-deep-dive` | autograd sâu (custom Function), nn.Module, DataLoader hiệu năng, mixed precision, gradient accumulation/checkpointing, normalization & residual, profiling bộ nhớ, debug train hỏng | CIFAR-10 | GPU 4GB |
| 3 | `03-computer-vision` | tự viết conv2d numpy → LeNet/ResNet → ViT; transfer learning; detection (YOLO/ultralytics) + segmentation; **Advanced portfolio: detector + app webcam** | CIFAR-10, Oxford-IIIT Pet, Penn-Fudan | GPU 4GB |
| 4 | `04-nlp-sequence-models` | tự viết BPE tokenizer, word2vec, RNN/LSTM, seq2seq + attention (Bahdanau/Luong) | UIT-VSFC (sentiment tiếng Việt), IWSLT'15 en-vi, Wikipedia tiếng Việt | CPU / GPU 4GB |
| 5 | `05-transformers-llm-architecture` | tự dựng GPT mini (attention, MLP, LayerNorm, causal mask), BERT vs GPT, RoPE, GQA, KV cache, MoE, Mamba/SSM, scaling laws; **portfolio: GPT mini tiếng Việt từ số 0** | Wikipedia tiếng Việt (HF `wikimedia/wikipedia` 20231101.vi) | GPU 4GB (bản nhỏ) / 12GB (PC) |
| 6 | `06-generative-models` | autoencoder, VAE (ELBO tự viết), GAN (DCGAN, mode collapse), diffusion (DDPM tự viết); **portfolio: diffusion sinh ảnh theo class** | MNIST, FashionMNIST, CIFAR-10 | GPU 4GB / 12GB |
| 7 | `07-reinforcement-learning` | MDP, value/policy iteration, Q-learning, DQN (replay, target net), REINFORCE, PPO, Gymnasium, giới thiệu RLHF; **portfolio: agent chơi game + video** | Gymnasium (FrozenLake, CartPole, LunarLander), ALE Atari | CPU / GPU |
| 8 | `08-interpretability` | probing, attention analysis, logit lens, activation patching, sparse autoencoder | GPT mini của module 05 hoặc model nhỏ mở (Pythia-70m/GPT-2 small) | GPU 4GB |
| 9 | `09-llms-and-open-models` | pre-trained models (lợi ích, giới hạn, context, cut-off), model đóng/mở, HF Hub/Tasks/Inference/Transformers.js, Ollama models/SDK, sampling (temperature, top-p, top-k) tự cài | Qwen2.5 0.5B/3B, HF Hub | CPU / GPU 4GB |
| 10 | `10-quantization` | int8/int4/fp8 tự cài (absmax, zero-point, per-channel/group), PTQ vs QAT, GPTQ, AWQ, GGUF/llama.cpp, bitsandbytes; đo accuracy/tốc độ/VRAM | model của module 01/05, Qwen2.5-0.5B, perplexity trên Wikipedia vi | CPU / GPU |
| 11 | `11-llm-apis-prompting` | Chat API, token counting & quản lý, pricing, prompt engineering, structured output (JSON schema), function calling, playground; đánh giá prompt có số đo | UIT-VSFC qua prompting `qwen2.5:3b` | CPU (Ollama) |
| 12 | `12-embeddings-vector-db` | embeddings (OpenAI-style API + sentence-transformers + HF), use cases (search, classification, recommendation, anomaly), vector DB (FAISS, Chroma, Qdrant local, LanceDB, pgvector qua Docker cổng `setup/.env`), tự viết ANN (IVF/HNSW đơn giản), indexing | Zalo Legal, UIT-VSFC | CPU |
| 13 | `14-fine-tuning-llm` | SFT, LoRA tự cài trên nn.Linear, QLoRA (PEFT/bitsandbytes), DPO, chuẩn bị dữ liệu, khi nào fine-tune | bộ instruction tiếng Việt giấy phép rõ; Qwen2.5-0.5B (laptop) / 7B QLoRA (PC) | GPU 4GB / 12GB |
| 14 | `15-reasoning-models` | CoT, self-consistency, test-time compute, reasoning models, GRPO (tự viết advantage nhóm), distillation, synthetic data; **portfolio: reasoning model mini có số trước/sau** | GSM8K | GPU 4GB (bản nhỏ) / 12GB |
| 15 | `16-ai-agents` | ReAct tự viết không framework, tool use/function calling, context engineering, MCP server/client (SDK `mcp`), A2A, memory dài hạn, computer-use; **Advanced: coding/research agent có bộ task kiểm bằng test pass/fail** | task tự tạo + repo nhỏ | CPU (Ollama) |
| 16 | `17-langchain-langgraph` | LCEL, LangGraph state/graph, checkpoint/memory, multi-agent, human-in-the-loop; test bằng LLM giả của LangChain | Zalo Legal | CPU (Ollama) |
| 17 | `18-multimodal` | vision LLM, Whisper (STT), TTS, sinh ảnh (diffusers), video understanding, LangChain/LlamaIndex multimodal; **Advanced portfolio: trợ lý tài chính (hóa đơn MC-OCR + giọng nói + báo cáo tháng)** | MC-OCR (cần đăng ký), FLEURS vi / Common Voice vi | CPU / GPU 4GB |
| 18 | `19-ai-safety-security` | prompt injection (trực tiếp/gián tiếp), bảo mật & privacy (PII), bias & fairness, moderation, end-user IDs, adversarial testing/red-teaming, ràng buộc input/output, guardrails | bộ prompt-injection công khai (vd. deepset/prompt-injections) | CPU (Ollama) |
| 19 | `20-evaluation-production` | evals (offline/online), LLM-as-judge + hiệu chuẩn với nhãn người, observability (tracing OpenTelemetry/Langfuse), serving (vLLM/llama.cpp server), speculative decoding, prompt caching, chi phí/độ trễ (p50/p95), AI code editors | Zalo Legal, UIT-VSFC | CPU / GPU 4GB |
| 20 | `21-ai-system-design` | khung đóng bài toán, chọn prompt/RAG/fine-tune/agent, ước lượng capacity/chi phí, ≥6 case phỏng vấn; bài: máy tính chi phí/độ trễ, design doc chấm rubric | — | CPU |
| 21 | `22-quantum-ml` | qubit, gate, mạch, đo; variational circuit, quantum kernel trên simulator (PennyLane); tự viết simulator statevector nhỏ bằng numpy; đánh giá thẳng thắn hiện trạng; ghi "cập nhật dần" | Iris / moons (sklearn) | CPU |

Chạy song song theo đợt 3–4 module (ghép module nặng CPU/GPU với module nhẹ), mỗi module worktree riêng. Trước Task 5 (module 05), báo người học setup truy cập PC (SSH hoặc `OLLAMA_HOST`) nếu muốn số liệu 12GB được kiểm thật; không có thì làm bản thu nhỏ.

### Task 22: Capstone "Trợ lý pháp luật tiếng Việt"

**Files:** `tracks/ai-engineer/capstone/milestones/m01-…m09-….md`, `tracks/ai-engineer/capstone/project/` (khung code + test), sửa `tracks/ai-engineer/track.json` (thêm khoá `capstone` với `readme` và 9 milestone `after` theo `capstone/README.md`), cập nhật `capstone/README.md` nếu cần.

**Interfaces:** cấu trúc capstone giống `tracks/data-science/capstone/` (milestone doc: mục tiêu, việc phải làm, tiêu chí đạt có số, gợi ý). `project/` có package Python nhỏ (`legal_assistant/`) với các hàm khung theo milestone và test fixture tự viết (không trích Zalo Legal), dùng `llmkit`; tập đánh giá ghim như module 13 (300 `query-id` đầu của `qrels/test.jsonl`).

- [ ] **Step 1:** Viết 9 milestone theo spec §8, mỗi milestone chỉ cần kiến thức các module trước `after`.
- [ ] **Step 2:** Khung `project/` + test; starter FAIL/SKIP, bản tham chiếu ngoài repo đạt tiêu chí có số của m01–m03 trên laptop (BM25 / hybrid / RAG có trích dẫn) và ghi số thật vào milestone.
- [ ] **Step 3:** Thêm khoá `capstone` vào `track.json`; `cd app && pnpm typecheck && pnpm build`.
- [ ] **Step 4:** Kiểm tổng: `uv run pytest tracks/ai-engineer -q` chỉ FAIL/SKIP; `SOLUTION=1 uv run pytest tracks -q` PASS (không giảm so với baseline DE+DS 1662 pass); `uv run pytest tests -q` PASS. Commit `"AI Engineer: capstone trợ lý pháp luật tiếng Việt"`.
