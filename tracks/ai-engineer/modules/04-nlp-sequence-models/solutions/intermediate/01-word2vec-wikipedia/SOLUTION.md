# Lời giải: word2vec trên Wikipedia tiếng Việt

## Cách làm

**Corpus.** Shard `train-00001-of-00004` có 322 170 bài, phần lớn là bài sơ khai do bot tạo (trung vị 176 ký tự). Lọc
bài từ 2 000 ký tự (9 160 bài) rồi `sample(n=5000, random_state=0)`: lấy ngẫu nhiên thay vì 5 000 bài đầu, vì bài trong
shard xếp theo chủ đề và 3 000 bài dài đầu tiên lệch hẳn về vài chủ đề (cụm `bột_hải` lọt top 20). `tokenize` cắt câu
trước rồi mới lấy âm tiết, để cặp skip-gram và cụm không vượt qua dấu chấm.

**Cụm.** Đếm unigram, bigram trong từng câu, điểm $$(\text{count}(ab) - \delta)N / (\text{count}(a)\text{count}(b))$$.
`delta` loại cặp hiếm có điểm cao do may (hai tên riêng chỉ đi cùng nhau 3 lần). `apply_phrases` một lượt, tham lam từ
trái: `hà nội thành` thành `hà_nội thành`, không thành `hà nội_thành`.

**Cặp skip-gram vectorized.**

| Bước | numpy | Ghi chú |
| --- | --- | --- |
| subsample | `mask = rng.random(n) < keep[ids]` | gọi `rng` trước |
| cửa sổ động | `b = rng.integers(1, window + 1, len(a))` | một số cho mỗi token, dùng khi nó làm center |
| khoảng cách `d` | `same = s[:-d] == s[d:]`; phải: `same & (b[:-d] >= d)`; trái: `same & (b[d:] >= d)` | 2 × window phép mask |

Lặp Python từng token mất khoảng 70 giây mỗi epoch cho 5.3 triệu token (đo trên 200 000 token rồi nhân lên); bản mask khoảng 1.4 giây.

**Train.** `nn.Embedding(sparse=True)` cho gradient chỉ trên các dòng có mặt trong batch (giống `np.add.at` của Basic
02); `torch.optim.SGD` nhận gradient sparse. Loss trung bình nên lr của optimizer là `lr * batch_size`; lr per-cặp giảm
tuyến tính từ 0.025 về `1e-4` theo bước như mã C gốc. `in_emb` khởi tạo đều nhỏ, `out_emb` bằng 0: ở bước đầu mọi điểm
bằng 0, loss bằng $$(K + 1)\ln 2 = 4.16$$ với 5 negative.

## Kết quả thật

5 000 bài, 421 347 câu, 6 431 832 âm tiết. Ghép cụm: 13 077 cụm, còn 5 471 286 token. SGNS 100 chiều, window 5, 5
negative, subsample `1e-4`, batch 1 024, 3 epoch, seed 0, CPU 4 luồng:

| | Âm tiết | Ghép cụm |
| --- | --- | --- |
| Vocab (count ≥ 5) | 24 305 | 33 760 |
| Cặp mỗi epoch | 14.4 triệu | 12.9 triệu |
| Loss epoch 1 / 2 / 3 | 2.526 / 2.295 / 2.251 | 2.607 / 2.294 / 2.233 |
| Thời gian (máy rảnh / máy bận) | khoảng 2.5 phút / 13 phút | khoảng 2 phút / 10.5 phút |

Láng giềng và analogy: bảng ở mục 3 lý thuyết. Analogy nước–thủ đô 31/272 (0.114), giới tính 13/72 (0.181);
`pháp : paris :: đức : ?` cho `berlin` ở vị trí 1.

Đọc kết quả:

- Loss của hai model gần bằng nhau nhưng **không so được**: hai vocab khác nhau, bài toán dự đoán khác nhau. Đánh giá
  embedding bằng tác vụ (láng giềng, analogy, hoặc tốt nhất là bài toán downstream), không bằng loss.
- Ghép cụm cho vocab lớn hơn và ít token hơn; láng giềng của `mèo`, `đỏ`, `sông` có nghĩa hơn. Không ghép cụm, vector của
  `hà` là trung bình của mọi tên riêng chứa "hà".
- Analogy 11-18% là thấp nhưng đúng kỳ vọng với 5 triệu token. Muốn hơn: nhiều dữ liệu hơn (cả 4 shard), nhiều epoch,
  hoặc tách từ bằng công cụ thay cho ngưỡng PMI (bắt được `trung_quốc`).

## Bẫy thường gặp

- Không cắt câu: cặp skip-gram và cụm vượt qua dấu chấm, ghép cuối câu này với đầu câu sau (vd. "tham khảo" cuối bài với dòng đầu của mục tiếp theo).
- Cửa sổ động gắn với context thay vì center: vẫn chạy, nhưng phân phối khoảng cách lệch so với word2vec gốc.
- Quên `sparse=True`: mỗi bước SGD đụng cả ma trận 33 760 × 100, chậm hơn nhiều lần.
- So láng giềng bằng tích vô hướng: toàn từ phổ biến (`của`, `là`) vì vector của chúng dài.
- Đánh giá analogy mà để `a`, `b`, `c` trong kết quả: thường thì đáp án top 1 chính là `c`.
