# Lời giải: Pooling, kích thước output và receptive field

## Cách làm

**`conv_output_size`.** Kernel giãn phủ $$d(k-1)+1$$ pixel, nên

$$
n_{out} = \left\lfloor \frac{n + 2p - d(k-1) - 1}{s} \right\rfloor + 1
$$

Với $$d = 1$$ đây chính là công thức $$\lfloor (n + 2p - k)/s \rfloor + 1$$ ở module 13 track DS.

**`receptive_field`.** Đệ quy từ input lên: $$r_0 = 1, j_0 = 1$$, rồi với tầng $$l$$:

$$
r_l = r_{l-1} + d_l (k_l - 1)\, j_{l-1}, \qquad j_l = j_{l-1}\, s_l
$$

$$j$$ ("jump") là khoảng cách giữa hai điểm kề nhau của feature map tầng $$l$$, đo bằng pixel input. Kernel ở
tầng sâu nở receptive field nhanh vì mỗi bước của nó đã dài $$j$$ pixel. Ba conv 3×3 stride 1 cho
$$1 + 2 + 2 + 2 = 7$$: cùng vùng nhìn với một conv 7×7 nhưng $$27C^2$$ thay vì $$49C^2$$ tham số và thêm hai phi
tuyến (lập luận của VGG). Gốc ResNet (conv 7×7/2, maxpool 3×3/2) đã cho receptive field 11 với jump 4 chỉ
sau hai tầng.

**Max pooling.** `np.stack` k·k lát cắt thành mảng `(N, C, k·k, OH, OW)`, `argmax` theo trục 2 (vị trí đầu tiên
khi bằng nhau, khớp PyTorch), lấy giá trị bằng `np.take_along_axis`. Cache chỉ cần `argmax`, không cần `x`.
Backward: với mỗi `(i, j)` của cửa sổ, `dx[lát cắt (i, j)] += dout * (argmax == i*k + j)`. Dấu `+=` lo phần cửa
sổ chồng nhau.

**Average pooling.** Forward là tổng k·k lát cắt chia $$k^2$$; backward rải $$dout/k^2$$ về mọi pixel của cửa sổ,
cũng bằng `+=`.

## Kết quả kiểm

| Chồng tầng | rf, jump |
| --- | --- |
| 3 × conv 3×3 | 7, 1 |
| VGG-16 tới conv5_3 / pool5 | 196, 16 / 212, 32 |
| Gốc ResNet + 4 tầng tiếp `[(7,2), (3,2), (3,1), (3,1), (3,2), (3,1)]` | 51, 8 |
| conv 3×3 dilation 1, 2, 4 | 15, 1 |

Ba conv dilation 1, 2, 4 cho receptive field 15 với đúng 3 tầng và không giảm độ phân giải: đó là ý tưởng của
WaveNet và DeepLab (mục 6 lý thuyết).

## Bẫy thường gặp

- `argmax` trên mảng stack theo thứ tự `(j, i)` (cột trước): kết quả đúng khi mọi giá trị khác nhau, sai khi bằng
  nhau, đúng kiểu lỗi chỉ hiện ra với ảnh có vùng bão hoà (pixel 255 liền nhau).
- `dx[...] = ...` thay vì `+=` trong backward: đúng với `k == stride`, sai khi cửa sổ chồng nhau (maxpool 3×3/2 của
  ResNet).
- Quên dilation trong receptive field: chồng dilation 1, 2, 4 ra 7 thay vì 15.
- Nghĩ receptive field là vùng neuron "thật sự dùng". Đó là vùng **có thể** ảnh hưởng; vùng ảnh hưởng hiệu
  dụng (effective receptive field) tập trung ở giữa theo dạng gần Gauss và nhỏ hơn nhiều (Luo et al. 2016).
