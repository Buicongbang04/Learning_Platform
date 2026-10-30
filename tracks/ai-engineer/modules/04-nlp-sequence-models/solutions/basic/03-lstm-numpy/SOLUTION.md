# Lời giải: LSTM numpy và BPTT

## Cách làm

**Forward.** Mỗi bước một phép nhân ma trận cho cả 4 cổng (`x_t @ W_ih.T + h @ W_hh.T + b_ih + b_hh`, shape `(N, 4H)`),
rồi cắt 4 khối theo thứ tự `i, f, g, o`. Thứ tự này là quy ước của PyTorch (Keras dùng `i, f, c, o`, cuDNN có bố cục
riêng): sai thứ tự thì forward vẫn chạy, ra số hợp lý, chỉ không khớp `nn.LSTM`, và khi nạp trọng số từ checkpoint của
framework khác thì model hỏng âm thầm.

**Backward.** Đi ngược thời gian, mang theo hai gradient `dh_next`, `dc_next`:

| Bước | Công thức | Ghi chú |
| --- | --- | --- |
| vào $$h_t$$ | $$dh = \text{dout}_t + dh_{next}$$ | $$h_t$$ vừa là output vừa là input của bước sau |
| vào $$c_t$$ | $$dc = dc_{next} + dh \odot o \odot (1 - \tanh^2 c_t)$$ | hai đường: băng chuyền và qua $$h_t$$ |
| 4 khối $$z$$ | xem Gợi ý 2 của đề | đạo hàm sigmoid, tanh |
| tham số | $$dW_{ih} \mathrel{+}= dz^\top x_t$$, $$dW_{hh} \mathrel{+}= dz^\top h_{t-1}$$ | cộng dồn qua mọi bước |
| về bước trước | $$dh_{next} = dz\,W_{hh}$$, $$dc_{next} = dc \odot f$$ | dòng cuối là "con đường cộng" của mục 5 |

`dh0`, `dc0` là `dh_next`, `dc_next` sau bước $$t = 0$$. Khởi tạo các tích luỹ `dW` bằng 0 **trong** `backward` rồi gán
vào `self` ở cuối, nên gọi hai lần cho cùng kết quả.

**Sigmoid ổn định.** Tách theo dấu: $$1/(1+e^{-x})$$ cho $$x \ge 0$$ và $$e^x/(1+e^x)$$ cho $$x < 0$$, không bao giờ tính
`exp` của số dương lớn. `np.tanh` vốn đã ổn định.

**Clip.** Chuẩn gộp $$\sqrt{\sum_p \|g_p\|^2}$$, hệ số `max_norm / (total + 1e-6)` giống PyTorch; cắt theo chuẩn gộp giữ
nguyên hướng của cả vector gradient.

## Kết quả thật

- T = 50, N = 32, D = 16, H = 64, float64: forward lệch `nn.LSTM` tối đa 1.7e-16, `dx` lệch 4.4e-16, `dW_hh` lệch
  2.8e-14 (ngưỡng test `1e-12` và `1e-10`).
- Test "bias quên bằng 3" (H = 8, 50 bước): gradient ở bước 1 bằng 8.4e-3 lần gradient ở bước 50 (ngưỡng $$10^{-4}$$).
  Cùng phép đo với bias khởi tạo mặc định cho 1.2e-10, khớp bảng mục 4 lý thuyết.
- Thời gian forward + backward cùng cấu hình: 1.7 ms mỗi bước thời gian với numpy, 1.2 ms với `nn.LSTM` float64 trên CPU.
  Trên CPU khác biệt nhỏ vì cả hai đều phải đi tuần tự theo thời gian; lợi thế lớn của thư viện là kernel cuDNN trên GPU
  gộp cả chuỗi và cả 4 cổng, cộng autograd không phải tự viết.

## Bẫy thường gặp

- Quên `dc_next = dc * f` (cho bằng `dc`): gradient của `c0` và các tham số lệch, test `dc0` bắt được.
- Quên phần `o * (1 - tanh(c)^2)` khi đưa `dh` vào `dc`.
- Gán `dW_hh = dz.T @ h_prev` thay vì cộng dồn: chỉ còn gradient của bước $$t = 0$$.
- Bỏ `dh_next` khỏi `dh`: gradient không chảy ngược theo thời gian, model chỉ học phụ thuộc trong một bước.
- Dùng `1 / (1 + np.exp(-x))` trực tiếp: `RuntimeWarning: overflow` với input lớn, test chạy dưới `errstate(over="raise")`.
