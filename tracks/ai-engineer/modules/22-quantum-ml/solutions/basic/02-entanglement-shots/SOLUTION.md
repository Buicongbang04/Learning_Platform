# Lời giải: entanglement bằng SVD và ước lượng từ shots

## Cách làm

- **`bell_state`**: bốn vector hằng chia $$\sqrt 2$$; tên lạ thì `ValueError` thay vì trả `None` âm thầm.
- **`schmidt_coefficients`**: `state.reshape(2**n_a, 2**(n - n_a))` là ma trận hệ số $$M$$, vì wire 0 là bit trái nên $$n_a$$ bit đầu
  của chỉ số chính là chỉ số hàng. `np.linalg.svd(M, compute_uv=False)` trả singular value giảm dần; bỏ các giá trị dưới $$10^{-12}$$
  (sai số làm tròn, không phải entanglement thật).
- **`entanglement_entropy`**: $$p_k = \lambda_k^2$$ là phân phối (tổng 1), entropy Shannon cơ số 2 của nó. Đã lọc $$\lambda = 0$$ nên không gặp
  $$0 \log 0$$; `max(0.0, ...)` chặn $$-0.0$$ do làm tròn.
- **`marginal_probabilities`**: reshape `(2,) * n`, `sum` theo các trục không thuộc `wires`. Các trục còn lại theo thứ tự tăng, nên
  `np.transpose` theo vị trí của từng wire trong danh sách đã sắp; đây là chỗ hay sai khi `wires=[2, 0]`.
- **`expval_from_counts`**: mỗi chuỗi bit góp $$(-1)^{\text{parity}} \times$$ số lần, chia tổng shots. Chuỗi in wire 0 bên trái, nên
  `bits[w]` là bit của wire $$w$$.
- **`shots_for_std`**: từ $$\sqrt{(1 - \langle P\rangle^2)/S} \le \sigma$$ suy ra $$S \ge (1 - \langle P\rangle^2)/\sigma^2$$, lấy trần. `round(x, 9)` trước `ceil`: với `target_std=0.002, expval=0.3`, `0.91 / 0.002**2` ra `227500.00000000003`, `ceil` thẳng cho 227501 thay vì 227500;
  làm tròn tới 9 chữ số bỏ phần nhiễu đó mà không đổi kết quả của các giá trị thật sự lẻ.

## Vì sao test như vậy

- Trạng thái $$\cos t|00\rangle + \sin t|11\rangle$$ có đáp án đóng cho cả hệ số Schmidt lẫn entropy: bắt lỗi quên bình phương ($$\lambda$$ thay
  cho $$\lambda^2$$) và dùng log tự nhiên.
- Hai cách cắt của $$|\Phi^+\rangle \otimes |0\rangle$$ (cắt sau wire 0 cho 1 bit, sau wire 1 cho 0) bắt lỗi reshape theo thứ tự ngược
  (`reshape(2**(n-n_a), 2**n_a).T`).
- Bell state có phân phối biên đều mà phân phối chung chỉ có $$00$$ và $$11$$: đúng điều mục 4 lý thuyết nói về "không truyền thông tin".

## Bẫy thường gặp

- Nhầm entropy của **toàn hệ** (luôn 0 với trạng thái thuần) với entropy của **một phía**.
- Ước lượng $$\langle Z\rangle$$ bằng tỉ lệ ra 0 (thiếu $$2p - 1$$), hoặc đọc chuỗi bit ngược thứ tự.
- Quên rằng sai số giảm theo $$1/\sqrt{S}$$: "gấp đôi shots cho gấp đôi độ chính xác" là sai, cần gấp bốn.
