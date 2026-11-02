---
title: Entanglement bằng SVD và ước lượng từ shots
level: basic
services: []
files:
  - path: starter/entanglement.py
    note: 6 hàm TODO
  - path: tests/test_entanglement.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/22-quantum-ml/exercises/basic/02-entanglement-shots -q
---

## Mục tiêu

Đo entanglement bằng đúng công cụ đại số tuyến tính bạn đã biết (SVD), và đọc kết quả đo nhiều qubit như một Data
Scientist đọc mẫu: phân phối biên, ước lượng kỳ vọng từ counts, và số shots cần cho một độ chính xác. Đây là hai thứ
quyết định một mô hình lượng tử có khác mô hình cổ điển không, và nó tốn bao nhiêu để chạy.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/entanglement.py` (chỉ dùng numpy; trạng thái là vector complex dài $$2^n$$, wire 0 là bit trái; nhóm A là
`n_a` wire đầu, B là phần còn lại):

1. `bell_state(kind)`: `"phi+"`, `"phi-"`, `"psi+"`, `"psi-"` (công thức trong docstring), tên khác thì `ValueError`.
2. `schmidt_coefficients(state, n_a)`: singular value của ma trận hệ số $$2^{n_a} \times 2^{n - n_a}$$, giảm dần, bỏ giá trị dưới $$10^{-12}$$
   (mục 4 lý thuyết).
3. `entanglement_entropy(state, n_a)`: $$-\sum_k \lambda_k^2 \log_2 \lambda_k^2$$, đơn vị bit, float Python.
4. `marginal_probabilities(probs, wires)`: phân phối của các wire trong `wires` (theo đúng thứ tự đó, wire đầu là bit trái),
   cộng dồn mọi wire khác.
5. `expval_from_counts(counts, wires)`: ước lượng $$\langle Z_{w_1} Z_{w_2} \cdots\rangle$$ từ `{chuỗi bit: số lần}` (định dạng bài 01): trung bình
   của $$(-1)^{\text{tổng các bit tại wires}}$$.
6. `shots_for_std(target_std, expval=0.0)`: số shots **nhỏ nhất** để độ lệch chuẩn $$\sqrt{(1 - \langle P\rangle^2)/S}$$ không vượt `target_std`,
   kiểu `int` (mục 2 lý thuyết).

## Tiêu chí đạt

- Bốn Bell state đúng, đều có hai hệ số Schmidt $$1/\sqrt 2$$ và entropy 1 bit; trạng thái tích có một hệ số bằng 1, entropy 0.
- $$\cos t|00\rangle + \sin t|11\rangle$$ cho hệ số $$(\cos t, \sin t)$$ và entropy nhị phân của $$\cos^2 t$$; vị trí cắt (`n_a`) đổi kết quả đúng.
- Trạng thái ngẫu nhiên 5 qubit: $$\sum \lambda^2 = 1$$, entropy hai phía bằng nhau.
- Phân phối biên đúng, kể cả khi `wires` không theo thứ tự tăng; Bell state có biên đều nhưng phân phối chung tương quan.
- `expval_from_counts` đúng trên counts viết tay và không chệch trên 20 000 mẫu.
- `shots_for_std(0.01) == 10000`, `shots_for_std(0.1, expval=0.9) == 19`, sai số nhỏ đi 10 lần cần shots gấp 100.

## Gợi ý

### Gợi ý 1

`np.linalg.svd(M, compute_uv=False)` trả singular value đã sắp giảm dần. Phân phối biên: reshape `probs` thành tensor
`(2,) * n`, `sum` theo các trục không nằm trong `wires`. Kết quả có trục theo thứ tự tăng dần; nếu `wires` không tăng dần thì
cần `np.transpose`.

### Gợi ý 2

`shots_for_std`: $$S = \lceil (1 - \langle P \rangle^2)/\sigma^2 \rceil$$, nhưng phép chia số thực có thể lệch bit cuối (`0.91 / 0.002**2 = 227500.00000000003`), nên làm tròn
nhẹ trước khi `ceil` (ví dụ `round(x, 9)`). Trường hợp $$\langle P\rangle = \pm 1$$ không có phương sai: 1 shot là đủ.
