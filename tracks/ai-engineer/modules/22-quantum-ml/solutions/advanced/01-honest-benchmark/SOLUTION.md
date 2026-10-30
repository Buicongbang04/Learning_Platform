# Hướng làm: benchmark trung thực và memo cho CTO

Bài không có một đáp án duy nhất: thiết kế benchmark và kết luận của memo là của bạn. Dưới đây là cách làm của bản tham
chiếu (chạy ngoài repo, CPU, `OMP_NUM_THREADS=4`, PennyLane 0.45.1, scikit-learn 1.9.1, scipy), các con số nó đo được để bạn
đối chiếu, và rubric chấm memo.

## Ba hàm được chấm

- **`gradient_variance`**: simulator numpy có **trục batch**: tensor `(B, 2, ..., 2)`, gate một qubit là mảng `(B, 2, 2)` áp bằng
  `np.einsum("bij,bj...->bi...")` sau khi `moveaxis` trục của wire lên vị trí 1; CZ là đổi dấu lát cắt có hai bit liền kề bằng 1.
  Rút `theta` một lần đúng đặc tả, dựng hai bản dịch $$\pm\pi/2$$ của `theta[:, 0, 0, 0]`, gradient là hiệu chia 2, trả `np.var`.
  Cost global nhân xác suất với $$\prod_w (\pm 1)$$, local chỉ với dấu của wire 0. 200 mẫu, 10 qubit, 20 layer chạy dưới 1 giây.
  Dùng QNode PennyLane trong vòng lặp cũng đúng nhưng chậm hơn hàng trăm lần.
- **`angle_kernel_classical`**: $$R_Y(a)|0\rangle = (\cos\frac a2, \sin\frac a2)$$, nên tích vô hướng một qubit là
  $$\cos\frac a2\cos\frac b2 + \sin\frac a2 \sin\frac b2 = \cos\frac{a - b}{2}$$, và kernel là $$\prod_w \cos^2\frac{a_w - b_w}{2}$$. Một dòng numpy với broadcasting
  `(N, 1, d) - (1, M, d)`. Đây là một kernel cổ điển: với $$d$$ nhỏ nó gần một kernel Gauss trên từng chiều.
- **`paired_ci`**: hiệu theo cặp, mean, `std(ddof=1)`, nửa độ rộng `stats.t.ppf((1 + c) / 2, K − 1) · std / sqrt(K)`.

## Số liệu của bản tham chiếu

**Barren plateau** (200 mẫu, seed 0; phương sai gradient của tham số đầu tiên):

| L | Cost | n = 2 | 4 | 6 | 8 | 10 | Độ dốc log2 / qubit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | global | 2.40e-01 | 7.05e-02 | 1.40e-02 | 3.16e-03 | 7.58e-04 | −1.05 |
| 1 | local | 4.79e-01 | 5.16e-01 | 4.50e-01 | 4.62e-01 | 5.01e-01 | −0.00 |
| 5 | global | 1.28e-01 | 2.56e-02 | 5.68e-03 | 1.46e-03 | 5.08e-04 | −1.00 |
| 5 | local | 1.63e-01 | 1.32e-01 | 1.40e-01 | 1.54e-01 | 1.33e-01 | −0.02 |
| 20 | global | 1.51e-01 | 3.18e-02 | 7.18e-03 | 2.02e-03 | 5.10e-04 | −1.02 |
| 20 | local | 1.49e-01 | 3.37e-02 | 1.50e-02 | 1.21e-02 | 1.23e-02 | −0.43 |

Đọc: cost global giảm khoảng một nửa mỗi qubit thêm **ngay cả với 1 layer**; cost local với mạch nông không giảm; cost local
với mạch sâu (20 layer) bắt đầu giảm, đúng như Cerezo et al. (2021): plateau đến từ cả cost lẫn độ sâu. Một qubit: 0.496 (lý
thuyết 0.5).

**Dequantization** (300 điểm, góc đều trong $$[-\pi, \pi]$$): sai lệch tối đa với kernel statevector PennyLane cỡ $$10^{-15}$$ ở mọi $$d$$.
Thời gian simulator khoảng 0.003 / 0.012 / 0.37 / 2.1 / 9.2 giây với $$d$$ = 4 / 8 / 12 / 14 / 16; công thức đóng 11 tới 40 ms (ở $$d$$ nhỏ
công thức đóng còn chậm hơn simulator vì broadcasting $$N^2 d$$, điều đáng ghi trung thực).

**Benchmark** (5-fold; kernel ZZ và angle chọn scale trong {0.1, 0.3, 0.5, 1.0} bằng centered alignment trên fold train; RBF chọn
gamma trong {scale, 0.01, 0.1, 1, 10} bằng inner 3-fold CV):

| Dữ liệu | ZZ kernel | Angle kernel (cổ điển) | SVM RBF | Logistic | ZZ − RBF, CI 95% |
| --- | --- | --- | --- | --- | --- |
| Iris | 0.953 ± 0.027 | 0.960 ± 0.033 | 0.947 ± 0.027 | 0.960 ± 0.013 | +0.007 [−0.039, +0.052] |
| moons | 0.830 ± 0.046 | 0.847 ± 0.037 | 0.983 ± 0.021 | 0.847 ± 0.031 | −0.153 [−0.214, −0.092] |
| breast cancer PCA-4 | 0.958 ± 0.009 | 0.967 ± 0.015 | 0.960 ± 0.020 | 0.960 ± 0.018 | −0.002 [−0.025, +0.022] |

ZZ không thắng ngoài khoảng tin cậy ở đâu, thua rõ ở moons, và không hơn kernel angle tính cổ điển (ZZ − angle âm ở cả ba bộ,
khoảng tin cậy chứa 0): entanglement không mang lại gì đo được ở đây, đúng phát hiện của Bowles et al. (2024).

**Nhiễu + shots** (moons 150 điểm, scale 0.3, depolarizing sau mỗi khối, 5-fold):

| p | Shots | Test acc | Trung bình đường chéo | Trung bình ngoài đường chéo |
| --- | --- | --- | --- | --- |
| 0 | ∞ | 0.820 ± 0.062 | 1.000 | 0.920 |
| 0 | 100 | 0.813 ± 0.072 | 1.000 | 0.920 |
| 0.05 | ∞ | 0.820 ± 0.062 | 0.620 | 0.584 |
| 0.05 | 100 | 0.793 ± 0.077 | 0.621 | 0.584 |

Đọc: depolarizing gần như là phép co affine về kernel hằng, SVM gần như bất biến với nó nên accuracy không đổi khi không có shots;
nhưng độ tương phản (đường chéo trừ ngoài đường chéo) giảm từ 0.080 còn 0.036, nên cùng số shots thì sai số tương đối lớn gấp
đôi. Mạch sâu hơn hoặc nhiều qubit hơn thì co mạnh hơn theo hàm mũ (noise-induced barren plateau). Mọi chênh lệch accuracy ở bảng
này nằm trong độ lệch chuẩn giữa fold: phải nói vậy, không viết "nhiễu làm giảm 2.7 điểm".

## Các quyết định thiết kế cần cân nhắc

- **Ngân sách tuning như nhau** cho mọi model, và tiền xử lý fit trong fold train.
- **Khoảng tin cậy theo cặp** trên cùng fold, kèm lưu ý rằng các fold dùng chung dữ liệu train nên t-test hơi lạc quan (Nadeau và
  Bengio đề xuất hiệu chỉnh); với 5 fold, khoảng rất rộng: "không phân biệt được" là kết luận hợp lệ.
- **Ablation**: kernel angle (không entanglement) là đối chứng tự nhiên cho kernel ZZ.
- **Chi phí** trong cùng bảng: thời gian simulator, và số mạch, số shots nếu chạy phần cứng.
- **Tách simulator và phần cứng**: mọi con số là trần trên; nhiễu và shots chỉ có thể làm tệ hơn.

## Một memo tốt trông thế nào

Đoạn đầu kiểu: "Khuyến nghị: không đầu tư vào QML cho bài toán phân loại hiện tại. Trên 3 bộ dữ liệu, kernel lượng tử tốt nhất
không thắng SVM RBF ở đâu (khoảng tin cậy chứa 0 ở Iris và breast cancer, thua 15 điểm ở moons), không hơn chính phiên bản cổ điển
của nó, và mọi kết quả đo trên simulator không nhiễu, tức trường hợp tốt nhất. Đề xuất theo dõi bằng một benchmark cố định chạy lại
mỗi năm (khoảng 3 ngày công); xem lại khi có kết quả độc lập cho thấy mô hình lượng tử trên phần cứng thật thắng baseline tuning
trên dữ liệu cổ điển, hoặc khi công ty có bài toán dữ liệu lượng tử." Phần bằng chứng có bảng benchmark, độ dốc barren plateau,
dequantization, nhiễu; phần giới hạn nói rõ dữ liệu nhỏ, ít qubit, simulator, mô hình nhiễu đơn giản.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Ba hàm qua test; `MEMO.md` đủ mục, đủ dài, có bảng |
| Benchmark công bằng | 25 | 3 bộ dữ liệu, 4 model, cùng fold, cùng ngân sách tuning, tiền xử lý trong fold, mean ± std và khoảng tin cậy theo cặp; có ablation kernel angle |
| Rào cản đo bằng số | 20 | Bảng barren plateau với độ dốc; dequantization có sai lệch và thời gian; nhiễu + shots có độ tương phản, không chỉ accuracy |
| Memo: khuyến nghị và lập luận | 25 | Khuyến nghị ở đoạn đầu; mỗi khẳng định có số hoặc trích dẫn; phân biệt đo được và suy luận; công bằng với quantum (nêu chỗ ngang baseline) |
| Khi nào xem lại | 15 | Tiêu chí cụ thể, kiểm được (phần cứng, kết quả độc lập, loại dữ liệu) và cách theo dõi có chi phí |

Đạt từ 70 điểm. Memo kết luận "quantum tốt hơn" hoặc "quantum vô dụng" mà không có khoảng tin cậy và baseline được tuning không quá
40 điểm, dù số liệu đúng.
