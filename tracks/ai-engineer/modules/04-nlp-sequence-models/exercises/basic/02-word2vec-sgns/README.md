---
title: word2vec skip-gram negative sampling bằng numpy
level: basic
services: []
files:
  - path: starter/word2vec.py
    note: 6 hàm TODO
  - path: tests/test_word2vec.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/basic/02-word2vec-sgns -q
---

## Mục tiêu

Viết các mảnh của word2vec skip-gram với negative sampling (SGNS) bằng numpy: vocab, subsampling, phân phối nhiễu,
sinh cặp, bước SGD có gradient tự suy, và tìm láng giềng. Làm xong bạn biết chính xác mỗi bước train chạm vào dòng nào
của hai ma trận embedding, và vì sao một lỗi cập nhật nhỏ làm word2vec học kém mà không báo lỗi.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/word2vec.py` (chỉ numpy), ký hiệu như mục 3 phần lý thuyết: `W_in` (vector $$v$$ của từ trung tâm) và
`W_out` (vector $$u$$ của từ ngữ cảnh), cùng shape `(V, d)`. Viết:

1. `build_vocab(tokens, min_count)`: bỏ từ xuất hiện dưới `min_count` lần, id theo tần suất giảm dần, hoà thì theo chữ
   cái. Trả `(word2id, counts)`.
2. `keep_probs(counts, t)`: xác suất **giữ** khi subsample, $$\min\left(1, \left(\sqrt{f/t} + 1\right) t / f\right)$$ với
   $$f$$ là tần suất tương đối.
3. `noise_distribution(counts, power=0.75)`: $$P_n(w) \propto \text{count}(w)^{0.75}$$.
4. `skipgram_pairs(ids, window)`: mọi cặp `(center, context)` trong một câu với khoảng cách 1 tới `window`, thứ tự theo
   center rồi theo context.
5. `sgns_step(W_in, W_out, centers, contexts, negatives, lr) -> float`: loss **trung bình** trên batch
   $$-\log\sigma(u_o^\top v_c) - \sum_k \log\sigma(-u_k^\top v_c)$$ (tính trước khi cập nhật, ổn định số với điểm cỡ 1000),
   rồi một bước SGD sửa tại chỗ chỉ các dòng liên quan. Cùng một từ có thể xuất hiện nhiều lần trong batch (làm center
   hai lần, vừa là context vừa là negative): gradient phải **cộng dồn**.
6. `most_similar(W, word2id, word, k)`: `k` từ có **cosine** cao nhất, bỏ chính từ đó.

## Tiêu chí đạt

- `build_vocab`, `keep_probs`, `noise_distribution`, `skipgram_pairs` đúng các ví dụ số trong test.
- `sgns_step` khớp loss và một bước SGD của `torch.autograd` (`atol=1e-12`) trên batch có center, context, negative trùng
  nhau.
- Điểm cỡ ±1800 cho loss hữu hạn, không cảnh báo tràn số.
- `most_similar` dùng cosine, không dùng tích vô hướng.
- Train 3 epoch trên corpus hai chủ đề (món ăn, thể thao) sinh trong test: loss giảm, 5 láng giềng của "phở" đều là món
  ăn.

## Gợi ý

### Gợi ý 1

$$\log\sigma(x) = -\log(1 + e^{-x})$$ = `-np.logaddexp(0, -x)`: không bao giờ tràn. Gradient theo điểm $$s = u^\top v$$ của
$$-\log\sigma(s)$$ là $$\sigma(s) - 1$$, của $$-\log\sigma(-s)$$ là $$\sigma(s)$$; nhân với vector bên kia là ra gradient theo
$$v$$ và $$u$$ (mục 3 lý thuyết). Nhớ chia cho B vì loss là trung bình.

### Gợi ý 2

`W_in[centers] -= lr * dv` với `centers = [0, 0, 3]` chỉ áp **một** trong hai cập nhật của dòng 0 (fancy indexing gán,
không cộng). Dùng `np.add.at(W_in, centers, -lr * dv)`. Với negative shape `(B, K)`, làm phẳng chỉ số thành `(B*K,)` và
gradient thành `(B*K, d)`. Tính mọi gradient từ giá trị **trước** cập nhật rồi mới sửa ma trận.
