---
title: Quantum kernel ZZ, bandwidth, concentration và shots
level: intermediate
services: []
files:
  - path: starter/qkernel.ipynb
    note: 4 hàm TODO
  - path: tests/test_qkernel.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/22-quantum-ml/exercises/intermediate/02-quantum-kernel/starter/qkernel.ipynb
  - uv run pytest tracks/ai-engineer/modules/22-quantum-ml/exercises/intermediate/02-quantum-kernel -q
---

## Mục tiêu

Dựng một quantum kernel từ feature map ZZ, đưa vào SVM cổ điển, và thấy bằng số bốn điều quyết định nó có dùng được không:
bandwidth, kernel-target alignment, concentration khi thêm qubit, và sai số do shots, so với SVM RBF và logistic regression
trên cùng fold.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Thời gian trên là thời gian làm bài. Chạy cả notebook lời giải khoảng 50 giây (phần lớn ở bảng concentration với 10 qubit).

Mở `starter/qkernel.ipynb`. Iris, moons, breast cancer đều có sẵn trong scikit-learn.

1. `feature_states(X, reps=2)`: statevector của feature map ZZ mô tả trong notebook cho từng hàng của `X`, shape `(B, 2**n)`,
   dùng PennyLane `qml.state()` với parameter broadcasting.
2. `kernel_matrix(XA, XB, reps=2)`: $$|\langle\varphi(a_i)|\varphi(b_j)\rangle|^2$$, tính statevector một lần cho mỗi tập rồi nhân ma trận.
3. `kernel_target_alignment(K, y)`: centered alignment (công thức trong notebook, Cortes et al. 2012).
4. `sample_kernel(K, shots, rng)`: giả lập ước lượng mỗi phần tử bằng shots (nhị thức).

Rồi chạy các cell `explore`: quét scale trên Iris và moons, bảng concentration trên breast cancer với 2 tới 10 qubit, và kernel
từ 10/100/1000 shots. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `feature_states` khớp mạch ZZ viết tay bằng numpy (tới pha toàn cục) với $$n = 1, 2, 3$$ và `reps` 1, 2; mỗi hàng chuẩn hoá.
- `kernel_matrix` khớp tham chiếu với hai tập khác cỡ; với cùng một tập thì đối xứng, đường chéo 1, nửa xác định dương, giá trị trong $$[0, 1]$$.
- Alignment bằng 1 với kernel lý tưởng, không đổi khi cộng hằng số hay nhân hệ số vào `K`, âm với kernel ngược nhãn.
- `sample_kernel` cho bội số của `1/shots`, trung bình và độ lệch chuẩn đúng phân phối nhị thức, chịu được phần tử lệch nhẹ trên 1, tất định theo `rng`.
- Cell `explore` in ra các bảng ở mục 6 lý thuyết (vd. Iris scale 0.5: test 0.953 ± 0.027; breast cancer 10 qubit, scale 1.0:
  trung bình ngoài đường chéo 0.058, test 0.819).

## Gợi ý

### Gợi ý 1

$$\langle a|b\rangle = \sum_k \overline{a_k} b_k$$: với hai ma trận statevector `SA` (hàng là trạng thái) và `SB`, mọi tích vô hướng là một phép nhân
ma trận, nhớ liên hợp phía bên trái. Bỏ liên hợp vẫn ra số, chỉ là sai.

### Gợi ý 2

Centering: $$H = I - \frac{1}{m}\mathbf{1}\mathbf{1}^\top$$ là `np.eye(m) - np.ones((m, m)) / m`; $$HKH$$ trừ trung bình hàng và cột của $$K$$. Chuẩn
Frobenius là `np.linalg.norm(K)`. `rng.binomial(shots, p)` nhận cả mảng `p`, nhưng báo lỗi nếu có phần tử lớn hơn 1 dù chỉ $$10^{-16}$$.
