---
title: Benchmark trung thực và memo "có nên đầu tư quantum ML không"
level: advanced
services: []
files:
  - path: starter/benchmark.ipynb
    note: 3 hàm TODO, thí nghiệm tự thiết kế
  - path: starter/MEMO.md
    note: Memo cho CTO
  - path: tests/test_benchmark.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/22-quantum-ml/exercises/advanced/01-honest-benchmark/starter/benchmark.ipynb
  - uv run pytest tracks/ai-engineer/modules/22-quantum-ml/exercises/advanced/01-honest-benchmark -q
---

## Mục tiêu

Trả lời câu hỏi của CTO "có nên đầu tư quantum machine learning không" bằng một benchmark bạn tự thiết kế và một memo có số.
Bài gom mọi rào cản của mục 7 lý thuyết thành phép đo: barren plateau, dequantization, baseline mạnh có khoảng tin cậy, nhiễu
cộng shots. Kỹ năng thật sự được luyện là đánh giá trung thực một công nghệ đang được quảng cáo, dùng lại được cho bất kỳ
"model mới thần kỳ" nào.

## Đề bài

**Phần cứng:** CPU · ~240 phút

Thời gian trên là thời gian làm bài (thiết kế thí nghiệm, đọc kết quả, viết memo). Bản tham chiếu chạy hết thí nghiệm khoảng
2 phút: barren plateau vài giây, dequantization khoảng 15 giây, benchmark khoảng 15 giây, nhiễu với `default.mixed` khoảng 1
phút.

1. Trong `starter/benchmark.ipynb`, viết ba hàm được chấm (đặc tả chi tiết trong notebook):
   - `gradient_variance(n_qubits, n_layers, cost, n_samples=200, seed=0)`: phương sai của $$\partial C/\partial\theta_{0,0,0}$$ trên ansatz
     RY-RZ-CZ với tham số ngẫu nhiên, cost `"global"` ($$\langle Z_0 \cdots Z_{n-1}\rangle$$) hoặc `"local"` ($$\langle Z_0\rangle$$), bằng parameter-shift.
   - `angle_kernel_classical(XA, XB)`: kernel fidelity của angle embedding RY, tính bằng **công thức đóng** bạn tự suy ra.
   - `paired_ci(scores_a, scores_b, confidence=0.95)`: khoảng tin cậy Student-t cho chênh lệch theo cặp trên cùng fold.
2. Thí nghiệm (cell `explore`, tự viết):
   - **Barren plateau**: $$n = 2..10$$, $$L \in \{1, 5, 20\}$$, global và local; độ dốc của $$\log_2$$ phương sai theo $$n$$.
   - **Dequantization**: `angle_kernel_classical` khớp kernel PennyLane; thời gian theo số qubit (4 tới 16).
   - **Benchmark**: Iris, moons, breast cancer PCA-4; kernel ZZ, kernel angle (cổ điển), SVM RBF, logistic regression; 5-fold,
     **cùng ngân sách tuning**; mean ± std, thời gian, `paired_ci` của ZZ so với SVM RBF và so với kernel angle (ablation bỏ entanglement).
   - **Nhiễu + shots**: kernel ZZ trên moons 150 điểm với `default.mixed` và `DepolarizingChannel`, $$p \in \{0, 0.05\}$$, shots
     $$\{\infty, 100, 30\}$$; báo accuracy và độ tương phản kernel.
3. Viết `starter/MEMO.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một memo tốt** đọc trong 5 phút và người đọc dừng sau đoạn đầu vẫn quyết định được:

- **Khuyến nghị trước**, bằng chứng sau. "Không đầu tư; theo dõi bằng một thí nghiệm 3 ngày mỗi năm; xem lại khi ..." tốt hơn
  ba đoạn lịch sử cơ học lượng tử.
- **Mỗi khẳng định một con số** từ notebook của bạn, nói rõ con số đó đo trên simulator, bao nhiêu qubit, bao nhiêu fold.
- **Phân biệt "đo được" và "suy luận"**: "kernel ZZ không thắng RBF trên 3 bộ dữ liệu nhỏ" là đo được; "sẽ không thắng trên dữ
  liệu của chúng ta" là suy luận, cần lý do.
- **Công bằng với quantum**: nêu cả nơi nó ngang baseline, và điều kiện nào sẽ làm bạn đổi khuyến nghị.

## Tiêu chí đạt

- `gradient_variance`: một qubit cho phương sai 0.5 (±0.03); khớp từng mẫu với tính toán bằng PennyLane cho cả hai cost; cost global
  8 qubit thấp hơn 2 qubit ít nhất 16 lần với 5 layer; cost local 1 layer ở 8 qubit vẫn trên 0.3; tất định theo seed.
- `angle_kernel_classical` khớp statevector tới $$10^{-12}$$ và chạy được với 40 chiều.
- `paired_ci` đúng mean, std (ddof 1), khoảng Student-t; khoảng rộng ra khi tăng `confidence`.
- `MEMO.md` không còn TODO, ít nhất 500 từ, có các mục `## Khuyến nghị`, `## Bằng chứng`, `## Khi nào nên xem lại` và ít nhất một bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`gradient_variance` với 200 mẫu, 10 qubit, 20 layer: đừng gọi QNode 400 lần trong vòng lặp Python. Dựng simulator có thêm **trục
batch** đầu tiên (tensor shape `(B, 2, ..., 2)`, gate shape `(B, 2, 2)`, `np.einsum`), hoặc dùng parameter broadcasting của
PennyLane. CZ chỉ đổi dấu các biên độ có hai bit liền kề cùng bằng 1. Tham khảo bài Basic 01 cho quy ước wire.

### Gợi ý 2

Angle embedding là trạng thái tích, nên tích vô hướng tách thành tích của các tích vô hướng một qubit; viết
$$R_Y(a)|0\rangle$$ và $$R_Y(b)|0\rangle$$ ra rồi tính $$\langle \cdot|\cdot \rangle$$. "Cùng ngân sách tuning": nếu kernel lượng tử được chọn scale trong lưới
4 giá trị bằng alignment hoặc inner CV, thì RBF cũng được chọn gamma trong lưới cỡ đó bằng inner CV. Với `paired_ci`, nhớ
rằng các fold dùng chung dữ liệu train nên khoảng tin cậy hơi lạc quan; nói điều này trong memo.
