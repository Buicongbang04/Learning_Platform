# Lời giải: Hộp bao, IoU và Non-Maximum Suppression

## Cách làm

**Đổi định dạng.** `x1 = cx - w/2`, `x2 = cx + w/2` (tương tự cho y), và ngược lại. Viết bằng `boxes.T` để
tách bốn cột, `np.stack(..., axis=1)` để ghép.

**IoU vector hoá.** Với $$A$$ shape `(N, 4)` và $$B$$ shape `(M, 4)`:

$$
\mathrm{IoU}(a, b) = \frac{|a \cap b|}{|a| + |b| - |a \cap b|}
$$

Góc trên trái của phần giao là `np.maximum(a[:, None, :2], b[None, :, :2])`, góc dưới phải là
`np.minimum(a[:, None, 2:], b[None, :, 2:])`, cả hai shape `(N, M, 2)`. Kẹp hiệu về 0 rồi nhân hai cạnh ra diện
tích giao `(N, M)`. Hợp bằng diện tích hai hộp (broadcast `(N, 1)` + `(1, M)`) trừ giao. `np.divide(...,
where=union > 0)` trả 0 cho hai hộp suy biến mà không sinh `nan` hay cảnh báo. Bộ nhớ là $$O(NM)$$: 1 500 × 1 500
hộp tạo vài mảng 2.25 triệu phần tử, vẫn dưới 0.5 giây.

**NMS.** `order = np.argsort(-scores, kind="stable")`, rồi lặp: lấy `i = order[0]`, thêm vào `keep`, tính IoU
của `i` với `order[1:]` và giữ `order[1:][iou <= thr]`. Mỗi vòng loại ít nhất một hộp (chính `i`), nên tối đa
$$N$$ vòng, mỗi vòng $$O(N)$$: $$O(N^2)$$ trong trường hợp xấu nhất (ít hộp chồng nhau). Detector thật chạy NMS sau
khi lọc theo confidence, nên $$N$$ chỉ còn vài trăm.

**Batched NMS.** Gọi `nms` cho từng lớp (`np.unique(classes)`), đổi chỉ số cục bộ về chỉ số gốc bằng
`np.flatnonzero(classes == c)[keep_c]`, ghép lại và sắp theo score giảm dần. torchvision dùng một mẹo nhanh hơn:
cộng vào toạ độ mỗi hộp một độ dời `class_id * (max_coord + 1)` để hộp khác lớp không bao giờ giao nhau, rồi
gọi `nms` một lần. Hai cách cho cùng kết quả.

## Kết quả kiểm

| Kiểm tra | Kết quả |
| --- | --- |
| `box_iou` so `torchvision.ops.box_iou`, 30 × 17 hộp | sai lệch dưới `1e-12` |
| `nms` so `torchvision.ops.nms`, 200 hộp, 5 ngưỡng | trùng từng chỉ số |
| IoU đúng 0.5, ngưỡng 0.5 | giữ cả hai (so sánh `>` chứ không `>=`) |
| `batched_nms` so `torchvision.ops.batched_nms`, 150 hộp 4 lớp | trùng từng chỉ số |

## Bẫy thường gặp

- Lấy diện tích bằng `(x2 - x1 + 1) * (y2 - y1 + 1)`: quy ước pixel rời rạc của Pascal VOC cũ. Toạ độ liên tục
  (torchvision, YOLO, COCO) không cộng 1. Trộn hai quy ước làm lệch IoU của hộp nhỏ đáng kể (mục 5 lý thuyết).
- Quên kẹp chiều rộng giao về 0: hai hộp không giao mà cả hai cạnh giao đều âm thì tích dương, IoU dương giả.
- NMS kiểu "một lượt": so mỗi hộp với mọi hộp score cao hơn kể cả hộp đã bị loại. Trong đám đông, chuỗi
  A > B > C chồng nhau theo cặp làm C bị loại oan.
- NMS không theo lớp cho detector nhiều lớp: người đứng cạnh xe đạp chồng nhau nhiều, một trong hai biến mất.
