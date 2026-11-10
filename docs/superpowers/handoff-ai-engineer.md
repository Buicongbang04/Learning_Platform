# Tổng kết: track AI Engineer (đã hoàn thành)

Cập nhật 2026-11-10. Thay bản bàn giao ngày 2026-10-30. Đọc tài liệu này trước khi sửa hay mở rộng track.

## 1. Trạng thái

Track **hoàn thành**, đã gộp vào `main` qua PR #12 (merge commit `a435653`, 2026-11-02). `tracks/ai-engineer/track.json` ở
trạng thái `active`, có 23 module (00–22, 173 bài) và capstone "Trợ lý pháp luật tiếng Việt" 9 milestone.

Mỗi module do một agent soạn và một reviewer độc lập kiểm, sửa tới khi review sạch rồi mới gộp. Kiểm trên `main` ngày
2026-11-10 (sau khi đã có thêm track MLOps và FDE):

| Kiểm | Kết quả |
| --- | --- |
| `uv run pytest tracks/ai-engineer -q` (starter) | 2261 failed, 14 passed, 50 skipped, 0 error |
| `SOLUTION=1 uv run pytest tracks/ai-engineer -q` | 1884 passed, 441 skipped, 0 failed |
| `uv run pytest tests/test_quiz_files.py -q` | 515 passed |
| torch ở env gốc | `2.14.1+cpu` |

Skip gồm bài Advanced (lời giải là `SOLUTION.md`), 49 test capstone (không có lời giải trong repo) và test cần dữ liệu chưa tải.

## 2. Tài liệu gốc

1. Spec: `docs/superpowers/specs/2026-10-29-ai-engineer-track-design.md`.
2. Plan: `docs/superpowers/plans/2026-10-29-ai-engineer-phase1-2.md` và `docs/superpowers/plans/2026-10-30-ai-engineer-phase3.md`.
3. Hướng dẫn agent: `docs/superpowers/ai-engineer/module-implementer.md` (quy tắc cứng, gồm bài học review) và
   `docs/superpowers/ai-engineer/module-reviewer.md`.
4. `CONTENT_SPEC.md`, `testkit.py`, `llmkit.py`, `data/README.md`.

## 3. Môi trường

- Env gốc `uv sync`: torch CPU, test chạy ở đây. Nhóm tuỳ chọn `uv sync --group llama` (llama-cpp-python, build từ source).
- Env GPU riêng `setup/gpu` (CUDA 12.6, Python do uv quản lý vì Triton/`torch.compile` cần `Python.h`); có thêm gymnasium,
  ale-py, imageio, kagglehub. Kernel Jupyter: `uv run --project setup/gpu python -m ipykernel install --user --name ai-gpu`.
- LLM local qua Ollama: `qwen2.5:3b` (số liệu bài), `qwen2.5:7b` (ô mở rộng trên PC), `bge-m3`, `nomic-embed-text`,
  `qwen3-vl:2b` (module 18). OmniRoute chỉ dùng tuỳ chọn; id `auto/...` là router, model phía sau thay đổi.
- Dữ liệu: `uv run python data/download_dataset.py <tên>` cho mnist, zalo-legal, cifar10, oxford-pets, penn-fudan, uit-vsfc,
  iwslt15-en-vi, wikipedia-vi, openorca-viet, gsm8k, prompt-injections, fleurs-vi, cord-v2. Cache embedding `bge-m3` của Zalo
  Legal (~47 phút trên PC) do notebook module 12 tạo lần đầu và module 13, 17, capstone dùng lại.
- Checkpoint GPT mini của người học (module 05 Advanced 01): đặt biến `GPT_MINI_CKPT`; module 08 và 10 đọc qua biến này.

## 4. Quyết định đã đưa ra

| Quyết định | Lý do |
| --- | --- |
| Zalo Legal từ mirror HF `GreenNode/zalo-ai-legal-text-retrieval-vn`; tập đánh giá ghim = 300 `query-id` đầu của `qrels/test.jsonl` | Repo gốc đã mất |
| Module 18 dùng `cord-v2` (hoá đơn Indonesia, CC BY 4.0) thay MC-OCR | MC-OCR cần đăng ký; người học đồng ý 2026-11-02 |
| vLLM chỉ giải thích, không chạy; module 20 dùng llama.cpp server và Ollama | Xung đột phụ thuộc `transformers` |
| Bài portfolio GRPO dùng khung `\boxed{}` thay `<think>` | Model 0.5B gần như không theo tag (0–1.6%) |
| Capstone M04 (quantize) đứng trước M01; M01–M03 sau module 13 | M04 không phụ thuộc RAG; M01 cần BM25 và thước đo của module 13 |

## 5. Việc còn ngỏ (không chặn)

- Một số số đo thời gian GPU ghi là đo khi GPU dùng chung; có thể đo lại khi máy rảnh.
- Module 13: bảng judge local `qwen2.5:3b`/`7b` của Advanced 01 chưa đo (bảng hiện tại chấm qua OmniRoute).
- Module 18: có MC-OCR thì đổi theo hướng dẫn trong bài (chuẩn hoá Unicode cho tên tiếng Việt).
- Module 20: server của llama-cpp-python cần `uv run --with "starlette-context==0.5.1"`; có thể thêm vào nhóm `llama`.
- Bản tham chiếu Advanced và capstone không nằm trong repo; muốn kiểm lại thì viết lại, với capstone thì chạy test bằng
  `LEGAL_ASSISTANT_SRC=<thư mục bản của bạn>`.
- Phụ thuộc ghim theo quy tắc "phát hành ≥ 2 tuần" (`constraint-dependencies` trong `pyproject.toml` và `setup/gpu`); xem lại
  rồi `uv lock --upgrade` khi cần.

## 6. Bài học khi soạn tiếp (đã ghi vào `module-implementer.md`)

- Không đáp án quiz nào được đọc ra từ lý thuyết, interview, README bài, starter hay đề quiz khác.
- Câu `data` phải bền khi chạy lại: không dựa vào một điểm của một seed hay biên nhỏ hơn độ dao động.
- Bài debug không được nêu tên bug ở bất cứ đâu, kể cả assert message.
- Mọi con số và kết luận nhân quả phải có log; đọc lại bảng của chính mình trước khi viết câu tổng kết.
- Máy dùng chung với người học: `nice`, ghim core, mỗi agent một job nặng, ưu tiên GPU.
