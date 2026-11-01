# Trợ lý pháp luật tiếng Việt

> README này là bản nháp cho repo portfolio của bạn. Viết lại dần sau mỗi milestone; sau M09, phần đầu trang là
> kiến trúc cuối cùng và bảng con số chính.

Hệ thống hỏi đáp pháp luật tiếng Việt chạy local: BM25 + embedding → RAG có trích dẫn điều, khoản → agent LangGraph →
guardrails → eval suite, trace, serving. Mọi con số truy được về một script chạy lại được trên 300 câu ghim của
Zalo Legal.

## Quick start

```bash
uv run python data/download_dataset.py zalo-legal
ollama pull bge-m3 && ollama pull qwen2.5:3b
export PYTHONPATH=tracks/ai-engineer/capstone/project
uv run pytest tracks/ai-engineer/capstone/project/tests -q -rs
```

Lúc đầu mọi test **skip** với lời nhắc `Chưa làm: M0x: <hàm>`: package chỉ có khung hàm. Viết xong hàm nào, test của
hàm đó chạy thật. Test dùng bộ luật tí hon hư cấu ở `tests/fixtures/mini-legal/` và `llmkit.FakeLLM`, không cần mạng,
GPU hay Ollama; riêng `test_pinned_set_on_real_data` skip khi chưa tải `zalo-legal`.

Capstone không có lời giải mẫu trong repo, nên `SOLUTION=1` skip cả thư mục. Khi tách ra repo portfolio, chạy test trên
code của repo đó bằng `LEGAL_ASSISTANT_SRC=<thư mục chứa legal_assistant/>`.

## Package `legal_assistant/`

| Tệp | Milestone | Nội dung |
| --- | --- | --- |
| `text.py` | M01 | `normalize`, `tokenize` (âm tiết, bigram tuỳ chọn), `split_uid` |
| `data.py` | M01 | `Article`, `Question`, `load_corpus`, `load_questions` (tập ghim = `load_questions(root, "test", 300)`) |
| `bm25.py` | M01 | `BM25` (chép lời giải module 13 cũng được) |
| `metrics.py` | M01 | `recall_at_k`, `mrr_at_k`, `ndcg_at_k`, `first_hit_rank` |
| `fusion.py` | M02 | `normalize_rows`, `dense_top_k`, `max_by_article`, `rrf` (có trọng số) |
| `chunking.py` | M03 | `Passage`, `split_clauses` (khoản, điểm, có nhãn địa chỉ) |
| `citations.py` | M03 | `REFUSAL`, `build_messages`, `parse_citations`, `is_refusal`, `cited_uids` |
| `rag.py` | M03 | `RagAnswer`, `answer` (cổng điểm + một lời gọi LLM) |
| `judge.py` | M03 | `judge_faithfulness`, `rag_summary` |
| `quant.py` | M04 | `bits_per_weight`, `pareto_front` |
| `finetune_data.py` | M05 | `check_no_leak`, `hard_negatives`, `training_pairs` |
| `agent.py` | M06 | `AgentState`, `merge_hits`, `parse_sub_questions`, `next_step` |
| `safety.py` | M07 | `looks_like_injection`, `mentioned_articles`, `fabricated_references`, `ground_or_refuse` |
| `evals.py` | M08 | `latency_summary`, `percentile_ci`, `cost_per_query`, `cohen_kappa`, `regression_gate` |
| `tracing.py` | M08 | `Tracer` tối giản (thay bằng OpenTelemetry khi làm thật) |

Đây là phần **thuần**, test được bằng fixture. Phần chạy trên dữ liệu thật (dựng index, gọi Ollama, vòng lặp đánh
giá, đồ thị LangGraph, server) là script và notebook của bạn, gọi các hàm trên chứ không chép lại logic.

## Cấu trúc gợi ý

```
project/
├── README.md
├── legal_assistant/       # code dùng chung, có test
├── scripts/               # m01_bm25.py, m02_retrieval.py, m03_rag.py, ... mỗi script in bảng và ghi log
├── notebooks/             # phân tích lỗi, biểu đồ (gọi hàm trong legal_assistant/)
├── reports/               # RETRIEVAL.md (M01–M02), RAG.md (M03), QUANT.md (M04), FINETUNE.md (M05),
│                          # AGENT.md (M06), SAFETY.md (M07), EVAL_OPS.md (M08), DESIGN.md (M09)
├── evalsets/              # câu hỏi tự viết: ngoài phạm vi, nhiều vế, thiếu dữ kiện, red-team (có phiên bản)
├── artifacts/             # index, vector cache, câu trả lời cache, trace: không commit
└── tests/                 # uv run pytest tracks/ai-engineer/capstone/project/tests -q -rs
```

Nguyên tắc:

- **Một tập đánh giá cho mọi so sánh**: 300 câu ghim của split test. Tham số (trọng số RRF, ngưỡng từ chối, số nguồn)
  chọn trên một tập dev lấy từ split train, rồi mới chạy một lần trên tập ghim.
- **Cache mọi thứ đắt** (vector, câu trả lời LLM, điểm judge) theo khoá (cấu hình, câu hỏi), và tách pha: retrieve hết
  rồi mới sinh, để Ollama không nạp lại model liên tục.
- **Mọi con số trong `reports/` có log**: lệnh, commit, model, phần cứng, ngày chạy.
- Thêm `artifacts/` vào `.gitignore` của repo portfolio. Không commit dữ liệu Zalo hay đoạn trích từ nó.

## Con số chính

_(Bảng: recall@10 và MRR@10 của retrieval tốt nhất, tỉ lệ trích đúng điều, faithfulness kèm kappa của judge, tỉ lệ
từ chối đúng và từ chối sai, tỉ lệ bịa điều luật, p50/p95 có khoảng tin cậy, chi phí mỗi 1 000 câu. Mỗi dòng link tới
script tạo ra nó.)_

## Decisions

_(Đơn vị retrieval và đơn vị trích dẫn, hybrid hay dense, có rerank không, ngưỡng từ chối chọn trên tập nào, mức
quantize, có fine-tune không, khi nào đi đường agent, lớp guardrail nào và vì sao.)_

## Giới hạn

_(Nhãn qrels chỉ một điều mỗi câu; corpus không có ngày hiệu lực; judge nhỏ; số đo độ trễ trên máy dùng chung.)_
