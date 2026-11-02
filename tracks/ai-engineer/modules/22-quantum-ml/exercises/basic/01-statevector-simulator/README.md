---
title: Simulator statevector nhỏ bằng numpy
level: basic
services: []
files:
  - path: starter/statevector.py
    note: 5 hằng gate, 8 hàm TODO
  - path: tests/test_statevector.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/22-quantum-ml/exercises/basic/01-statevector-simulator -q
---

## Mục tiêu

Tự viết lõi của mọi simulator lượng tử: gate là ma trận, trạng thái là vector $$2^n$$ chiều, áp gate vào đúng wire mà
không dựng ma trận $$2^n \times 2^n$$, rồi đo bằng xác suất và shots. Làm xong, mỗi dòng PennyLane ở các bài sau với bạn chỉ còn là
một phép nhân ma trận bạn đã tự viết, và bạn khớp được kết quả với PennyLane tới $$10^{-10}$$.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/statevector.py` (chỉ dùng numpy), theo quy ước PennyLane: **wire 0 là bit trái nhất** của chỉ số trạng thái
(với 3 qubit, chỉ số 4 = `0b100` là $$|100\rangle$$).

1. Hằng `X`, `Y`, `Z`, `H` (ma trận $$2 \times 2$$ complex) và `CNOT` ($$4 \times 4$$, control là bit trái), theo bảng mục 3 lý thuyết.
2. `rx(theta)`, `ry(theta)`, `rz(theta)`: $$R_P(\theta) = e^{-i\theta P/2}$$. Để ý góc chia đôi.
3. `zero_state(n)`: $$|0\dots0\rangle$$, vector complex dài $$2^n$$.
4. `apply_gate(state, U, wires, n)`: áp gate $$k$$ qubit `U` ($$2^k \times 2^k$$) lên các wire trong `wires`, **theo đúng thứ tự đó** (với
   CNOT, `wires=[2, 0]` nghĩa là control wire 2, target wire 0). Trả trạng thái mới, không sửa `state`, không dựng ma trận
   $$2^n \times 2^n$$: test chạy với 20 qubit.
5. `probabilities(state)`: Born rule, mảng thực.
6. `sample_counts(state, shots, rng)`: đo `shots` lần, trả `{chuỗi bit: số lần}` chỉ với các chuỗi xuất hiện, wire 0 bên trái,
   số ngẫu nhiên chỉ lấy từ `rng`.
7. `expval_z(state, wire, n)`: $$\langle Z_{wire}\rangle = P(0) - P(1)$$ của wire đó, float Python.

## Tiêu chí đạt

- Gate cố định đúng tác dụng trên cơ sở và đều unitary; `rx`, `ry`, `rz` đúng $$e^{-i\theta P/2}$$ (vd. $$R_X(\pi) = -iX$$, $$R_Y(2\pi) = -I$$).
- `X` trên wire 0 của 3 qubit cho $$|100\rangle$$; gate một và hai qubit khớp phép dựng bằng Kronecker, kể cả `wires` không theo thứ tự tăng.
- `apply_gate` không sửa input và chạy được với 20 qubit.
- Một mạch ngẫu nhiên 3 qubit (H, RX, RY, RZ, CNOT, Y) khớp `qml.state()` của PennyLane tới $$10^{-10}$$.
- `sample_counts` đúng định dạng, không có chuỗi xác suất 0, tần suất trong 5 độ lệch chuẩn, cùng seed cùng kết quả.
- `expval_z` đúng cho từng wire.

## Gợi ý

### Gợi ý 1

`state.reshape((2,) * n)` biến vector thành tensor có một trục cho mỗi wire, trục $$w$$ là wire $$w$$ (vì wire 0 là bit trái, cũng là
trục đầu theo thứ tự C của numpy). Áp gate một qubit lên wire $$w$$ là nhân ma trận $$2 \times 2$$ vào trục đó.

### Gợi ý 2

Với gate $$k$$ qubit: `np.moveaxis` đưa các trục trong `wires` lên đầu **theo thứ tự của `wires`**, reshape thành
$$(2^k, 2^{n-k})$$, nhân `U @`, reshape lại rồi `moveaxis` trả các trục về chỗ cũ. Lấy mẫu: `rng.choice(2**n, size=shots, p=...)` rồi
`np.unique(..., return_counts=True)`; chuỗi bit là `format(i, f"0{n}b")`.
