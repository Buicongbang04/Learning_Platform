---
title: Pooling, kích thước output và receptive field
level: basic
services: []
files:
  - path: starter/pooling.py
    note: 6 hàm TODO
  - path: tests/test_pooling.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/03-computer-vision/exercises/basic/02-pooling-receptive-field -q
---

## Mục tiêu

Viết max pooling và average pooling có backward bằng numpy, rồi hai phép tính mà kỹ sư CV làm hằng ngày khi
đọc hoặc thiết kế kiến trúc: kích thước output của mỗi tầng và **receptive field** của một neuron. Làm xong
bạn trả lời được "neuron cuối của backbone này nhìn thấy vùng ảnh rộng bao nhiêu" mà không cần chạy code.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 1 phần lý thuyết (phần pooling và receptive field). Trong `starter/pooling.py`, quy ước NCHW như
Basic 01; pooling không padding, áp riêng từng kênh.

1. `conv_output_size(n, k, stride=1, padding=0, dilation=1)`: kích thước output theo một chiều, đúng như
   `nn.Conv2d` (kernel giãn `dilation` phủ $$d(k-1)+1$$ pixel).
2. `receptive_field(layers)`: `layers` là danh sách `(kernel, stride)` hoặc `(kernel, stride, dilation)`. Trả
   `(rf, jump)`: số pixel input (theo một chiều) mà một điểm output cuối nhìn thấy, và khoảng cách tính bằng
   pixel input giữa hai điểm output kề nhau.
3. `maxpool2d_forward(x, k, stride)` → `(out, cache)` và `maxpool2d_backward(dout, cache)` → `dx`. Gradient chỉ
   về vị trí max của mỗi cửa sổ; nhiều vị trí bằng nhau thì vị trí **đầu tiên** theo thứ tự hàng rồi cột thắng
   (như PyTorch); cửa sổ chồng nhau (`k > stride`) thì gradient **cộng dồn**.
4. `avgpool2d_forward(x, k, stride)` và `avgpool2d_backward(dout, cache)`.

Chỉ dùng numpy; vòng lặp Python chỉ qua `k × k` vị trí trong cửa sổ.

## Tiêu chí đạt

- `conv_output_size` khớp shape của `nn.Conv2d` trên 8 cấu hình (có stride, padding, dilation).
- `receptive_field` khớp receptive field **đo bằng gradient** trong test (conv trọng số 1, đếm pixel input
  có gradient khác 0) trên 5 chồng tầng, gồm gốc ResNet và chồng dilation 1, 2, 4; VGG-16 cho `(196, 16)` ở
  conv5_3 và `(212, 32)` ở pool5.
- Max/avg pooling forward và backward khớp `F.max_pool2d`/`F.avg_pool2d` + autograd trên 5 cặp
  `(k, stride)`, gồm cửa sổ chồng nhau.
- Pixel là max của cả 9 cửa sổ 3×3 stride 1 nhận gradient 9; bốn phần tử bằng nhau thì gradient về phần tử
  góc trên trái.

## Gợi ý

### Gợi ý 1

Giống im2col ở Basic 01: lát cắt `x[:, :, i : i + s*OH : s, j : j + s*OW : s]` là giá trị tại vị trí `(i, j)` của
mọi cửa sổ. `np.stack` k·k lát cắt theo một trục mới rồi `max`/`argmax` theo trục đó; `argmax` của numpy trả
vị trí đầu tiên khi bằng nhau, và thứ tự stack `(i, j)` theo hàng rồi cột cho đúng quy tắc của PyTorch.

### Gợi ý 2

Receptive field đi từ input lên: bắt đầu `rf = 1, jump = 1`. Mỗi tầng kernel $$k$$, stride $$s$$, dilation
$$d$$ nở rộng $$d(k-1)$$ bước, mỗi bước dài `jump` pixel input: `rf += d*(k-1)*jump`, rồi `jump *= s`. Padding
không đổi receptive field, chỉ đổi vị trí của nó.
