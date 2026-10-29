---
title: Phân loại review Olist bằng embedding
level: intermediate
services: []
files:
  - path: starter/review_embeddings.ipynb
    note: 6 TODO (load_reviews, time_split có sẵn)
  - path: tests/test_review_embeddings.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/13-deep-learning/exercises/intermediate/03-olist-review-embeddings/starter/review_embeddings.ipynb
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/intermediate/03-olist-review-embeddings -q
---

## Mục tiêu

Đi trọn đường từ văn bản thô tiếng Bồ Đào Nha tới một model embedding bằng PyTorch, rồi làm việc
mà một DS senior luôn làm: so với một baseline đơn giản và trả lời trung thực "deep learning có đáng
không ở đây". Hiểu embedding của một model phân loại học được gì và không học được gì.

## Đề bài

Mở `starter/review_embeddings.ipynb`. `load_reviews` và `time_split` đã viết sẵn theo định nghĩa
chung của track (đơn giao xong, review mới nhất mỗi đơn, review xấu là điểm ≤ 2, chia theo ngày mua).

1. `tokenize(text)`: chữ thường, bỏ dấu (NFKD + bỏ ký tự combining), lấy các cụm `[a-z]+`.
2. `build_vocab(texts, min_freq=2, max_size=None)`: `<pad>` = 0, `<unk>` = 1, rồi từ theo tần suất
   giảm dần (hoà thì theo chữ cái); `max_size` tính cả hai token đặc biệt.
3. `encode(texts, vocab, max_len)`: ma trận id, cắt bớt, đệm 0, từ lạ thành 1.
4. `BagOfEmbeddings(vocab_size, dim)`: thuộc tính `embedding` và `out = nn.Linear(dim, 1)`; logits là
   `out(trung bình embedding các token khác 0)`.
5. `train_text_model(...)`: Adam + `BCEWithLogitsLoss`, early stopping theo val loss và khôi phục
   trọng số tốt nhất (quy tắc như bài Basic 02).
6. `nearest_words(weight, vocab, word, k)`: k từ gần nhất theo cosine, bỏ chính nó, `<pad>`, `<unk>`.

Chạy các cell `explore`: so model với TF-IDF + logistic regression trên validation và test, xem
hàng xóm gần nhất trong embedding, rồi trả lời ba câu hỏi ở cuối.

## Tiêu chí đạt

- `tokenize("Não GOSTEI!! produto péssimo, 2x") == ["nao", "gostei", "produto", "pessimo", "x"]`.
- Vocabulary đúng thứ tự, đúng `min_freq`, `max_size`; `encode` đúng cắt, đệm, `<unk>`.
- `BagOfEmbeddings` bằng đúng trung bình có mask rồi qua `out`; thêm cột padding không đổi kết quả;
  dòng toàn padding cho logits bằng bias.
- Trên review giả, model đạt AUC test trên 0.97, `best_epoch` là epoch có val loss nhỏ nhất và model
  trả về mang đúng trọng số đó; cùng seed cho cùng loss.
- `nearest_words` dùng cosine (không phải tích vô hướng), báo `KeyError` với từ lạ.
- Trên Olist thật: 38 872 review có lời bình (train 17 883, validation 8 562, test 12 427), tỉ lệ
  xấu 23.75%, vocabulary train với `min_freq=2` có 4 341 mục.

## Gợi ý

### Gợi ý 1

`nn.EmbeddingBag(vocab_size, dim, mode="mean", padding_idx=0)` nhận thẳng ma trận `(N, L)` và tính
trung bình bỏ qua padding, dòng toàn padding cho vector 0. Nếu dùng `nn.Embedding`, tự làm mask:
`m = (ids != 0).float()`, tổng `(emb * m[..., None]).sum(1)` chia `m.sum(1, keepdim=True).clamp(min=1)`.

### Gợi ý 2

Cosine: chuẩn hoá mọi hàng bằng `torch.nn.functional.normalize(weight, dim=1)`, nhân với vector của
từ cần tìm, đặt điểm của `<pad>`, `<unk>` và chính nó bằng `-inf`, rồi `topk`.
