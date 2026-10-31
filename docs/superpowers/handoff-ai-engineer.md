# Bàn giao: track AI Engineer (tiếp tục trên PC RTX 3060 12GB)

Ngày bàn giao: 2026-10-30. Viết cho phiên Claude Code tiếp theo chạy trên PC của người học. Đọc hết tài liệu này trước khi làm bất cứ việc gì.

## 1. Người học và mục tiêu (đã chốt với người học)

- Người học viết tiếng Việt, muốn nội dung tiếng Việt giữ thuật ngữ tiếng Anh. Đã xong track Data Engineer và AI & Data Scientist.
- Mục tiêu nguyên văn: "tất cả mọi thứ để trở thành một AI Engineer lão luyện". Hiểu AI từ bên trong (layer, neuron, kiến trúc), có sản phẩm tự làm về NLP, computer vision, game (RL), agent, LangChain/LangGraph. Thêm phần mới của ngành khi có.
- Người học yêu cầu **tự hoàn thành cả track như một senior**, không dừng chờ duyệt module mẫu. Chỉ dừng hỏi khi cần thứ chỉ người học cấp được (API key, đăng ký dữ liệu, truy cập máy), hoặc thao tác không đảo ngược (merge vào `main`, xoá dữ liệu).
- Chạy kiểu subagent-driven (superpowers:subagent-driven-development): mỗi module một implementer + một reviewer độc lập, sửa tới khi review sạch. **Tối đa 2 module chạy song song** (người học chốt sau khi laptop bị quá tải).
- Commit message tiếng Việt, **không bao giờ** thêm dòng `Co-Authored-By`.
- Ưu tiên dữ liệu thật (Kaggle/HF/công khai), dữ liệu sinh chỉ dùng làm fixture cho test.

## 2. Tài liệu gốc (đọc theo thứ tự)

1. Spec: `docs/superpowers/specs/2026-10-29-ai-engineer-track-design.md` (mục đích, 23 module, ràng buộc, capstone).
2. Plan giai đoạn 1–2 (đã xong): `docs/superpowers/plans/2026-10-29-ai-engineer-phase1-2.md`.
3. Plan giai đoạn 3 (đang làm): `docs/superpowers/plans/2026-10-30-ai-engineer-phase3.md`. Bảng "Nội dung bắt buộc theo module" là yêu cầu nội dung của từng module.
4. Hướng dẫn chung cho implementer: `docs/superpowers/ai-engineer/module-implementer.md`.
5. Hướng dẫn chung cho reviewer: `docs/superpowers/ai-engineer/module-reviewer.md`.
6. `CONTENT_SPEC.md` (quy ước nội dung app), `testkit.py`, `llmkit.py`, `data/README.md` (mọi bộ dữ liệu và thư viện đã chuẩn bị cho giai đoạn 3).
7. Module mẫu chuẩn: `tracks/ai-engineer/modules/01-nn-from-scratch/` (phần A) và `tracks/ai-engineer/modules/13-rag/` (phần B).

## 3. Trạng thái (cập nhật lúc bàn giao)

Nhánh tích hợp: **`ai-engineer`** (mọi thứ đã review). Nhánh module làm dở: `ae-m-<id>` (một commit "WIP … chưa review" ở đỉnh).

| Module | Trạng thái | Ở đâu | Việc còn lại |
| --- | --- | --- | --- |
| Hạ tầng (`llmkit`, `testkit`, `setup/gpu`, registry dữ liệu, `track.json` 23 module) | Xong, đã review | `ai-engineer` | — |
| Task 0 giai đoạn 3 (thư viện + 10 bộ dữ liệu) | Xong, đã review | `ai-engineer` | MC-OCR chờ người học đăng ký |
| 00 introduction | Xong, đã review | `ai-engineer` | Số độ trễ Int-02 đo lúc máy bị chiếm (đã ghi chú) — đo lại trên PC nếu muốn |
| 01 nn-from-scratch | Xong, đã review (module mẫu A) | `ai-engineer` | — |
| 02 pytorch-deep-dive | Xong, đã review | `ai-engineer` | Vài số GPU đo khi GPU bị chiếm (đã ghi chú) — đo lại trên PC |
| 03 computer-vision | **WIP, chưa review** | `ae-m-03-computer-vision` | Agent dừng giữa notebook đánh giá detection/segmentation; script train tham chiếu nằm ở scratch (không push) → làm lại phần tham chiếu. Hoàn thiện, kiểm, review |
| 04 nlp-sequence-models | **WIP, chưa review** | `ae-m-04-nlp-sequence-models` | Basic + Intermediate đã commit (chưa review); README lý thuyết, interview, Advanced ở commit WIP — hoàn thiện, chạy kiểm cuối, review |
| 05–08, 10–12, 14–20 | Chưa bắt đầu | — | Theo bảng plan giai đoạn 3 |
| 09 llms-and-open-models | **WIP, chưa review** | `ae-m-09-llms-and-open-models` | Agent dừng sớm (đang thử gọi Ollama) — coi như làm lại, dùng phần đã có làm nháp |
| 13 rag | Xong, đã review (module mẫu B) | `ai-engineer` | Bảng judge Advanced 01 chấm bằng `auto/gemini-3.8-flash` (OmniRoute); bảng judge local `qwen2.5:3b`/`7b` chưa đo xong → đo trên PC, cập nhật SOLUTION nếu khác |
| 21 ai-system-design | Xong, đã review | `ai-engineer` | Link tới module 09–20 và capstone sẽ sống khi các module đó có |
| 22 quantum-ml | Xong, đã review | `ai-engineer` | Ghi "cập nhật dần" |
| Capstone (Task 22 của plan) | Chưa bắt đầu | — | Sau khi có 10, 12, 14, 17, 19, 20 |

Kiểm lúc bàn giao (laptop): `SOLUTION=1 uv run pytest tracks/ai-engineer -q` → 150 passed, 52 skipped (skip = Advanced); starter chỉ FAIL, 0 ERROR; `uv run pytest tests -q` pass; root torch `2.14.1+cpu`. Sau khi gộp Task 0, `langchain-core` là 1.6.12 (Task 12 viết với 1.7.3, test module 13 vẫn pass).

Với module WIP: tạo worktree từ nhánh `ae-m-<id>` (không tạo nhánh mới), rebase lên `ai-engineer` mới nhất, dispatch implementer với chỉ dẫn "đọc phần đã có, hoàn thiện theo dòng module, chạy toàn bộ kiểm", rồi review như module mới.

## 4. Bài học từ review (áp cho mọi module còn lại)

Những lỗi reviewer đã bắt nhiều lần. Đưa vào dispatch và kiểm khi review:

- **Không lộ lời giải.** README lý thuyết và starter không chứa code giải bài tập của chính module (module 01, 13 đều phải gỡ). Giải thích bằng công thức, sơ đồ, số đo, đoạn code minh hoạ không dùng được ngay.
- **Mọi con số phải đo thật** với seed ghim. Con số trong lý thuyết, quiz và ngưỡng test phải khớp nhau. Khi đổi cách cài (ví dụ BM25 khử trùng token) phải đo lại bảng lý thuyết.
- **Quiz bền.** Câu `data` không được phụ thuộc chữ LLM sinh ra, số luồng BLAS (float32 lệch ở chữ số thứ 4), hay giá trị sát ngưỡng. Dùng khoảng/so sánh hoặc chuyển thành `knowledge`. Đáp án không được in sẵn trong README/interview.
- **Giá và thông số model đổi nhanh.** Chỉ ghi giá đã kiểm trên trang chính thức kèm ngày kiểm; còn lại ghi rõ "giả định". Trang giá Anthropic 2026-10-30 có Claude Fable 5.1 ($10/$50), Opus 5.5, Sonnet 5.5, Haiku 5.5.
- **Dòng `**Phần cứng:** … · ~N phút`** đầu `## Đề bài`: N là thời gian **làm bài** của người học, thời gian máy chạy ghi riêng.
- **Test phải phân biệt cài sai.** Implementer tự viết vài "mutant" (cài sai hợp lý) và chắc test bắt được. Test offline, không GPU, không LLM thật (`llmkit.FakeLLM`), < 30 giây, starter FAIL không ERROR.
- **Đo độ trễ khi máy bị chiếm** phải ghi rõ điều kiện; tách service time khỏi queue time.
- **Gợi ý (Gợi ý 1/2)** dẫn hướng, không đưa thuật toán từng bước; bài debug không được chỉ thẳng chỗ có bug.
- Thông tin pháp lý/đời thực không kiểm được thì viết thận trọng ("theo nguồn …", "chưa kiểm hiệu lực ngày …").

## 5. Các quyết định đã tự đưa ra (người học đọc lại để sửa nếu không đồng ý)

| Quyết định | Lý do | Rủi ro nếu sai |
| --- | --- | --- |
| Zalo Legal lấy từ mirror HF `GreenNode/zalo-ai-legal-text-retrieval-vn` (MIT) vì repo `nntoan209/ZaloLegal` đã mất | Cùng dữ liệu Zalo AI 2021, spec cho phép bộ tương đương | Mirror có thể lệch nhẹ bản gốc |
| Dữ liệu Zalo dạng BEIR JSONL; tập đánh giá ghim = 300 `query-id` đầu của `qrels/test.jsonl`; giữ split train cho milestone fine-tune | Theo cấu trúc thật của mirror | Số quiz gắn với lựa chọn này |
| Root env giữ torch CPU; GPU qua uv project riêng `setup/gpu` (CUDA 12.6 vì driver laptop 550) | Không phá track DE/DS | Trên PC driver mới hơn có thể dùng CUDA mới hơn, không bắt buộc |
| `llama-cpp-python` ở nhóm tuỳ chọn `uv sync --group llama` (build từ source cần gcc/cmake) | `uv sync` mặc định phải chạy trên mọi máy | — |
| vLLM không cài được (vllm 0.31 cần transformers <5.18, env cần ≥5.22) → module 20 dùng llama.cpp server/Ollama | Xung đột phụ thuộc | Trên PC có thể thử vLLM trong env riêng |
| huggingface-hub ghim <2.0 vì diffusers 0.41 | Xung đột phụ thuộc | Xem lại sau 2026-11-06 |
| `constraint-dependencies` chặn phụ thuộc gián tiếp phát hành sau 2026-10-16 (quy tắc ≥2 tuần tuổi) | Ổn định | Gỡ và `uv lock --upgrade` từ 2026-11-13 |
| Common Voice vi cần đăng nhập HF → dùng FLEURS vi | Không tự vượt đăng ký | — |
| MC-OCR cần đăng ký với ban tổ chức → chưa có; bài trợ lý tài chính (module 18) tạm chỉ quiz `knowledge` | Chờ người học | Bài portfolio 18 chưa có dữ liệu hoá đơn |
| OmniRoute (gateway người học cung cấp) chỉ dùng cho LLM-as-judge và phần API tuỳ chọn (Advanced 13/19/20), không dùng cho số liệu chính của bài | Bài phải tái lập được bằng `qwen2.5:3b` local | — |
| SOLUTION.md của Advanced được trích một dòng sửa lỗi | Đó là tài liệu lời giải; "không code" nghĩa là không có tệp lời giải chạy được | — |
| Bỏ cổng "duyệt module mẫu" của spec §9 theo yêu cầu người học | Người học muốn làm trọn track | Lỗi văn phong/độ khó lan ra mọi module |

## 6. Runbook trên PC

### 6.1 Chuẩn bị máy

```bash
git clone <remote> DataScience && cd DataScience
git checkout ai-engineer
uv sync                                   # root env (torch CPU), test chạy ở đây
uv sync --project setup/gpu               # env CUDA; xem setup/gpu/README.md
uv run --project setup/gpu python setup/gpu/check_gpu.py   # phải in RTX 3060, ~12 GB
uv run --project setup/gpu python -m ipykernel install --user --name ai-gpu
cd app && pnpm install --frozen-lockfile && cd ..
```

- Driver PC mới hơn có thể dùng index CUDA mới hơn trong `setup/gpu/pyproject.toml`; nếu đổi thì lock lại và chạy `check_gpu.py`.
- Ollama: `ollama pull qwen2.5:3b qwen2.5:7b bge-m3 nomic-embed-text`. PC đủ VRAM cho model 7B–14B; số liệu bài Basic/Intermediate vẫn đo bằng `qwen2.5:3b` (người học dùng laptop 4GB).

### 6.2 Dữ liệu (`data/raw` không nằm trong git)

```bash
uv run python data/download_dataset.py --list
for d in mnist zalo-legal cifar10 oxford-pets penn-fudan uit-vsfc iwslt15-en-vi wikipedia-vi openorca-viet gsm8k prompt-injections fleurs-vi; do
  uv run python data/download_dataset.py "$d"
done
```

- Cache của module 13 (`data/raw/zalo-legal/cache/`: embedding bge-m3 toàn corpus ~45 phút trên laptop, hybrid top-100, rerank top-50) do notebook bài Intermediate 01/03 tự tạo lại khi chạy.
- Kaggle (nếu cần): `KAGGLE_API_TOKEN=KGAT_...` trong `setup/.env`.

### 6.3 `setup/.env` (không commit)

Chép từ laptop hoặc tạo mới: các biến cổng Docker của track DE (nếu dùng), `KAGGLE_API_TOKEN`, `HF_TOKEN` (tuỳ chọn), và OmniRoute:

```
OMNIROUTE_BASE_URL=https://omniroute.ai-gateway.tk2s.org/v1
OMNIROUTE_API_KEY=...
OMNIROUTE_MODEL=auto/gemini-3.8-flash
```

Chỉ id `auto/gemini-3.8-flash` gọi được (chat + json_schema, ~7 s/lần); các id `openrouter/...` trả 402/429.

### 6.4 Cách chạy module còn lại

1. Mỗi module một worktree + nhánh tách từ `ai-engineer`:
   ```bash
   git worktree add -b ae-m-<id> ../DataScience-ae-m<NN> ai-engineer
   ln -s "$PWD/data/raw" ../DataScience-ae-m<NN>/data/raw
   ln -s "$PWD/setup/.env" ../DataScience-ae-m<NN>/setup/.env
   (cd ../DataScience-ae-m<NN> && uv sync)
   ```
2. Dispatch implementer (model mạnh nhất cho nội dung) với: đường dẫn worktree, `docs/superpowers/ai-engineer/module-implementer.md`, dòng của module trong bảng plan giai đoạn 3 (chép nguyên văn + ghi chú riêng), đường dẫn báo cáo.
3. Khi implementer xong: tạo diff (`git log`, `git diff --stat`, `git diff -U5` từ điểm tách) thành một tệp, dispatch reviewer với `docs/superpowers/ai-engineer/module-reviewer.md` + diff + báo cáo. Có lỗi Critical/Important thì gửi lại cho chính implementer sửa, rồi re-review phạm vi hẹp. Lỗi Minor rẻ thì gửi sửa luôn một lượt.
4. Review sạch → merge nhánh module vào `ai-engineer` (`git merge --no-ff`), xoá worktree. Module không sửa tệp dùng chung nên không xung đột; nếu cần thêm thư viện/dữ liệu, controller thêm bằng một commit nhỏ trên `ai-engineer` rồi module rebase.
5. Sau mỗi merge: `SOLUTION=1 uv run pytest tracks -q` không giảm số pass; `uv run pytest tests -q` PASS; `cd app && pnpm build`.

Thứ tự đề xuất (2 module một lúc, ghép nặng GPU với nhẹ):
04 + 03 (tiếp từ nhánh WIP) → 09 (WIP) + 05 → 11 + 06 → 12 + 07 → 10 + 08 → 16 + 14 → 17 + 15 → 19 + 18 → 20 → capstone (Task 22).
05 phải xong trước 08 (08 dùng GPT mini của 05). Capstone cần 10, 12, 14, 17, 19, 20, 21.

### 6.5 Kết thúc

- Kiểm tổng theo Task 22 của plan giai đoạn 3.
- Review toàn nhánh (một reviewer mạnh nhất đọc diff `main..ai-engineer`).
- Hỏi người học trước khi merge vào `main` hoặc push.
