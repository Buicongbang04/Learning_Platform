# Lời giải: gradient check bằng sai phân trung tâm

## Cách làm

`numerical_grad` duyệt mọi chỉ số của `x` bằng `np.ndindex(x.shape)` (chạy với mọi số chiều). Với mỗi
chỉ số: lưu giá trị gốc, gán `old + eps` rồi gọi `f`, gán `old - eps` rồi gọi `f`, cuối cùng **gán lại
`old`** trong khối `finally`. Gradient là $$\frac{f_+ - f_-}{2\varepsilon}$$.

Ba quyết định đáng chú ý:

- **Sửa tại chỗ, không copy.** Copy cả `x` cho mỗi phần tử tốn $$O(n^2)$$ bộ nhớ ghi; sửa tại chỗ rẻ hơn và
  giống cách gradient check thật làm với trọng số của layer (bài 03: `f` đọc `layer.W` qua chính layer,
  nên **phải** sửa đúng mảng đó).
- **Khôi phục bằng phép gán.** Cách viết hay gặp là dịch bằng phép cộng trừ: `+= eps`, gọi `f`,
  `-= 2 * eps`, gọi `f`, `+= eps`. Mỗi phép làm tròn một lần, nên không chắc trả đúng số cũ: với
  `x ~ N(0, 1)` và `eps = 1e-6`, khoảng 83% phần tử lệch bit cuối. Lệch nhỏ, nhưng
  tích luỹ qua hàng nghìn tham số thì các phần tử check sau được tính trên trọng số đã trôi. Test so
  `np.array_equal` từng bit để buộc cách làm đúng.
- **`try`/`finally`.** Nếu `f` ném lỗi giữa chừng, `x` vẫn được trả về nguyên vẹn.

`relative_error` theo đúng công thức mục 4: chia cho **tổng độ lớn lớn nhất** của hai mảng, nên kết quả
không phụ thuộc thang đo (gradient 1e-8 và 1 được đánh giá như nhau), và mẫu số chặn dưới `1e-12` để hai
mảng toàn 0 cho 0 thay vì `0/0`.

## Vì sao sai phân trung tâm, vì sao eps = 1e-6

Khai triển Taylor: $$f(x \pm \varepsilon) = f(x) \pm \varepsilon f'(x) + \tfrac12\varepsilon^2 f''(x) \pm \tfrac16\varepsilon^3 f'''(x) + \dots$$.
Trừ hai vế, số hạng bậc chẵn triệt tiêu, nên sai số **cắt cụt** là $$O(\varepsilon^2)$$, so với $$O(\varepsilon)$$ của sai
phân một phía. Test `eps=0.1` trên $$x^3$$ cho đúng $$3x^2 + \varepsilon^2$$, thấy rõ số hạng đó.

Ngược lại, sai số **làm tròn** của $$f_+ - f_-$$ cỡ $$10^{-16}|f|$$, chia cho $$2\varepsilon$$ thì lớn lên khi $$\varepsilon$$ nhỏ.
Tổng hai sai số nhỏ nhất quanh $$\varepsilon \approx 10^{-5}$$ tới $$10^{-6}$$ với float64, cho rel cỡ 1e-10. Với float32
($$10^{-7}$$ thay cho $$10^{-16}$$), không có eps nào cho kết quả tin được: luôn check bằng float64.

## Liên hệ với PyTorch

`torch.autograd.gradcheck(fn, inputs, eps=1e-6, atol=1e-5, rtol=1e-3)` làm đúng việc này (và kiểm thêm
Jacobian của hàm nhiều output), và cảnh báo nếu input không phải float64. Khi tự viết một
`torch.autograd.Function` có `backward` riêng, chạy `gradcheck` trước khi tin nó.

## Bẫy thường gặp

- Khôi phục bằng cộng trừ `eps` (xem trên), hoặc quên khôi phục hẳn: phần tử sau check trên `x` đã lệch.
- Dịch cả mảng `x + eps` thay vì một phần tử: ra đạo hàm theo hướng $$(1, 1, \dots)$$, không phải gradient.
- Dùng `np.nditer` mà không có `op_flags=["readwrite"]` rồi gán vào biến lặp: không sửa được `x`.
- Sai số tuyệt đối thay cho tương đối: gradient cỡ 1e-9 thì sai 100% vẫn "đạt" `atol=1e-7`.
