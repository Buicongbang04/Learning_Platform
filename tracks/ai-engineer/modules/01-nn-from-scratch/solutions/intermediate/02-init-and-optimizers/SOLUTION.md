# Lời giải: Xavier, He, SGD momentum, Adam/AdamW

## Cách làm

**Khởi tạo.** Mỗi hàm là một dòng `rng.normal(0, std, (fan_in, fan_out))`, với $$\text{std} = \sqrt{2/(n_{in} + n_{out})}$$
(Xavier) hoặc $$\sqrt{2/n_{in}}$$ (He). Hai lỗi hay gặp: truyền phương sai vào chỗ của độ lệch chuẩn (std nhỏ
đi căn bậc hai lần, ví dụ 0.002 thay vì 0.045), và dùng `fan_out` cho He. Test `he_init(1000, 10)` bắt lỗi
thứ hai: dùng nhầm thì phương sai thành $$2/10$$, lớn gấp 100 lần.

**State của optimizer.** `step(params)` nhận danh sách cặp `(tham số, gradient)` luôn cùng thứ tự, nên state
chỉ cần là danh sách mảng song song, tạo bằng `np.zeros_like(p)` ở lần gọi đầu. Mọi phép cập nhật đều tại
chỗ (`v *= μ`, `v += g`, `p -= ...`): `p = p - ...` sẽ không đổi gì trong model, còn `v = μ * v + g` thì đổi
biến cục bộ, state không được lưu.

**SGDMomentum.** Kiểu PyTorch $$v \leftarrow \mu v + g$$, $$\theta \leftarrow \theta - \eta v$$. PyTorch ở bước đầu đặt $$v = g$$, đúng bằng
$$\mu \cdot 0 + g$$, nên khởi tạo $$v = 0$$ là khớp. Kiểu sách ($$v \leftarrow \mu v + \eta g$$) cho cùng quỹ đạo khi $$\eta$$ cố định
nhưng khác khi lr đổi giữa chừng (schedule), nên khi so với `torch.optim` phải dùng đúng kiểu này.

**Adam/AdamW.** Đếm bước `t` từ 1, cập nhật $$m, v$$ tại chỗ, chia cho $$1 - \beta^t$$, cộng `eps` **sau** căn.
Weight decay kiểu AdamW: `p -= lr * λ * p` **trước** bước Adam, đúng thứ tự `torch.optim.AdamW` (nhân
tham số với $$1 - \eta\lambda$$ trước). Với $$\lambda = 0$$, lớp này chính là `torch.optim.Adam`.

Hai test ngoài so khớp `torch.optim` cho thấy công dụng của hai chi tiết:

- Gradient 0: Adam thuần đứng yên, AdamW vẫn co tham số đúng $$1 - \eta\lambda$$. Weight decay không đi qua
  $$m, v$$ nên không bị chia cho $$\sqrt{\hat v}$$. Với Adam + L2, tham số có gradient lớn (v̂ lớn) bị phạt ít hơn.
- Bước đầu tiên: $$\hat m = g$$, $$\hat v = g^2$$ nên mỗi toạ độ đi đúng $$\eta$$ theo dấu gradient, dù $$g$$ là
  0.001 hay 200. Bỏ bias correction thì bước đầu là $$\eta \cdot 0.1g/\sqrt{0.001g^2} \approx 3.16\eta$$.

## Kết quả thật

numpy 2.5.4, `OMP_NUM_THREADS=4`, seed 0. Hai bảng của phần lý thuyết, tái hiện đúng tới chữ số cuối (bảng
khởi tạo dùng float64; bảng MNIST dùng float32 nên số luồng BLAS khác có thể làm lệch chữ số thứ tư).

10 tầng 512 neuron, input chuẩn hoá (mục 5):

| Activation, khởi tạo | std tầng 1 | std tầng 5 | std tầng 10 | std gradient về input |
| --- | --- | --- | --- | --- |
| tanh, $$\mathcal{N}(0, 0.01^2)$$ | 2.16e-01 | 5.61e-04 | 3.26e-07 | 3.22e-07 |
| tanh, $$\mathcal{N}(0, 1)$$ | 9.82e-01 | 9.82e-01 | 9.82e-01 | 2.73e+05 (90.5% activation có $$\lvert h\rvert > 0.99$$) |
| tanh, Xavier | 6.29e-01 | 3.19e-01 | 2.24e-01 | 2.60e-01 |
| ReLU, Xavier | 5.85e-01 | 1.40e-01 | 2.27e-02 | 3.05e-02 |
| ReLU, He | 8.27e-01 | 7.93e-01 | 7.25e-01 | 9.75e-01 |

MLP 784-128-10, batch 64, 3 epoch trên 60 000 ảnh (mục 6):

| Optimizer | Train loss epoch 1 / 2 / 3 | Test acc | Thời gian |
| --- | --- | --- | --- |
| SGD lr 0.01 | 0.872 / 0.407 / 0.342 | 0.9160 | 0.7 s |
| SGD lr 0.1 | 0.362 / 0.190 / 0.144 | 0.9636 | 0.7 s |
| SGD + momentum 0.9, lr 0.01 | 0.379 / 0.192 / 0.146 | 0.9622 | 0.8 s |
| Adam lr 1e-3 | 0.292 / 0.130 / 0.091 | **0.9747** | 1.5 s |
| Adam lr 1e-1 | 0.847 / 0.720 / 0.810 | 0.7288 | 3.2 s |

Đọc kết quả:

- Bảng khởi tạo: chỉ "ReLU, He" và "tanh, Xavier" giữ thang đo qua 10 tầng; "tanh, N(0, 1)" có std
  activation đẹp nhất nhưng 90.5% neuron bão hoà và gradient nổ tới 2.7e+05. Nhìn std thôi là chưa đủ.
- Momentum 0.9 với lr 0.01 gần trùng SGD lr 0.1: lr hiệu dụng khi gradient ổn định là $$\eta/(1-\mu) = 0.1$$.
- Adam lr 1e-3 tốt nhất mà không cần tune, nhưng Adam lr 1e-1 có loss **tăng lại** ở epoch 3 và chỉ đạt
  72.9%: Adam ít nhạy với lr hơn SGD trong vùng hợp lý, không phải miễn nhiễm. Cấu hình này nằm trong vùng hỗn
  loạn nên rất nhạy với sai số làm tròn: chạy 1 luồng BLAS cho loss 0.856 / 0.750 / 0.801 và test acc 0.8274
  (các cấu hình khác chỉ lệch ở chữ số thứ tư), nhưng loss vẫn tăng lại ở epoch 3 và accuracy vẫn tụt xa.
- Adam chậm hơn SGD khoảng 2 lần mỗi bước: thêm hai mảng state và các phép căn, chia trên mỗi tham số.
  Với model lớn, hai state đó còn là 2 lần bộ nhớ tham số (module 10, 14).

## Bẫy thường gặp

- `rng.normal(0, 2 / fan_in, ...)`: truyền phương sai thay cho std.
- State tạo lại mỗi bước: momentum và $$m, v$$ không tích luỹ qua các bước. State dùng chung một mảng cho
  nhiều tham số (`[np.zeros(...)] * n`): các tham số ghi đè state của nhau, hoặc lỗi shape.
- Bias correction dùng `t` bắt đầu từ 0: chia cho $$1 - \beta^0 = 0$$.
- Cộng `eps` vào trong căn (`sqrt(v̂ + eps)`): gần như vô hại khi gradient lớn, nhưng với gradient cỡ 1e-3 thì
  $$\sqrt{10^{-6} + 10^{-8}}$$ đã lệch 0.5%; test bước đầu với $$g = 0.001$$ bắt được.
- AdamW áp decay sau bước Adam thay vì trước: lệch $$\eta^2\lambda$$ mỗi bước, test bắt được.
