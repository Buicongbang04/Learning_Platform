---
title: Self-consistency, best-of-N và pass@k
level: basic
services: []
files:
  - path: starter/voting.py
    note: 6 hàm TODO
  - path: tests/test_voting.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/basic/02-voting-pass-at-k -q
---

## Mục tiêu

Test-time compute biến **nhiều lời giải** thành **một đáp số**: bỏ phiếu (self-consistency), bỏ phiếu có trọng số, hay
chọn lời giải được verifier chấm cao nhất (best-of-N). Muốn so các cách đó thì cần thước đo đúng: maj@k cho cách bỏ phiếu,
pass@k cho trần "chỉ cần một lời giải đúng". Bài này viết cả hai nửa; bài Intermediate 01 dùng chúng để vẽ đường cong
độ chính xác theo ngân sách token.

## Đề bài

**Phần cứng:** CPU · ~40 phút

Đọc mục 2 lý thuyết. Trong `starter/voting.py` (chỉ thư viện chuẩn), đáp số là chuỗi đã chuẩn hoá (bài 01) hoặc `None`
khi không đọc được:

1. `majority_vote(answers)`: đáp số xuất hiện nhiều nhất; `None` không phải một phiếu; hoà thì lấy đáp số **xuất
   hiện sớm nhất** trong danh sách; danh sách rỗng hoặc toàn `None` thì `None`.
2. `weighted_vote(answers, weights)`: như trên với tổng trọng số thay cho số phiếu. Hai danh sách khác độ dài thì
   `ValueError`.
3. `best_of_n(answers, scores)`: đáp số của lời giải có điểm cao nhất (kể cả khi đáp số đó là `None`); hoà thì lời giải
   đứng trước; rỗng thì `None`; khác độ dài thì `ValueError`.
4. `pass_at_k(n, c, k)`: ước lượng không chệch của Chen và cộng sự (2021) cho xác suất có ít nhất một lời giải đúng
   trong `k` lời giải **khác nhau** rút từ `n` lời giải, trong đó `c` lời giải đúng:
   $$\text{pass@}k = 1 - \binom{n-c}{k} \Big/ \binom{n}{k}$$.
   Tính sao cho không tràn số với `n = 1000`, trả `float`. Cần `0 <= c <= n`, `1 <= k <= n`, ngược lại `ValueError`.
5. `maj_at_k(samples, golds, k)`: `samples[i]` là các đáp số của câu `i`. Chia lời giải của mỗi câu thành các khối `k`
   **liên tiếp** không chồng nhau (bỏ phần dư không đủ một khối), bỏ phiếu trong từng khối, tỉ lệ khối đúng là điểm của
   câu đó; trả trung bình theo câu. Câu nào có ít hơn `k` lời giải thì `ValueError`.
6. `coverage_at_k(samples, golds, k)`: trung bình `pass_at_k` theo câu.

## Tiêu chí đạt

- Hoà trong bỏ phiếu theo thứ tự xuất hiện (`["2", "10", "1"]` cho `"2"`), `None` không được tính.
- `pass_at_k` khớp phép đếm mọi tập con trên 7 bộ `(n, c, k)`, ổn định với `n = 1000`, khác công thức "có hoàn lại"
  $$1 - (1 - c/n)^k$$.
- `maj_at_k` đúng trên ví dụ tính tay (khối liên tiếp, bỏ khối thiếu, hoà).
- Trên dữ liệu mô phỏng (đáp án đúng 45%, đáp án sai phân tán), maj@16 vượt 0.95.

## Gợi ý

### Gợi ý 1

`dict` của Python giữ thứ tự chèn: đếm vào một `dict` theo thứ tự duyệt thì "đáp số xuất hiện sớm nhất" là khoá đầu
tiên đạt giá trị lớn nhất. Viết `weighted_vote` trước, `majority_vote` là trường hợp mọi trọng số bằng 1.

### Gợi ý 2

$$\binom{n-c}{k} / \binom{n}{k}$$ viết được thành tích của các thừa số dạng $$1 - k/i$$, mỗi thừa số trong (0, 1], nên không
bao giờ tràn. Kiểm lại công thức của bạn bằng cách liệt kê mọi tập con với `n` nhỏ (`itertools.combinations`).
