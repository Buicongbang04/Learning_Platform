# Lời giải: variational quantum classifier với parameter-shift tự viết

Lời giải đầy đủ trong `vqc.ipynb`. Số liệu: CPU, `OMP_NUM_THREADS=4`, PennyLane 0.45.1, seed ghi trong notebook.

## Cách làm

**`parameter_shift_jacobian`.** Copy `params` thành mảng float, gọi `f` một lần ở điểm gốc để biết shape output, rồi với mỗi
chỉ số (`np.ndindex`) dựng bản dịch $$+s$$ và $$-s$$ đúng một phần tử, ghi `(f+ − f−) / (2 sin s)` vào `jac[idx]`. Gán lại từ
`base[idx]` thay vì cộng trừ liên tiếp để không trôi số. Mẫu số $$2\sin s$$ chứ không phải 2: chỉ trùng nhau khi $$s = \pi/2$$, và test
dùng cả $$\pi/4$$ và 1.

**`make_vqc`.** Một QNode trên `default.qubit` 2 wire, nhận cả ma trận `X`; `qml.RY(X[:, w], wires=w)` kích hoạt
parameter broadcasting nên một lần chạy cho cả batch. Bọc trong `model(params, X)` trả `np.ndarray` float shape `(B,)`
(PennyLane có thể trả tensor của interface khác).

**`loss_and_grad`.** Jacobian của output theo tham số có shape `params.shape + (B,)`; gradient của MSE là
`jac @ (2 * (out − y) / B)`. Không gọi parameter-shift trên **loss** (vô hướng) vì loss không còn là hàm dạng
$$a + b\cos\theta + c\sin\theta$$ (bình phương của nó có tần số 2), nên luật shift hai điểm không còn chính xác. Đây là lỗi tinh vi
nhất của bài: kết quả gần đúng, train vẫn chạy.

**`train_vqc`.** Khởi tạo đúng đặc tả, ghi loss **trước** mỗi bước, cập nhật `params = params − lr · grad`.

## Kết quả (moons, seed 0)

| L | Loss cuối | Train | Test | Lần chạy QNode |
| --- | --- | --- | --- | --- |
| 1 | 0.687 | 0.680 | 0.620 | 900 |
| 2 | 0.605 | 0.735 | 0.660 | 1 700 |
| 3 | 0.239 | 0.930 | 0.910 | 2 500 |
| 4 | 0.169 | 0.985 | 0.980 | 3 300 |

5 lần chia: VQC $$L = 4$$ 0.946 ± 0.022, logistic regression 0.834 ± 0.021, SVM RBF 0.968 ± 0.016, MLP 16 mặc định 0.812 ± 0.031,
MLP 32-32 0.968 ± 0.017. Parameter-shift khớp backprop của PennyLane tới $$5.6 \times 10^{-16}$$. Với 1000 shots, gradient của
$$\cos\theta$$ tại 0.8: parameter-shift trung bình −0.715 độ lệch chuẩn 0.015; sai phân $$\varepsilon = 10^{-2}$$ trung bình −0.960 độ lệch chuẩn 1.650.

## Trả lời câu hỏi cuối notebook

1. **1 layer**: CNOT có control wire 0 giao hoán với $$Z_0$$, nên mọi thứ trên wire 1 (cả $$x_1$$) không ảnh hưởng $$\langle Z_0\rangle$$. Mô hình
   chỉ là hàm Fourier bậc 1 của $$x_0$$, không thể tách hai mặt trăng. Cùng lý do, ở layer cuối của mọi $$L$$, chỉ RY trên wire 0
   có gradient khác 0 (3 trong 4 tham số luôn bằng 0).
2. **Shots**: parameter-shift lấy hiệu của hai kỳ vọng cách nhau $$\pi$$, chia cho 2; nhiễu shot không bị khuếch đại. Sai phân chia
   nhiễu cỡ $$1/\sqrt{1000} \approx 0.03$$ cho $$2\varepsilon = 0.02$$.
3. **So sánh**: chênh 0.022 giữa VQC và SVM RBF cỡ một độ lệch chuẩn giữa các lần chia, nghiêng về SVM; seed 0 cho kết luận
   ngược lại. Không thể viết "quantum tốt hơn". MLP 16 mặc định thua cả logistic regression, MLP 32-32 bằng SVM: baseline
   yếu là cách dễ nhất để có kết quả "quantum thắng".
4. **Chi phí phần cứng**: $$2 \times 16 + 1 = 33$$ mạch mỗi mẫu, 6 600 mạch cho 200 mẫu, khoảng 6.6 triệu lần đo với 1000 shots, cho một bước;
   100 bước là 660 triệu lần đo.

## Bẫy thường gặp

- Mẫu số 2 thay cho $$2\sin s$$; sửa `params` tại chỗ rồi quên trả lại.
- Parameter-shift trực tiếp trên loss MSE (xem trên).
- Không dùng broadcasting: vòng lặp Python 200 mẫu × 33 lần chạy QNode chậm hơn hàng chục lần.
- Báo một lần chia duy nhất.
