# Lời giải: quantum kernel ZZ, bandwidth, concentration và shots

Lời giải đầy đủ trong `qkernel.ipynb`. Số liệu: CPU, `OMP_NUM_THREADS=4`, PennyLane 0.45.1, scikit-learn 1.9.1, 5-fold stratified
`random_state=0`, SVM `C=1`.

## Cách làm

- **`feature_states`**: QNode trên `default.qubit` với $$n$$ wire, lặp `reps` lần khối [H, `RZ(X[:, w])` trên mỗi wire; với mỗi cặp kề:
  CNOT, `RZ(X[:, w] * X[:, w+1])` trên wire $$w+1$$, CNOT], trả `qml.state()`. Broadcasting cho shape `(B, 2**n)`. Khối CNOT–RZ–CNOT là
  $$e^{-i\phi Z_w Z_{w+1}/2}$$: CNOT đưa parity của hai bit vào wire $$w+1$$, RZ gắn pha theo parity, CNOT trả lại. `qml.IsingZZ` cho cùng
  trạng thái tới pha toàn cục (test so tới pha toàn cục nên cũng đạt).
- **`kernel_matrix`**: tính `SA`, `SB` một lần, `np.abs(SA.conj() @ SB.T) ** 2`. Cách này $$O((N_A + N_B)\,\text{chi phí mạch} + N_A N_B 2^n)$$
  thay vì $$N_A N_B$$ lần chạy mạch. Phần cứng không có lựa chọn này: không đọc được statevector, phải chạy $$U(b)^\dagger U(a)$$ cho từng cặp.
- **`kernel_target_alignment`**: $$H = I - \frac1m \mathbf{1}\mathbf{1}^\top$$, $$K_c = HKH$$, $$T_c = HTH$$, tích Frobenius chia hai chuẩn. Centering làm
  alignment bất biến khi cộng hằng vào $$K$$ (kernel concentration làm mọi phần tử gần một hằng; bản thô sẽ phản ánh hằng đó
  thay vì cấu trúc) và bớt lệch khi các lớp không cân bằng (Iris 3 lớp: 2/3 cặp khác lớp, bản thô ra âm ở 5 trong 6 scale đã thử, kể cả các scale tốt nhất).
- **`sample_kernel`**: `rng.binomial(shots, np.clip(K, 0, 1)) / shots`; clip vì statevector cho đường chéo $$1 + 10^{-16}$$.

## Kết quả

Iris (4 qubit): scale 0.3 và 0.5 cho test 0.953 (± 0.034 và ± 0.027), scale 4.0 tụt còn 0.400 dù train 0.902; SVM RBF 0.953 ± 0.016,
logistic 0.960 ± 0.013. Moons (2 qubit): tốt nhất 0.843 (scale 0.3), SVM RBF 0.970, logistic 0.847. Alignment đỉnh ở scale 0.5 (Iris,
0.723) và 0.1 (moons, 0.538): đúng vùng, không đúng từng điểm.

Concentration (breast cancer, scale 1.0): trung bình ngoài đường chéo 0.546 / 0.283 / 0.155 / 0.091 / 0.058 với 2 / 4 / 6 / 8 / 10 qubit;
train 0.899 → 0.993, test 0.888 → 0.819. Scale 0.3 giữ test 0.951–0.958 từ 4 tới 10 qubit, ngang SVM RBF (0.958–0.963). Thời gian
tăng nhanh theo $$2^n$$: 10 qubit mất khoảng 15–20 giây cho 5 fold, phần lớn thời gian chạy notebook.

Shots (Iris scale 0.5): 10 shots 0.900 ± 0.021, 100 shots 0.940 ± 0.013, 1000 shots 0.967 ± 0.037, chính xác 0.953 ± 0.027. Một fold là
$$120 \cdot 119/2 + 30 \cdot 120 = 10\,740$$ mạch.

## Trả lời câu hỏi cuối notebook

1. Iris: kernel ZZ chỉnh tốt **ngang** RBF, thua nhẹ logistic. Moons: thua RBF 13 điểm; feature map ZZ cố định không có lý do để
   hợp với dữ liệu, giống chọn sai kernel cổ điển.
2. Alignment chọn đúng vùng scale với chi phí một ma trận kernel, nhưng không thay được CV: nó đo độ khớp tuyến tính với nhãn,
   không đo margin của SVM.
3. Kernel tiến về ma trận đơn vị: mỗi điểm train chỉ "giống" chính nó, SVM thuộc lòng (train tăng), điểm test thì gần trực giao
   với mọi điểm train (test giảm).
4. Độ lệch chuẩn nhị thức $$\sqrt{k(1-k)/S}$$: với $$k \approx 0.65$$ và 100 shots là khoảng 0.048, cỡ khoảng cách giữa nhiều cặp phần tử, nên
   accuracy giảm vài điểm (0.953 → 0.940); 10 shots giảm 5 điểm.

## Bẫy thường gặp

- Bỏ `conj()`: vẫn ra số trong $$[0, 1]$$, ma trận vẫn đối xứng, nhưng không phải kernel đúng (test so với tham chiếu bắt được).
- Fit `StandardScaler` trên toàn bộ dữ liệu trước khi chia fold (rò rỉ); hoặc so quantum kernel đã chỉnh scale với RBF không chỉnh.
- Tính kernel từng cặp bằng QNode: $$N^2$$ lần chạy, chậm hàng trăm lần mà kết quả như nhau.
