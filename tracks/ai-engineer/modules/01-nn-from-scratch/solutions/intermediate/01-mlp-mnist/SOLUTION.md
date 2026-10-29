# Lời giải: MLP bằng numpy trên MNIST thật

## Cách làm

**`load_mnist`.** Đọc cả tệp gz thành bytes, lấy số chiều ở byte thứ tư của magic, đọc kích thước bằng
`np.frombuffer(data, ">u4", ndim, offset=4)`, rồi phần dữ liệu `uint8` từ offset $$4 + 4 \cdot \text{ndim}$$.
`frombuffer` không sao chép, nên cả 47 MB ảnh train đọc trong khoảng 0.2 giây. Làm phẳng thành 784 cột,
`astype(np.float32) / 255`; nhãn `astype(np.int64)` để dùng làm chỉ số (fancy indexing) và khớp
`torch.long` khi đối chiếu.

**`MLP`.** Giữ hai danh sách `Ws`, `bs` và hai danh sách gradient cùng shape. Đây là hàm
`forward_backward` ở mục 4 lý thuyết viết thành vòng lặp:

| Bước | Forward (tầng i) | Backward (tầng i, đi ngược) |
| --- | --- | --- |
| Linear | lưu input $$h_{i}$$, $$z_i = h_i W_i + b_i$$ | $$dW_i = h_i^\top g$$, $$db_i = \sum_n g_n$$ |
| ReLU (trừ tầng cuối) | lưu $$z_i$$, $$h_{i+1} = \max(z_i, 0)$$ | $$g \leftarrow (g W_i^\top) \odot \mathbb{1}[z_{i-1} > 0]$$ |
| Loss | log-softmax trừ max từng dòng | $$g = (p - \text{onehot}(y)) / N$$ |

`params()` trả cặp `(W, dW), (b, db)` của **chính** các mảng trong model. Vì `loss_and_backward` gán mảng
gradient mới vào `dWs[i]`, `params()` phải dựng danh sách mỗi lần gọi (không lưu sẵn một lần ở
`__init__`), nếu không optimizer sẽ đọc gradient cũ.

**`sgd_step`.** `p -= lr * g` sửa mảng tại chỗ. `p = p - lr * g` thì tạo mảng mới và chỉ gán lại tên
cục bộ, model không đổi: một trong những bug im lặng ở mục 7.

**`train_epoch`.** Một hoán vị cho cả `X` và `y`, cộng `loss * len(b)` rồi chia `len(X)`. Với 60 000 ảnh
và batch 64, batch cuối có 32 mẫu; trung bình đơn giản các loss batch sẽ cho batch đó trọng số gấp đôi.
Test kiểm điều này bằng `lr=0`: tham số đứng yên nên loss epoch phải bằng đúng loss trên cả tập.

## Kết quả thật

numpy 2.5.4, float32, `OMP_NUM_THREADS=4`, seed 0 cho cả model và `rng`:

| Kiểm tra | Kết quả |
| --- | --- |
| Mean pixel train | 0.1307 |
| Loss bước 0 trên 1000 ảnh | 2.384 (ln 10 = 2.303) |
| Overfit 32 ảnh, 200 bước SGD lr 0.1 | loss 0.0127, accuracy 1.00 |
| 784-128-10, lr 0.1, 2 epoch trên 20 000 ảnh (test chấm) | test acc 0.9235 (seed 1 tới 5: 0.918 tới 0.927) |

Bảng SGD ở mục 6 lý thuyết, tái hiện đúng tới chữ số cuối với 4 luồng BLAS (mỗi cấu hình dưới 1 giây). Chạy
1 luồng thì vài số lệch nhẹ vì float32 cộng theo thứ tự khác: lr 0.1 cho 0.9639, lr 1.0 còn 26% ReLU chết,
lr 2.0 (vùng hỗn loạn) cho 0.3311; kết luận không đổi.

| Cấu hình | Train loss epoch 1 / 2 / 3 | Test acc |
| --- | --- | --- |
| SGD lr 0.01 | 0.872 / 0.407 / 0.342 | 0.9160 |
| SGD lr 0.1 | 0.362 / 0.190 / 0.144 | 0.9636 |

| SGD 1 epoch | Loss 100 batch cuối | Test acc | ReLU chết |
| --- | --- | --- | --- |
| lr 0.5 | 0.126 | 0.9664 | 0% |
| lr 1.0 | 0.168 | 0.9552 | 27% |
| lr 2.0 | 2.061 | 0.2052 | 98% |
| lr 5.0 | 2.324 | 0.0982 | 100% |

Đọc kết quả:

- Loss bước 0 là 2.384, hơi trên $$\ln 10 = 2.303$$: He init cho logits có độ lớn cỡ 1 chứ không gần 0,
  nên xác suất ban đầu không đều hẳn. Loss bước 0 ở mức 5 hay 10 mới là dấu hiệu khởi tạo sai.
- lr 1.0 vẫn ra 95.5% nhưng 27% neuron ẩn đã chết: accuracy chưa báo gì mà model đã mất một phần tư công
  suất. lr 5.0 giết hết, output thành hằng số, loss đứng ở 2.324 (cross-entropy của một phân phối gần
  đều), và 0.0982 chính là tỉ lệ chữ số 4 trong tập test (982 / 10 000): model luôn đoán một lớp.
- Khớp tới chữ số cuối với bảng lý thuyết đòi hỏi lấy số ngẫu nhiên đúng thứ tự (`W1` rồi `W2`, dạng
  `rng.normal(0, std, shape)` rồi mới ép `float32`), xáo bằng `rng.permutation` một lần mỗi epoch, và cùng
  số luồng BLAS. Khởi tạo khác thứ tự thì số khác (seed 1 tới 5 ở trên lệch tới nửa điểm), nhưng xu hướng
  phải giống; lệch vài điểm phần trăm thì tìm bug.

## Bẫy thường gặp

- Quên chia gradient cho batch size: gradient check vẫn sai số nhỏ với batch 1, nhưng train thì lr hiệu
  dụng nhân 64, dễ giết ReLU như hàng lr 5.0.
- `params()` trả bản sao (`W.copy()`) hoặc một danh sách dựng sẵn ở `__init__`: optimizer cập nhật vào hư
  không, hoặc đọc gradient của lần backward đầu tiên mãi mãi.
- Dùng `np.random.randn` toàn cục: không tái lập được, và hai model "cùng seed" ra khác nhau.
- Để numpy dùng toàn bộ 16 luồng BLAS với ma trận 64×784: chậm hơn khoảng 5 lần so với 4 luồng.
