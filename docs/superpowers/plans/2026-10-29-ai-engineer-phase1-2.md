# AI Engineer track: hạ tầng + module mẫu 01 và 13 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bật track `ai-engineer` trong app với hạ tầng LLM local-first, môi trường GPU riêng, dữ liệu thật, và hai module mẫu hoàn chỉnh `01-nn-from-scratch` và `13-rag` để người học duyệt trước khi soạn hàng loạt.

**Architecture:** Một module gốc `llmkit.py` (cạnh `testkit.py`) là lớp gọi LLM dùng chung: provider `ollama` hoặc `openai_compat` (OmniRoute, Gemini qua endpoint OpenAI-compatible), cấu hình bằng biến môi trường / `setup/.env`, gọi HTTP bằng `httpx`, và `FakeLLM` xác định để test không cần LLM thật. Registry `data/download_dataset.py` có thêm nguồn `hf` (Hugging Face Hub). Môi trường GPU là một uv project riêng ở `setup/gpu/`, không đụng `pyproject.toml` gốc (torch CPU). Nội dung theo `CONTENT_SPEC.md`, app không sửa.

**Tech Stack:** Python 3.12, uv, pytest, httpx, numpy, nbformat, huggingface_hub, sentence-transformers (reranker CPU), LangChain hoặc LlamaIndex (một bài Advanced), Ollama (`qwen2.5:3b`, `qwen2.5:7b`, `bge-m3` đã có trên laptop).

**Spec:** `docs/superpowers/specs/2026-10-29-ai-engineer-track-design.md`. Plan này phủ mục 9 bước 1–2; bước 3 (21 module còn lại + capstone milestones) có plan riêng sau khi người học duyệt.

## Global Constraints

- Mọi nội dung đúng `CONTENT_SPEC.md` (cấu trúc, frontmatter, chỉ 4 heading đề bài, notebook không output, `quiz.yaml` + `quiz-answers.yaml` cho mọi bài notebook, quy tắc độ dài đáp án).
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn "AI Engineer lão luyện": có quyết định thực tế, đánh đổi, lỗi hay gặp; phần A tự cài đặt trước khi dùng thư viện.
- Track id `ai-engineer`, tên `AI Engineer`, icon `brain`, `order: 4` (giữ), `source: https://roadmap.sh/ai-engineer`.
- Mỗi module: 5–8 phần `## ` (phần cuối là tài liệu tham khảo), ≥2 sơ đồ mermaid; `interview.md` ≥12 câu có câu system design/case; ~3 Basic, 2–3 Intermediate, 2 Advanced.
- Basic/Intermediate (cả notebook lời giải, kể cả cell `explore`) chạy hết trên laptop: CPU / GPU 4GB, LLM tối đa `qwen2.5:3b`, embedding `bge-m3`. Việc cần PC 12GB chỉ ở Advanced hoặc cell mở rộng không chấm.
- Dòng đầu của `## Đề bài` mỗi bài: `**Phần cứng:** <CPU | GPU 4GB | GPU 12GB (PC)> · ~<N> phút`.
- Test: không mạng, không GPU, không LLM thật (dùng `FakeLLM`), không bộ dữ liệu đầy đủ (phần dữ liệu thật dùng `ex.dataset(...)` tự skip).
- Không commit token/key; key đọc từ biến môi trường hoặc `setup/.env` (đã gitignore). Không commit mẫu trích từ bộ giấy phép chưa rõ (Zalo Legal: fixture test phải do builder tự viết).
- Cần API trả phí, truy cập PC, hay đăng ký tài khoản → dừng, báo người học kèm hướng dẫn từng bước; không tự thay bộ dữ liệu khác.
- Track DE và DS giữ nguyên: `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` cho cùng số pass/skip trước và sau (ghi con số trước Task 1).
- Commit message tiếng Việt, không dòng Co-Authored-By.

## Review Focus

1. Ollama chưa chạy hoặc chưa `pull` model → `llmkit` báo lỗi tiếng Việt có lệnh khắc phục (`ollama serve`, `ollama pull <model>`), không traceback httpx thô. Test ở Task 1.
2. Notebook `import llmkit` ở top-level khi chưa cấu hình gì → import không mở kết nối (lazy), starter vẫn nạp được để test FAIL chứ không ERROR. Test ở Task 1.
3. Văn bản tiếng Việt dạng NFD (dấu tách rời) hoặc lẫn NFC → tokenize/chunk chuẩn hoá NFC, cùng một từ cho cùng token. Test ở Task 10.
4. RAG gặp câu hỏi không có đoạn liên quan (điểm retrieval dưới ngưỡng) hoặc LLM trích nguồn số không tồn tại (`[7]` khi chỉ có 5 nguồn) → từ chối trả lời / bỏ trích dẫn sai, không bịa. Test ở Task 11.
5. Chưa có `HF_TOKEN` khi bộ cần token → `download_dataset.py` thoát mã ≠0 với hướng dẫn tạo token, không traceback. Test ở Task 2.

---

### Task 1: `llmkit.py` — lớp gọi LLM dùng chung + `FakeLLM`

**Files:**
- Create: `llmkit.py`, `tests/test_llmkit.py`
- Modify: `setup/SETUP.md` (mục cấu hình LLM: các biến dưới)
- Consumes: `testkit._load_env_file(path)` (import, không chép) để đọc `setup/.env`

**Interfaces:**
- Produces (module `llmkit`):
  - `Message = dict[str, str]` (`{"role": ..., "content": ...}`).
  - `class LLMClient(Protocol)`: `chat(messages: list[Message], *, model: str | None = None, temperature: float = 0.0, json_schema: dict | None = None) -> str`; `embed(texts: list[str], *, model: str | None = None) -> np.ndarray` (float32, shape `(len(texts), dim)`, chưa chuẩn hoá).
  - `class OllamaClient(LLMClient)`: `POST {OLLAMA_HOST}/api/chat` (`stream: false`, `format` = json_schema khi có, `options.temperature`), `POST {OLLAMA_HOST}/api/embed`.
  - `class OpenAICompatClient(LLMClient)`: `POST {LLM_BASE_URL}/chat/completions` (`response_format` json_schema khi có), `POST {LLM_BASE_URL}/embeddings`, header `Authorization: Bearer {LLM_API_KEY}`. Dùng cho OmniRoute và Gemini (`https://generativelanguage.googleapis.com/v1beta/openai`).
  - `class FakeLLM(LLMClient)`: `FakeLLM(replies: Callable[[list[Message]], str] | list[str] | None = None, dim: int = 64)`. `chat` trả phần tử kế tiếp của list (hết thì `AssertionError`) hoặc kết quả callable; ghi mọi lời gọi vào `self.calls: list[list[Message]]`. `embed` xác định: bag-of-tokens băm (hash ổn định, không dùng `hash()` của Python) vào `dim` chiều, nên văn bản chung từ có cosine cao.
  - `class LLMError(RuntimeError)`: thông điệp tiếng Việt kèm lệnh khắc phục.
  - `get_client() -> LLMClient` (lazy, tạo theo env lần đầu gọi), `use(client) -> ContextManager` (đổi client toàn cục tạm thời), module-level `chat(...)`, `embed(...)` gọi qua `get_client()`.
- Biến môi trường: `LLM_PROVIDER` (`ollama` mặc định | `openai_compat`), `OLLAMA_HOST` (mặc định `http://localhost:11434`), `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (mặc định `qwen2.5:3b`), `EMBED_MODEL` (mặc định `bge-m3`), `LLM_TIMEOUT` (mặc định `120` giây).

- [ ] **Step 1: Ghi con số baseline** — `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q | tail -1`, lưu lại.
- [ ] **Step 2: Test thất bại** (`tests/test_llmkit.py`, HTTP giả bằng `httpx.MockTransport`, không mạng):

```python
def test_import_does_not_connect(monkeypatch): # chặn httpx.Client.send raise; import llmkit; get_client() chưa gọi → không lỗi
def test_ollama_chat_payload_and_reply():      # MockTransport kiểm path /api/chat, model, stream False, temperature 0; trả {"message":{"content":"xin chào"}} → "xin chào"
def test_ollama_json_schema_sent_as_format():
def test_ollama_embed_shape():                 # /api/embed trả {"embeddings":[[...3 số],[...]]} → ndarray float32 shape (2,3)
def test_openai_compat_bearer_and_parse():     # header Authorization "Bearer k", path /chat/completions, parse choices[0].message.content
def test_connection_refused_message():         # transport raise httpx.ConnectError → LLMError, str chứa "ollama serve"
def test_model_not_found_message():            # Ollama 404 {"error":"model \"x\" not found"} → LLMError chứa "ollama pull x"
def test_fake_llm_scripted_and_records_calls():
def test_fake_embed_deterministic_and_similar():  # cùng text → cùng vector giữa 2 lần chạy; cos("luật đất đai","đất đai luật") > cos("luật đất đai","bóng đá")
def test_use_swaps_global_client():
```

Client nhận tham số `transport: httpx.BaseTransport | None = None` để test bơm MockTransport.

- [ ] **Step 3: Chạy để thấy fail** — `uv run pytest tests/test_llmkit.py -q` → FAIL (ModuleNotFoundError).
- [ ] **Step 4: Cài `llmkit.py`**; docstring đầu tệp theo phong cách `testkit.py`: cách cấu hình Ollama local / Ollama trên PC (`OLLAMA_HOST=http://<ip-PC>:11434`) / OmniRoute / Gemini, và cách dùng `FakeLLM` trong test.
- [ ] **Step 5: Chạy** — `uv run pytest tests -q` PASS. Kiểm thật (không phải test): `uv run python -c "import llmkit; print(llmkit.chat([{'role':'user','content':'Trả lời đúng một từ: thủ đô Việt Nam?'}]))"` in ra Hà Nội; `llmkit.embed(['a','b']).shape[1] == 1024` với `bge-m3`.
- [ ] **Step 6: Commit** — `git commit -m "llmkit: lớp gọi LLM dùng chung (Ollama, OpenAI-compatible) và FakeLLM cho test"`

### Task 2: Dữ liệu — nguồn Hugging Face, MNIST, Zalo Legal

**Files:**
- Modify: `data/download_dataset.py` (thêm `source="hf"`, các bộ mới), `data/README.md` (mục "Bộ dữ liệu cho track AI Engineer"), `pyproject.toml` (`huggingface_hub`)
- Test: `tests/test_download_dataset.py` (thêm case)

**Interfaces:**
- `Dataset.source` thêm `"hf"`: `ref = "<owner>/<repo>"` (repo type dataset), `files` = đường dẫn trong repo; tải bằng `huggingface_hub.hf_hub_download(repo_type="dataset", token=os.environ.get("HF_TOKEN"))`, ghi vào `data/raw/<tên>/` giữ tên tệp. Thêm field `needs_token: bool = False`; nếu `True` mà thiếu `HF_TOKEN` → `SystemExit` mã ≠0, stderr chứa `HF_TOKEN` và link `https://huggingface.co/settings/tokens`. Đọc `setup/.env` như các bộ Kaggle.
- Bộ mới:
  - `mnist`: `url`, 4 tệp `train-images-idx3-ubyte.gz`, `train-labels-idx1-ubyte.gz`, `t10k-images-idx3-ubyte.gz`, `t10k-labels-idx1-ubyte.gz` từ mirror `https://ossci-datasets.s3.amazonaws.com/mnist/` (mirror torchvision dùng). License: CC BY-SA 3.0 (Yann LeCun & Corinna Cortes).
  - `zalo-legal`: `hf`, `GreenNode/zalo-ai-legal-text-retrieval-vn` (Ruling: repo `nntoan209/ZaloLegal` đã mất), tệp `corpus.jsonl`, `queries.jsonl`, `qrels/train.jsonl`, `qrels/test.jsonl`. License: dữ liệu cuộc thi Zalo AI Challenge 2021, chỉ dùng học tập/nghiên cứu (ghi rõ đây là bản mirror bên thứ ba). `needs_token` theo thực tế khi tải.
- Kiểm cấu trúc khi tải lần đầu và ghi vào `data/README.md`: `legal_corpus.json` là list `{law_id, articles: [{article_id, title, text}]}`; `train_question_answer.json` có `items: [{question_id, question, relevant_articles: [{law_id, article_id}]}]`. Khác thì sửa mô tả và các bài module 13 theo cấu trúc thật.

- [ ] **Step 1: Test thất bại**

```python
def test_hf_dataset_requires_token_exits_cleanly(monkeypatch, tmp_path, capsys): # Dataset hf needs_token=True, xoá HF_TOKEN → SystemExit code != 0, stderr chứa "HF_TOKEN"
def test_hf_download_calls_hub(monkeypatch, tmp_path):  # monkeypatch hf_hub_download trả tệp tạm → tệp xuất hiện trong out
def test_registry_entries_complete():  # (đã có) phải pass với bộ mới
```

- [ ] **Step 2: Chạy để thấy fail** — `uv run pytest tests/test_download_dataset.py -q`.
- [ ] **Step 3: Cài** (thêm `uv add huggingface_hub`).
- [ ] **Step 4: Chạy test** → PASS.
- [ ] **Step 5: Tải thật** — `uv run python data/download_dataset.py mnist` → 4 tệp, 60000/10000 ảnh 28×28 (đọc header idx). `uv run python data/download_dataset.py zalo-legal` → nếu cần token mà người học chưa có: dừng, báo người học tạo HF token (bước: settings/tokens → Read token → `HF_TOKEN=hf_...` vào `setup/.env`), tiếp tục các task không cần bộ này. Khi tải được: ghi số luật, số điều, số câu hỏi vào `data/README.md`.
- [ ] **Step 6: Commit** — `git commit -m "data: nguồn Hugging Face, bộ MNIST và Zalo Legal cho track AI Engineer"`

### Task 3: Môi trường GPU riêng

**Files:**
- Create: `setup/gpu/pyproject.toml`, `setup/gpu/README.md`, `setup/gpu/check_gpu.py`

**Interfaces:**
- uv project `ai-gpu` (`package = false`, Python 3.12) với torch + torchvision bản CUDA (index PyTorch CUDA mới nhất hỗ trợ RTX 30xx), `transformers`, `accelerate`, `peft`, `trl`, `bitsandbytes`, `datasets`. Kiểm phiên bản mới nhất tại thời điểm làm; ghi ngày kiểm trong README.
- `check_gpu.py`: in tên GPU, VRAM, phiên bản CUDA/torch, chạy một matmul fp16 trên GPU; thoát mã ≠0 với thông điệp rõ nếu `torch.cuda.is_available()` sai.
- README: chạy notebook bằng kernel của env này (`uv run --project setup/gpu python -m ipykernel install --user --name ai-gpu`), dùng trên laptop 3050 và PC 3060 (cùng repo, `git pull`), cách mở Ollama trên PC cho laptop gọi (`OLLAMA_HOST=0.0.0.0` trên PC, `OLLAMA_HOST=http://<ip>:11434` trên laptop).

- [ ] **Step 1: Viết 3 tệp**
- [ ] **Step 2: Kiểm** — `uv lock --project setup/gpu` thành công; `uv run --project setup/gpu python setup/gpu/check_gpu.py` trên laptop in `RTX 3050` (tải ~3GB, chạy nền được). Root `uv run python -c "import torch; print(torch.version.cuda)"` vẫn `None` (CPU không đổi).
- [ ] **Step 3: Commit** — `git commit -m "setup/gpu: môi trường CUDA riêng cho bài train nặng của track AI Engineer"`

### Task 4: Khai báo track + README + capstone README

**Files:**
- Modify: `tracks/ai-engineer/track.json`
- Create: `tracks/ai-engineer/README.md`, `tracks/ai-engineer/capstone/README.md`

**Interfaces:**
- `track.json`: `status: "active"`, `description` một câu, `source`, `modules` đủ 23 mục đúng id + tiêu đề tiếng Việt theo bảng mục 4 spec, mỗi mục có `summary` và `topics`. **Chưa** có khoá `capstone` (thêm ở plan sau cùng milestone docs).
- Track README: đối tượng và mục tiêu (mục 1 spec), cách học hai phần A/B, sơ đồ mermaid phụ thuộc 23 module, bảng module ↔ node roadmap.sh (đánh dấu ★), phần cứng & môi trường (laptop/PC, `setup/gpu`, `llmkit` + cách cấu hình Ollama/OmniRoute/Gemini), dữ liệu (HF token, Kaggle), danh sách dự án portfolio (mục 5 spec), ngoài phạm vi.
- Capstone README: "Trợ lý pháp luật tiếng Việt", mục tiêu, kiến trúc tổng (mermaid), dữ liệu, 9 milestone theo mục 8 spec (chỉ mô tả, chưa có tệp milestone), cách chấm (recall@k, độ trung thực, rubric).

- [ ] **Step 1: Viết 3 tệp**
- [ ] **Step 2: Kiểm app** — `cd app && pnpm typecheck && pnpm build` thành công; `pnpm dev`, mở track AI Engineer thấy 23 module (chưa có nội dung).
- [ ] **Step 3: Commit** — `git commit -m "Track AI Engineer: khai báo 23 module, README track và capstone"`

### Task 5: Module 01 — lý thuyết + interview

**Files:** Create `tracks/ai-engineer/modules/01-nn-from-scratch/README.md`, `interview.md`

- [ ] **Step 1: `README.md`** — 8 phần `## `:
  1. Neuron: từ hồi quy logistic tới perceptron, vì sao cần phi tuyến
  2. Activation (sigmoid, tanh, ReLU, GELU, softmax ổn định số) và đạo hàm
  3. Layer, MLP, universal approximation; loss (MSE, cross-entropy) và vì sao softmax+CE có gradient `p - y`
  4. Backprop trên computational graph, viết bằng numpy; gradient check
  5. Khởi tạo (Xavier, He) và vanishing/exploding gradient, có thí nghiệm std activation qua 10 layer
  6. Optimizer: SGD, momentum, RMSProp, Adam, AdamW, learning rate schedule
  7. BatchNorm/LayerNorm, dropout; khi train hỏng thì nhìn gì (loss NaN, loss không giảm, overfit)
  8. Tài liệu tham khảo (CS231n, Karpathy "micrograd"/"Neural Networks: Zero to Hero", Goodfellow ch.6–8, link Introduction của PDF roadmap)
  Mở đầu nói rõ khác gì module 13 track DS (DS dùng PyTorch, ở đây tự viết mọi thứ bằng numpy rồi mới đối chiếu PyTorch). ≥2 mermaid (graph forward/backward; vòng train). Code mẫu numpy chạy được.
- [ ] **Step 2: `interview.md`** — ≥12 câu, gồm: tự suy gradient softmax+CE; vì sao ReLU chết và cách xử lý; He vs Xavier; Adam vs SGD khi nào; BatchNorm train vs eval; loss NaN ở epoch 3 thì debug thế nào (case); ≥2 câu case/system (ví dụ "model không học, loss đứng yên ở ln(10)").
- [ ] **Step 3: Kiểm** — mọi khối ` ```python ` trong README chạy được bằng `uv run python`; đếm `## ` interview ≥12.
- [ ] **Step 4: Commit** — `git commit -m "AI Engineer module 01: lý thuyết và câu hỏi phỏng vấn"`

### Task 6: Module 01 — Basic (3 bài `.py`, CPU)

Gốc: `tracks/ai-engineer/modules/01-nn-from-scratch/`. Starter: `# TODO` + `raise NotImplementedError`. Chỉ numpy trong starter/lời giải; test được dùng torch CPU để đối chiếu.

**`01-activations`, `activations.py`:** `sigmoid, tanh, relu, gelu` (xấp xỉ tanh) và `sigmoid_grad, tanh_grad, relu_grad, gelu_grad` (theo `x`), `softmax(z: ndarray, axis=-1)`.
Test: khớp `torch.nn.functional` (`gelu(approximate="tanh")`) `atol=1e-6`; đạo hàm khớp sai phân trung tâm `atol=1e-5`; `softmax([1000, 1001, 1002])` không `nan`, tổng 1; `sigmoid(-1000)` không cảnh báo overflow (`np.errstate(all="raise")`).

**`02-gradient-check`, `gradcheck.py`:** `numerical_grad(f: Callable[[ndarray], float], x: ndarray, eps: float = 1e-6) -> ndarray` (sai phân trung tâm, không sửa `x` sau khi trả), `relative_error(a: ndarray, b: ndarray) -> float` (`max |a-b| / max(|a|+|b|, 1e-12)`).
Test: gradient của `sum(x**3)`, `log(sum(exp(x)))` khớp giải tích `rel < 1e-7`; `x` không đổi sau gọi; phát hiện được gradient sai (nhân 1.01 → `rel > 1e-3`).

**`03-layers-backprop`, `layers.py`:** `Linear(in_features, out_features, rng: np.random.Generator)` (He init, `W` shape `(in, out)`), `ReLU()`, `SoftmaxCrossEntropy()`; mỗi lớp `forward(x)`, `backward(grad) -> grad_in`; `Linear` có `dW`, `db` sau backward; `SoftmaxCrossEntropy.forward(logits, y: int array) -> float` (trung bình batch), `backward() -> dlogits`.
Test (float64): gradient từng lớp và cả chuỗi `Linear→ReLU→Linear→SoftmaxCE` khớp số `rel < 1e-6`; loss và `dW` khớp torch cùng trọng số `atol=1e-8`; logits 1e3 không nan.

- [ ] **Step 1: README + starter + test 3 bài**
- [ ] **Step 2: Starter** — `uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch/exercises/basic -q` → FAIL, không ERROR.
- [ ] **Step 3: Lời giải + `SOLUTION.md`**
- [ ] **Step 4: Lời giải** — `SOLUTION=1 uv run pytest …/exercises/basic -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "AI Engineer module 01: bài tập Basic"`

### Task 7: Module 01 — Intermediate (3 bài, notebook, MNIST thật, CPU)

Mỗi bài notebook có `quiz.yaml` (5–8 câu, nửa `data` nửa `knowledge`; câu `data` lấy số từ chạy lời giải với seed ghim) và `solutions/.../quiz-answers.yaml`. Notebook tự chứa lớp cần dùng (không import chéo bài). Cell đầu: tìm `ROOT`, `ensure("mnist")`.

**`01-mlp-mnist`, `mlp.ipynb`:** `load_mnist(root: Path) -> tuple[X_train, y_train, X_test, y_test]` (float32 /255, đọc idx gz), `class MLP(sizes: list[int], seed: int)` với `forward(X) -> logits`, `loss_and_backward(X, y) -> float`, `params() -> list[tuple[ndarray, ndarray]]` (cặp param, grad); `sgd_step(model, lr)`; `train_epoch(model, X, y, lr, batch_size, rng) -> float` (loss trung bình); `accuracy(model, X, y) -> float`.
Test: dữ liệu sinh nhỏ — loss epoch 2 < epoch 1; overfit 32 mẫu tới acc 1.0 trong 200 bước; seed giống → kết quả giống. Dữ liệu thật (`ex.dataset("mnist")`): `load_mnist` shape `(60000, 784)`, dtype float32, max 1.0; MLP `[784,128,10]` lr 0.1 batch 64, 2 epoch trên 20000 mẫu đầu → test acc ≥ ngưỡng builder hiệu chỉnh từ lời giải (trừ 1 điểm %), chạy < 30 giây.

**`02-init-and-optimizers`, `optim.ipynb`:** `xavier_init(fan_in, fan_out, rng)`, `he_init(fan_in, fan_out, rng)`; `class SGDMomentum(lr, momentum)`, `class Adam(lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)` (AdamW kiểu decoupled khi `weight_decay>0`), cả hai `step(params: list[tuple[ndarray, ndarray]])` cập nhật tại chỗ.
Test: 20 bước trên hàm bậc hai khớp `torch.optim.SGD(momentum)` và `torch.optim.AdamW` `atol=1e-6`; `he_init(1000, 1000)` var ≈ `2/1000` (`rel=0.05`). Explore: std activation qua 10 layer với init sai/đúng; so SGD vs Adam trên MNIST.

**`03-batchnorm-dropout`, `regularize.ipynb`:** `class BatchNorm1d(num_features, momentum=0.1, eps=1e-5)` có `forward(x, training: bool)`, `backward(grad)`, `dgamma`, `dbeta`, running stats; `class Dropout(p, rng)` inverted dropout, `forward(x, training)`, `backward(grad)`.
Test: forward train/eval khớp `torch.nn.BatchNorm1d` (kể cả running_var unbiased) `atol=1e-6`; gradient check `rel < 1e-5`; Dropout: kỳ vọng giữ nguyên (mean trên 1e6 phần tử `rel=0.01`), eval là identity. Explore: MLP MNIST có/không BN, có/không dropout, vẽ đường cong.

- [ ] **Step 1: README + starter notebook (cell chấm chỉ `def`/`class`, cell `explore` tag + dòng `# explore: ...`) + test + quiz.yaml**
- [ ] **Step 2: Starter** → FAIL/SKIP, không ERROR.
- [ ] **Step 3: Lời giải notebook + `SOLUTION.md` + `quiz-answers.yaml`**
- [ ] **Step 4: Kiểm** — `SOLUTION=1 uv run pytest …/exercises/intermediate -q` PASS; mỗi notebook lời giải `uv run jupyter nbconvert --to notebook --execute --stdout <nb> > /dev/null` thành công; `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` PASS.
- [ ] **Step 5: Commit** — `git commit -m "AI Engineer module 01: bài tập Intermediate trên MNIST"`

### Task 8: Module 01 — Advanced (2 bài) + kiểm module

**`01-numpy-framework-mnist`** (portfolio): mini framework numpy (Module/Sequential, Linear, ReLU, BN, Dropout, SoftmaxCE, AdamW, LR schedule, early stopping) đạt ≥ 97.5% test MNIST. Starter `framework.ipynb` định nghĩa `build_model(seed: int)`, `fit(model, X, y, X_val, y_val, epochs: int) -> dict[str, list[float]]` (history `train_loss`, `val_acc`), `evaluate(model, X, y) -> float`; `REPORT.md` khung (kiến trúc, đường cong, ablation BN/dropout/optimizer, lỗi đã gặp). Test fixture nhỏ: `evaluate` trong [0,1], history đúng độ dài; dữ liệu thật: acc ≥ 0.975 (skip nếu chưa tải). **Phần cứng:** CPU ~10 phút.

**`02-debug-broken-training`**: notebook `broken.ipynb` chứa MLP numpy có 4 bug "im lặng" cố ý (builder chọn, ví dụ: gradient không chia batch size, softmax không trừ max, nhãn bị lệch sau shuffle, bias dùng chung tham chiếu); người học sửa và ghi `BUGS.md` (triệu chứng → cách phát hiện → sửa). Test: `train(seed)` trên dữ liệu sinh nhỏ đạt acc ≥ 0.95 và `gradient_check_passes() is True`; đề không nói bug ở đâu.

Mỗi bài: `quiz.yaml` + `quiz-answers.yaml`, `SOLUTION.md` (hướng làm + rubric), không có code lời giải.

- [ ] **Step 1: README + starter + test + SOLUTION.md + quiz cho 2 bài**
- [ ] **Step 2: Kiểm module** — `uv run pytest tracks/ai-engineer/modules/01-nn-from-scratch -q` chỉ FAIL/SKIP; `SOLUTION=1 …` PASS (SKIP chỉ Advanced); builder tự giải 2 bài Advanced ở nhánh nháp (không commit) để chắc đạt được ngưỡng và hiệu chỉnh số liệu quiz.
- [ ] **Step 3: Commit** — `git commit -m "AI Engineer module 01: bài tập Advanced, hoàn thiện module mẫu"`

### Task 9: Module 13 — lý thuyết + interview

**Files:** Create `tracks/ai-engineer/modules/13-rag/README.md`, `interview.md`

- [ ] **Step 1: `README.md`** — 8 phần `## `:
  1. RAG giải quyết gì; RAG vs fine-tuning vs long context (bảng quyết định); use cases
  2. Chuẩn bị tài liệu và chunking (fixed, theo cấu trúc, semantic; văn bản luật Việt Nam: Điều/Khoản/Điểm; Unicode NFC)
  3. Retrieval: BM25 (tiếng Việt: âm tiết vs tách từ), dense embedding, hybrid + RRF
  4. Reranking (cross-encoder, LLM rerank) và đánh đổi độ trễ
  5. Generation có trích dẫn: prompt, định dạng nguồn, từ chối khi thiếu căn cứ, prompt injection qua tài liệu (trỏ module 19)
  6. Đánh giá RAG: recall@k, MRR, nDCG; faithfulness, answer relevance, LLM-as-judge và giới hạn
  7. Cách triển khai: SDK trực tiếp vs LangChain vs LlamaIndex; RAG nâng cao (query rewriting, HyDE, multi-hop, GraphRAG, agentic RAG — giới thiệu, trỏ 16/17); thay "OpenAI Assistant API" của roadmap bằng tương đương hiện hành (ghi chú)
  8. Tài liệu tham khảo (link mục RAG trong PDF roadmap + paper RAG gốc, BM25, RRF, bge-m3)
  ≥2 mermaid (pipeline indexing/query; cây quyết định RAG vs fine-tune). Ví dụ dùng Zalo Legal + `llmkit`.
- [ ] **Step 2: `interview.md`** — ≥12 câu, gồm: chọn chunk size; vì sao hybrid hơn dense thuần với văn bản luật; đo hallucination; RAG trả lời sai thì debug từ đâu (retrieval hay generation); bảo mật đa người dùng (ACL trong retrieval); ≥3 câu system design ("thiết kế RAG cho 1 triệu văn bản nội bộ, p95 < 2s").
- [ ] **Step 3: Kiểm** — khối python chạy được (khối cần Ollama/dữ liệu chạy sau khi có); đếm `## ` ≥12.
- [ ] **Step 4: Commit** — `git commit -m "AI Engineer module 13: lý thuyết RAG và câu hỏi phỏng vấn"`

### Task 10: Module 13 — Basic (3 bài `.py`, CPU, không LLM)

Fixture test là đoạn văn bản luật **builder tự viết** theo đúng định dạng (không trích Zalo Legal).

**`01-chunking`, `chunking.py`:** `normalize(text: str) -> str` (NFC, gộp khoảng trắng), `chunk_fixed(text: str, size: int, overlap: int) -> list[str]` (theo ký tự, `overlap < size` nếu không `ValueError`), `chunk_legal(article_text: str, max_chars: int) -> list[str]` (tách theo khoản `1.`, `2.`… ở đầu dòng, khoản dài hơn `max_chars` tách tiếp theo điểm `a)`, `b)`…, mỗi chunk giữ dòng tiêu đề Điều làm tiền tố).
Test: ghép `chunk_fixed` bỏ overlap ra lại văn bản gốc; `overlap >= size` → ValueError; `chunk_legal` trên fixture 3 khoản cho đúng 3 chunk có tiền tố "Điều 5."; khoản dài tách theo điểm; NFD đầu vào cho kết quả giống NFC.

**`02-bm25`, `bm25.py`:** `tokenize_vi(text: str) -> list[str]` (NFC, lower, bỏ dấu câu, tách theo khoảng trắng — mức âm tiết), `class BM25(docs: list[list[str]], k1: float = 1.5, b: float = 0.75)` với `scores(query: list[str]) -> np.ndarray`, `top_k(query: list[str], k: int) -> list[int]`. IDF dạng Lucene `log(1 + (N - n + 0.5)/(n + 0.5))`.
Test: điểm khớp giá trị tính tay trên corpus 3 tài liệu `abs=1e-9`; tài liệu không chứa từ truy vấn điểm 0; `b=0` không phụ thuộc độ dài; "Luật" và "luật" (NFD) cùng token.

**`03-retrieval-metrics`, `metrics.py`:** `recall_at_k(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float`, `mrr_at_k(...)`, `ndcg_at_k(...)` (gain nhị phân), trung bình trên các truy vấn.
Test: giá trị tính tay trên 3 truy vấn; truy vấn không có tài liệu liên quan → `ValueError`; `k` lớn hơn danh sách không lỗi.

- [ ] **Step 1–5:** như Task 6 (README + starter + test → starter FAIL → lời giải + SOLUTION.md → SOLUTION=1 PASS → commit `"AI Engineer module 13: bài tập Basic"`).

### Task 11: Module 13 — Intermediate (3 bài notebook, Zalo Legal thật, laptop)

Cell đầu `ensure("zalo-legal")`. **Dữ liệu (đã kiểm ở Task 2):** mirror `GreenNode/zalo-ai-legal-text-retrieval-vn`, JSONL kiểu BEIR: `corpus.jsonl` (61 425 điều, `{_id: "<law_id>+<article_id>", title, text}`), `queries.jsonl` (3 298 câu, `{_id, text}`), `qrels/train.jsonl` và `qrels/test.jsonl` (`{query-id, corpus-id, score}`). **Tập đánh giá ghim** dùng chung 3 bài: 300 `query-id` phân biệt đầu tiên theo thứ tự tệp `qrels/test.jsonl` (giữ split train cho milestone fine-tune), corpus = toàn bộ điều luật. Embedding corpus bằng `bge-m3` qua `llmkit.embed`, cache `data/raw/zalo-legal/cache/bge-m3.npy` (+ danh sách id). Builder đo thời gian embed trên laptop; nếu > 60 phút thì ghim corpus con xác định (mọi điều của các luật xuất hiện trong 300 câu + mẫu ngẫu nhiên seed 0 tới 10 000 điều) và ghi rõ trong README bài. Mỗi bài có quiz (số liệu `data` từ chạy lời giải trên tập ghim).

**`01-hybrid-retrieval`, `retrieval.ipynb`:** `load_corpus(root) -> list[Article]` (`Article` dataclass `uid: str` = `_id` của corpus, `title`, `text`), `load_questions(root, n: int, split: str = "test") -> list[Question]` (`qid`, `text`, `relevant: set[str]`; n query-id đầu theo thứ tự `qrels/<split>.jsonl`), `embed_corpus(texts, embed_fn, batch_size: int = 32) -> np.ndarray` (chuẩn hoá L2), `dense_search(q_vec, matrix, k) -> list[int]`, `rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[int]`.
Test: `FakeLLM.embed` + corpus nhỏ tự viết: dense tìm đúng; `rrf_fuse` khớp tính tay; `embed_corpus` gọi theo batch đúng số lần. Explore: bảng recall@1/5/10, MRR@10 của BM25 / dense / hybrid trên tập ghim.

**`02-rag-with-citations`, `rag.ipynb`:** `build_messages(question: str, passages: list[Article]) -> list[Message]` (nguồn đánh số `[1]..[n]`, chỉ thị chỉ dùng nguồn, trích dẫn dạng `[i]`, nói "Không tìm thấy căn cứ" khi thiếu), `parse_citations(answer: str, n_passages: int) -> list[int]` (bỏ số ngoài `1..n`, bỏ trùng, giữ thứ tự), `answer(question, retrieve: Callable[[str], list[tuple[Article, float]]], llm: LLMClient, min_score: float) -> RagAnswer` (`text`, `citations: list[str]` uid, `refused: bool`; không gọi LLM khi mọi điểm < `min_score`).
Test (FakeLLM): prompt chứa đủ nguồn đánh số; `[7]` khi n=5 bị bỏ; điểm thấp → `refused=True` và `FakeLLM.calls` rỗng; trích dẫn map đúng uid. Explore: 20 câu thật với `qwen2.5:3b`, in câu trả lời + nguồn.

**`03-reranking`, `rerank.ipynb`:** `rerank(query: str, candidates: list[Article], score_fn: Callable[[str, list[str]], list[float]], top_n: int) -> list[Article]`, `cross_encoder_score_fn(model_name: str = "BAAI/bge-reranker-v2-m3") -> Callable` (sentence-transformers `CrossEncoder`, CPU, lazy load). Test với `score_fn` giả: thứ tự đúng, `top_n` cắt đúng, ổn định khi điểm bằng nhau. Explore: MRR@10 hybrid trước/sau rerank top-50 trên 100 câu đầu tập ghim, kèm độ trễ/câu. Thêm `sentence-transformers` vào `pyproject.toml` (torch CPU sẵn có).

- [ ] **Step 1–5:** như Task 7 (README + starter + test + quiz → starter FAIL/SKIP → lời giải + SOLUTION.md + quiz-answers → `SOLUTION=1` PASS, nbconvert từng notebook lời giải thành công khi có Ollama + dữ liệu, `tests/test_quiz_files.py` PASS → commit `"AI Engineer module 13: bài tập Intermediate trên Zalo Legal"`). Nếu `zalo-legal` chưa tải được vì chờ token: làm phần test/starter/lời giải với fixture, để câu quiz `data` và nbconvert lại, báo người học.

### Task 12: Module 13 — Advanced (2 bài) + kiểm tổng + bàn giao

**`01-rag-eval-harness`**: bộ đánh giá RAG end-to-end: retrieval metrics (dùng lại hàm Basic 03 — chép vào bài, không import chéo), faithfulness và answer relevance bằng LLM-as-judge (`qwen2.5:7b` khuyên chạy trên PC, `qwen2.5:3b` được trên laptop), so ≥3 cấu hình (chunk, hybrid, rerank). Starter `eval.ipynb`: `judge_faithfulness(answer: str, passages: list[str], llm) -> float` (0–1, parse JSON qua `json_schema`), `run_eval(configs: dict[str, Callable], questions) -> pd.DataFrame`; `REPORT.md` khung. Test FakeLLM: parse điểm, JSON hỏng → `nan` không crash, DataFrame đúng cột.

**`02-rag-frameworks`**: dựng lại pipeline bài Intermediate 02 bằng LangChain (`langchain-ollama`) hoặc LlamaIndex, so với bản SDK trực tiếp về số dòng code, độ trễ, chất lượng trên 50 câu; `COMPARE.md`. Test: hàm `build_chain()` tồn tại và chạy được với một LLM giả của framework (builder chọn `FakeListChatModel` của LangChain nếu dùng LangChain). Thêm dependency framework đã chọn.

Mỗi bài: `quiz.yaml` + `quiz-answers.yaml`, `SOLUTION.md` (hướng làm + rubric).

- [ ] **Step 1: README + starter + test + SOLUTION.md + quiz cho 2 bài**
- [ ] **Step 2: Kiểm tổng**
  - `uv run pytest tracks/ai-engineer -q` → chỉ FAIL/SKIP, không ERROR.
  - `SOLUTION=1 uv run pytest tracks/ai-engineer -q` → PASS, SKIP chỉ ở Advanced và dữ liệu thật chưa tải.
  - `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` → bằng con số ở Task 1 Step 1.
  - `uv run pytest tests -q` → PASS.
  - `cd app && pnpm build` → thành công; mở app: module 01 và 13 hiện đủ lý thuyết, interview, bài tập, quiz.
- [ ] **Step 3: Commit** — `git commit -m "AI Engineer module 13: bài tập Advanced, hoàn thiện module mẫu"`
- [ ] **Step 4: Bàn giao** cho người học: nhờ duyệt văn phong, độ khó, trải nghiệm notebook/quiz của hai module; liệt kê việc còn chờ người học (HF token, đăng ký Zalo/MC-OCR, truy cập PC) và số liệu chưa kiểm được vì thiếu chúng.
