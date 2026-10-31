# Lời giải: Conv2d bằng numpy với im2col

## Cách làm

**`im2col`.** Pad một lần, rồi với mỗi vị trí `(di, dj)` của kernel lấy lát cắt có bước nhảy
`xp[:, :, di : di + s*OH : s, dj : dj + s*OW : s]`. Lát này là "pixel mà vị trí `(di, dj)` của kernel chạm tới"
ở mọi cửa sổ cùng lúc, shape `(N, C, OH, OW)`. Ghi vào `cols6[:, :, di, dj]` của mảng `(N, C, kh, kw, OH, OW)`,
rồi `transpose(0, 4, 5, 1, 2, 3)` và `reshape(N*OH*OW, C*kh*kw)`. Chỉ có `kh·kw` (thường là 9) vòng lặp
Python, mỗi vòng sao chép một khối lớn: numpy làm phần nặng.

Thứ tự trục quyết định tất cả: dòng theo `(n, oh, ow)` để output reshape về `(N, OH, OW, F)` được; cột theo
`(c, di, dj)` để khớp `W.reshape(F, -1)`. Sai thứ tự cột thì forward vẫn ra số, nhưng là conv với một kernel bị
xáo trộn: test so với `F.unfold` bắt lỗi này ngay, còn so `F.conv2d` thì chỉ bắt được khi `C > 1` hoặc kernel
không đối xứng.

**`col2im`.** Đi ngược: `cols.reshape(N, OH, OW, C, kh, kw).transpose(0, 3, 4, 5, 1, 2)` rồi
`xp[..., lát cắt] += c[:, :, di, dj]` vào ảnh đệm toàn 0, cuối cùng cắt bỏ viền padding. Dấu `+=` là cốt lõi:
với stride nhỏ hơn kernel, một pixel nằm trong nhiều cửa sổ, và gradient theo pixel đó là **tổng** đóng góp
của mọi cửa sổ (chain rule cộng theo mọi đường đi). col2im **không** phải nghịch đảo của im2col
(`col2im(im2col(x)) != x`, pixel giữa bị nhân với số cửa sổ chứa nó); nó là **adjoint** (ma trận chuyển vị
của phép tuyến tính im2col), đúng thứ backward cần.

**Forward.** `out = cols @ W.reshape(F, -1).T + b`, shape `(N·OH·OW, F)`, rồi
`reshape(N, OH, OW, F).transpose(0, 3, 1, 2)`. Cache `(x.shape, cols, W, stride, padding)`.

**Backward.** Đây là layer Linear của module 01 áp lên `cols`:

| Đại lượng | Công thức | Shape |
| --- | --- | --- |
| $$D$$ | `dout.transpose(0, 2, 3, 1).reshape(-1, F)` | `(N·OH·OW, F)` |
| $$dW$$ | `(D.T @ cols).reshape(W.shape)` | `(F, C, kh, kw)` |
| $$db$$ | `dout.sum(axis=(0, 2, 3))` | `(F,)` |
| $$dx$$ | `col2im(D @ W.reshape(F, -1), x.shape, ...)` | `(N, C, H, W)` |

## Kết quả thật

numpy 2.5.4, float32, `OMP_NUM_THREADS=4`, máy đang chạy nhiều việc khác (số thời gian chỉ để so thứ bậc):

| Cách tính forward, 64 ảnh 16×32×32, 32 bộ lọc 3×3 | Thời gian |
| --- | --- |
| 4 vòng lặp Python lồng nhau qua `(n, f, oh, ow)` | khoảng 31 s (đo 2 ảnh rồi nhân 32) |
| im2col + một phép nhân ma trận | 45 ms |

`cols` của tầng này nặng 37.7 MB, gấp đúng 9 lần input 4.2 MB (mỗi pixel được chép vào 9 cửa sổ): đó là cái giá
bộ nhớ của im2col, và là lý do cuDNN có thuật toán "implicit GEMM" không dựng `cols` thật.

## Bẫy thường gặp

- `reshape` thay cho `transpose` khi đổi trục: shape đúng, số sai, không lỗi nào.
- `=` thay `+=` trong `col2im`: forward đúng, `dx` sai ở mọi pixel thuộc nhiều cửa sổ. Test "pixel giữa = 4"
  bắt lỗi này.
- Quên cắt padding trong `col2im`, hoặc cắt sai (`xp[:, :, p:-p]` hỏng khi `p = 0` vì `-0` là 0, ra mảng rỗng):
  dùng `p : p + H`.
- `db = dout.sum(axis=0)`: thiếu trục không gian, shape `(F, OH, OW)` thay vì `(F,)`.
