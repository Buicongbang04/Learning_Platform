---
title: Rerank top-50 hybrid bằng cross-encoder bge-reranker-v2-m3
level: intermediate
services: []
files:
  - path: starter/rerank.ipynb
    note: 2 hàm TODO
  - path: tests/test_rerank.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - uv run jupyter lab tracks/ai-engineer/modules/13-rag/exercises/intermediate/03-reranking/starter/rerank.ipynb
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/intermediate/03-reranking -q
---

## Mục tiêu

Thêm tầng rerank vào sau hybrid retrieval của bài 01 bằng cross-encoder mở `BAAI/bge-reranker-v2-m3`, viết sao cho
test được không cần model, và đo bằng số cái giá của nó: MRR@10 tăng bao nhiêu, độ trễ mỗi câu trên CPU là bao nhiêu,
và chọn số ứng viên rerank theo ngân sách độ trễ.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Ngoài thời gian làm bài: lần đầu tải model khoảng 2.3 GB từ Hugging Face; rerank 100 câu × 50 ứng viên trên CPU của
laptop track mất khoảng 60 phút, 35 giây một câu (điểm được cache ở `data/raw/zalo-legal/cache/`, chạy lại chỉ vài giây). Có GPU
và kernel notebook chạy PyTorch CUDA có `sentence-transformers` thì đặt `DEVICE = "cuda"`: phần lý thuyết đo nhanh hơn khoảng 24 lần (môi trường gốc dùng PyTorch CPU). Cần
`cache/hybrid-top100.json` do bài 01 ghi ra: làm bài 01 trước. `sentence-transformers` đã có trong môi trường gốc
(`uv sync`), không cần Ollama.

Mở `starter/rerank.ipynb`. Trong cell chấm điểm:

1. `rerank(query, candidates, score_fn, top_n) -> list[Article]`: chấm cả danh sách bằng **một** lần gọi
   `score_fn(query, texts)` (văn bản là `"<title>\n<text>"`), trả `top_n` ứng viên điểm cao nhất; bằng điểm giữ thứ tự
   cũ của retrieval.
2. `cross_encoder_score_fn(model_name="BAAI/bge-reranker-v2-m3", device="cpu", max_length=512, batch_size=16)`: trả
   hàm chấm dùng `sentence_transformers.CrossEncoder`, **nạp lười**: không import, không tải gì cho tới lần chấm đầu
   tiên, rồi dùng lại model.

Rồi chạy các cell `explore`: thử trên một câu, rerank top-50 hybrid của 100 câu đầu tập ghim, in bảng MRR@10, R@1,
R@5, R@10 trước và sau, độ trễ trung vị và p95, số câu lên hạng và tụt hạng, và kết quả khi chỉ rerank top-10, top-20.
Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `rerank` với `score_fn` giả: đúng thứ tự giảm dần, gọi `score_fn` đúng một lần với `"title\ntext"`, `top_n` cắt
  đúng (lớn hơn số ứng viên thì trả hết), bằng điểm giữ thứ tự cũ, nhận cả mảng numpy, danh sách rỗng không gọi
  `score_fn`.
- `cross_encoder_score_fn` (thay `sentence_transformers` bằng module giả trong test): tạo hàm không nạp model; lần chấm
  đầu tạo đúng một `CrossEncoder(model_name, device=..., max_length=...)`, lần sau dùng lại; trả `list[float]`.
- Cell `explore` chạy hết và in bảng trước/sau trên 100 câu.

## Gợi ý

### Gợi ý 1

`sorted(range(n), key=...)` của Python là sort ổn định: các phần tử bằng khoá giữ thứ tự ban đầu. Đổi điểm sang
`float` trước khi sort để mảng numpy hay list đều dùng được như nhau.

### Gợi ý 2

Nạp lười là một closure: hàm ngoài chỉ lưu tham số và một biến `model = None`; hàm trong (dùng `nonlocal`) tạo model
khi biến đó còn `None`. Đặt câu `import` vào trong hàm trong.
