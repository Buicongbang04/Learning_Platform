# Lời giải: simulator statevector nhỏ bằng numpy

## Cách làm

**Gate.** Các hằng là đúng bảng ở mục 3 lý thuyết, dtype complex. Ba gate quay dùng chung một công thức
$$R_P(\theta) = \cos\frac{\theta}{2} I - i\sin\frac{\theta}{2} P$$, đúng vì $$P^2 = I$$; không cần `scipy.linalg.expm`.

**`apply_gate`.** Ý chính: vector $$2^n$$ phần tử với wire 0 là bit trái chính là tensor `(2,) * n` theo thứ tự C của numpy,
trục $$w$$ ứng với wire $$w$$. Áp gate $$k$$ qubit lên `wires`:

1. `np.moveaxis(psi, wires, range(k))`: đưa các trục cần thiết lên đầu, **theo thứ tự trong `wires`**, vì hàng/cột của `U` được
   đánh số theo thứ tự đó (với CNOT, bit trái là control).
2. Reshape thành $$(2^k, 2^{n-k})$$ rồi `U @ ...`: mỗi cột là một "phần còn lại" cố định, gate tác động lên $$2^k$$ biên độ của nó.
3. Reshape về tensor và `moveaxis` ngược lại.

Chi phí $$O(4^k \cdot 2^{n-k})$$ phép nhân, bộ nhớ $$O(2^n)$$; 20 qubit chỉ vài chục mili giây. Dựng
$$I \otimes \dots \otimes U \otimes \dots \otimes I$$ thì cần ma trận $$2^n \times 2^n$$ (16 TB với 20 qubit), và với gate hai qubit trên wire không kề nhau
còn phải chèn thêm SWAP. `moveaxis` trả view, `@` tạo mảng mới, nên `state` gốc không bị sửa.

**Đo.** `probabilities` là `abs(state) ** 2`. `sample_counts` lấy mẫu một lần bằng `rng.choice(2**n, size=shots, p=...)` rồi
`np.unique(..., return_counts=True)`, đổi chỉ số thành chuỗi bằng `format(i, f"0{n}b")` (wire 0 bên trái là đúng thứ tự in
nhị phân). Chia `p` cho tổng để tránh lỗi "probabilities do not sum to 1" khi sai số làm tròn tích luỹ qua nhiều gate.
`expval_z` reshape xác suất thành tensor, đưa trục `wire` lên đầu, cộng các trục còn lại, lấy $$P(0) - P(1)$$.

## Vì sao test như vậy

- So với PennyLane trên mạch ngẫu nhiên bắt mọi lỗi quy ước cùng lúc: thứ tự wire, dấu trong $$e^{-i\theta P/2}$$, góc $$\theta$$ thay vì $$\theta/2$$.
- `wires=[2, 0]` và `[1, 0]` bắt lỗi sắp xếp lại `wires` (dùng `sorted(wires)`): với CNOT nó đảo control và target.
- 20 qubit bắt cách dựng ma trận đầy đủ.

## Bẫy thường gặp

- **Quy ước wire.** Qiskit dùng little-endian (qubit 0 là bit phải), PennyLane và sách Nielsen–Chuang dùng bit trái. Chép code
  giữa hai bên mà không đổi quy ước cho kết quả "gần đúng" khó phát hiện (với trạng thái đối xứng thì trùng).
- **Góc chia đôi.** `rx(np.pi)` là $$-iX$$, không phải $$X$$; khác pha toàn cục nên xác suất đo như nhau, nhưng trong một gate có
  điều khiển (controlled-RX) pha đó thành pha tương đối và đổi kết quả.
- **Transpose nhầm.** `psi @ U` thay cho `U @ psi` áp $$U^\top$$; với H, X, Z (đối xứng) không lộ ra, với Y và gate quay thì lộ.
- **Lấy mẫu bằng vòng lặp** gọi `rng.random()` từng shot: đúng nhưng chậm, và khó tái lập khi đổi số shots.
