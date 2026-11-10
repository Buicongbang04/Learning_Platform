# Hướng làm: gỡ lỗi vòng train hỏng mà không báo lỗi

Bài không có code lời giải: bản sửa chỉ là 4 dòng, giá trị nằm ở quy trình khoanh vùng và `BUGS.md`. Dưới đây
là 4 bug, triệu chứng đo được của **từng bug khi chỉ còn mình nó** (3 bug kia đã sửa), cách phát hiện và cách
sửa. Số liệu: numpy float64, `OMP_NUM_THREADS=4`, seed 0 (accuracy ghi cho seed 0, 1, 2).

## Bốn bug

| # | Bug | Ở đâu | Gradient check | `train` seed 0/1/2 |
| --- | --- | --- | --- | --- |
| 1 | Gradient không chia batch size | `loss_and_backward`: thiếu `d /= n` | sai, mọi tham số gấp đúng 6 lần | 0.333 / 0.333 / 0.333 |
| 2 | Xáo `X` và `y` bằng hai hoán vị khác nhau | `shuffle` | qua | 0.333 / 0.333 / 0.328 |
| 3 | Hai bias trỏ chung một mảng | `MLP.__init__`: `self.b1 = self.b2 = np.zeros(hidden)` | sai, chỉ ở `b1`, `b2` | 0.998 / 0.998 / 0.998 |
| 4 | Không xoá gradient giữa các bước | `train`: thiếu `model.zero_grad()` | qua | 0.333 / 0.333 / 0.333 |

Sửa cả 4: `train` đạt 1.000 / 0.998 / 0.998, sai lệch gradient check lớn nhất 1.15e-08, mỗi lần train khoảng
0.3 giây. Notebook gốc (đủ 4 bug): accuracy 0.333 với cả ba seed, sai lệch gradient check 1.0, loss epoch 1 là
5.0 rồi thành `inf`, kèm một `RuntimeWarning: divide by zero encountered in log`. Không có exception nào.

### Bug 1: gradient không chia batch size

- **Triệu chứng.** Loss là trung bình trên batch nhưng gradient là tổng, nên mỗi bước đi xa gấp 32 lần (lr hiệu
  dụng 1.6 thay vì 0.05, lại nhân thêm momentum). Loss nhảy quanh 1.1–1.5, cuối cùng 1.19, sát $$\ln 3 = 1.099$$;
  norm gradient bước đầu 15.1 (bản đúng 0.47); 83% neuron tầng 1 và 100% tầng 2 chết.
- **Phát hiện.** Gradient check theo từng tham số: tỉ lệ `norm(giải tích) / norm(số)` bằng **đúng 6.000 ở mọi
  tham số**, 6 là batch size của hàm check. Một hằng số nguyên bằng batch size là dấu vân tay của bug này.
- **Sửa.** Thêm `d /= n` sau `d[np.arange(n), y] -= 1`.

### Bug 2: nhãn lệch khỏi input sau khi xáo

- **Triệu chứng.** Gradient check qua, loss đứng ở 1.10–1.14 suốt 60 epoch (đúng $$\ln 3$$: model học được
  điều tốt nhất có thể khi nhãn độc lập với input là đoán tỉ lệ lớp), accuracy 0.33.
- **Phát hiện.** Overfit một batch cố định (không qua `shuffle`) thì được, train qua `shuffle` thì không: lỗi ở
  đường dữ liệu. Tra từng điểm sau khi xáo về vị trí gốc: chỉ 41% cặp (x, y) giữ đúng nhãn (ngẫu nhiên là
  khoảng 1/3).
- **Sửa.** Một hoán vị dùng chung: `order = rng.permutation(len(X)); return X[order], y[order]`.

### Bug 3: hai tham số trỏ chung một mảng

- **Triệu chứng.** Train vẫn đạt 0.998: bug này gần như vô hại với bài này, nên dễ lọt. Nhưng gradient check
  báo sai lệch 1.0, và chỉ ở `b1` và `b2` (tỉ lệ norm 0.72 và 0.68), các `W` khớp hoàn toàn.
- **Phát hiện.** Sai phân hữu hạn nhích `b1[i]` thì nhích luôn `b2[i]`, nên đo được $$\partial L/\partial b_1 + \partial L/\partial b_2$$,
  còn giải tích chỉ có một số hạng. `model.b1 is model.b2` trả `True`. Optimizer cũng cập nhật mảng đó hai
  lần mỗi bước, với hai velocity riêng.
- **Sửa.** `self.b1, self.b2 = np.zeros(hidden), np.zeros(hidden)`.

### Bug 4: quên `zero_grad`

- **Triệu chứng.** Gradient check qua (nó gọi `zero_grad` trên model mới). Loss theo epoch 1.26 → 1.71 → 5.45
  → 11.0 → 19.2 → ... → `inf`; norm gradient tăng đều theo bước (0.47, 1.18, 2.03, 6.19 ở bước 1, 5, 10, 20);
  cuối cùng 97% neuron tầng 1 chết, `max|W1|` khoảng 1 300, cảnh báo `divide by zero encountered in log`.
- **Phát hiện.** Loss **tăng** đều từ epoch 2 là dấu hiệu bước cập nhật sai, không phải gradient sai. Log norm
  gradient theo bước: nó lớn dần mãi thay vì dao động. Đọc vòng train theo thứ tự PyTorch (`zero_grad` →
  forward → backward → step): `zero_grad` có định nghĩa nhưng không ai gọi, mà `loss_and_backward` thì cộng dồn.
- **Sửa.** Gọi `model.zero_grad()` đầu mỗi bước trong `train`. (Đổi `+=` thành `=` cũng hết bug, nhưng làm mất
  khả năng gradient accumulation và lệch với quy ước của PyTorch; nên giải thích lựa chọn trong `BUGS.md`.)

## Bug che nhau

- Với đủ 4 bug, gradient check báo lỗi (tỉ lệ 6 ở `W`, khoảng 4.1–4.3 ở `b1`, `b2`): hai bệnh trộn vào nhau.
  Tách chúng bằng cách xem tỉ lệ từng tham số: `W` và `b3` đều đúng 6, chỉ `b1`, `b2` lệch khác.
- Sửa bug 1 và 3 xong, gradient check qua nhưng accuracy vẫn 0.33: người vội sẽ nghĩ "gradient đúng rồi, chắc
  do lr" và chỉnh siêu tham số. Đề cấm đổi siêu tham số chính để chặn hướng này.
- Bug 2 và 4 cùng cho accuracy 0.33 nhưng khác loss: bug 2 làm loss đứng ở $$\ln 3$$, bug 4 làm loss tăng
  tới `inf`. Đọc đường loss trước khi đọc accuracy.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 20 | Mọi test pass mà không đổi dữ liệu, siêu tham số hay hàm gradient check |
| Đủ 4 bug, sửa ở gốc | 20 | Mỗi bug sửa đúng dòng gây ra nó; không thêm clip gradient, giảm lr hay đổi khởi tạo để bù |
| Bằng chứng đo được | 25 | Mỗi bug có con số: tỉ lệ gradient 6, tỉ lệ cặp giữ đúng nhãn, `b1 is b2`, đường loss hay norm gradient tăng |
| Quy trình khoanh vùng | 20 | Tách "gradient sai" và "vòng train sai"; nêu được bug nào che bug nào và thứ tự gỡ |
| Bài học dùng lại được | 15 | Checklist trước khi train lâu và cách áp dụng cho PyTorch (`zero_grad`, `DataLoader` xáo cả cặp, tied weights có chủ đích) |

Đạt từ 70 điểm. `BUGS.md` chỉ liệt kê dòng đã sửa mà không có triệu chứng và phép thử không quá 40 điểm.
