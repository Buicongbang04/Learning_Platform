# Lời giải: LSTM cho chuỗi độ dài thay đổi

## Cách làm

- `pad_sequences`: `torch.full((B, T_max), pad_value)` rồi chép từng chuỗi vào đầu hàng.
- Model: `Embedding(padding_idx=0)` → `pack_padded_sequence(emb, lengths.cpu(), batch_first=True,
  enforce_sorted=False)` → cell → `h_n[-1]` → `Linear`. Với LSTM, `state` là tuple `(h_n, c_n)`.
- `clip_gradients`: `float(nn.utils.clip_grad_norm_(model.parameters(), max_norm))`.
- Vòng train như bài Basic 02, thêm `clip_gradients` giữa `backward()` và `step()`.

`padding_idx=0` chỉ làm vector embedding của token 0 bằng 0 và không được cập nhật. Nó **không**
làm RNN bỏ qua padding: RNN vẫn chạy qua các bước đó và trạng thái vẫn đổi (vì có bias và trạng thái
cũ). Packing mới là thứ dừng mỗi chuỗi đúng ở token thật cuối. Test "ghi token thật vào padding"
phân biệt được hai cách.

## Thí nghiệm: ai nhớ được token đầu tiên

3 000 chuỗi train, 400 chuỗi kiểm tra, độ dài 10–20, embedding 16, hidden 32, Adam lr 3e-3, 10
epoch, batch 32, clip 1.0; 10 seed (0–9), CPU 2 luồng:

| Cell | Số seed đạt trên 90% | Accuracy kiểm tra từng seed | Thời gian mỗi lần |
| --- | --- | --- | --- |
| LSTM | 10/10 | 1.000 ở cả 10 seed | khoảng 3 s |
| GRU | 10/10 | 1.000 ở cả 10 seed | khoảng 3 s |
| RNN | 2/10 | 0.957 và 1.000 ở 2 seed; 8 seed còn lại 0.47–0.58 | khoảng 2 s |

Với cùng cấu hình nhưng lr 1e-2, LSTM kẹt ở mức đoán mò (khoảng 0.5) ở 3/3 seed đã thử: bài toán có
bước chuyển pha, learning rate quá lớn làm model không thoát được vùng "đoán theo token gần nhất".

Vì sao RNN thua: gradient từ loss về bước đầu tiên đi qua tích của 10–20 ma trận Jacobian; với
`tanh` và trọng số thường gặp, tích này co về 0 (vanishing gradient), nên tín hiệu "token đầu quyết
định nhãn" gần như không tới được embedding của token đầu. LSTM có **cell state** cập nhật kiểu cộng
($$c_t = f_t \odot c_{t-1} + i_t \odot \tilde c_t$$): khi forget gate gần 1, gradient đi qua gần như
nguyên vẹn. GRU làm điều tương tự với update gate.

## Khi nào dùng LSTM/GRU trong thực tế

- Chuỗi vừa phải, dữ liệu ít, cần chạy streaming từng bước (cảm biến, sự kiện người dùng theo thời
  gian thực): LSTM/GRU nhỏ, rẻ, dễ deploy.
- Văn bản, chuỗi dài, dữ liệu nhiều: Transformer (mục 5 lý thuyết) gần như luôn tốt hơn và train song
  song được.
- Chuỗi thời gian dạng bảng (dự báo doanh số): thường gradient boosting với lag feature (module 07)
  mạnh hơn và dễ giải thích hơn RNN.

## Bẫy thường gặp

- Lấy `output[:, -1]` thay vì `h_n`: với chuỗi ngắn hơn `T_max`, vị trí cuối là padding.
- Quên `enforce_sorted=False` khi batch chưa sắp theo độ dài: PyTorch báo lỗi.
- Clip trước `backward()` (gradient chưa có) hoặc sau `step()` (đã muộn).
- Clipping che mất vấn đề thật: nếu chuẩn gradient trả về thường xuyên lớn gấp hàng trăm lần
  `max_norm`, xem lại learning rate, khởi tạo hay chuẩn hoá dữ liệu.
