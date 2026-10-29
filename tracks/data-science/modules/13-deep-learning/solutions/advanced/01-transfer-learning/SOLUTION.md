# Hướng làm: transfer learning có kiểm chứng

## Các hàm

- `select_classes`: `keep = torch.isin(y, torch.tensor(classes))`, đổi nhãn qua dict `{c: i}`.
- `few_shot_indices`: với mỗi lớp, `randperm` (generator có seed) trên chỉ số của lớp đó, lấy
  `n_per_class` đầu, ghép và sắp.
- `replace_head`: `model[-1] = nn.Linear(model[-1].in_features, n_classes)`.
- `freeze_backbone`: `p.requires_grad_(id(p) in head_ids)` cho mọi tham số.
- `make_optimizer`: hai group, chỉ tham số `requires_grad`; group backbone bỏ hẳn khi rỗng. Đưa tham
  số đóng băng vào AdamW thường vô hại (không có `.grad` thì bị bỏ qua) nhưng dễ gây hiểu nhầm, và
  một số optimizer/thư viện vẫn áp weight decay lên chúng.
- `fine_tune`: vòng train chuẩn.

## Kết quả tham chiếu

Bản tham chiếu: CNN của bài Intermediate 01, pretrain 3 epoch trên 24 910 ảnh lớp 0–4 (Adam lr 1e-3;
accuracy test nguồn 0.919, 14 s trên CPU i7-11800H 8 luồng). Đích: lớp 5–9, test 5 000 ảnh. Số epoch
`max(20, 4000 // (5n))` (80 epoch khi n = 10), batch 32. Từ đầu: Adam lr 1e-3. Linear probe: head lr
1e-2. Fine-tune: head 1e-3, backbone 1e-4. 3 seed mỗi ô, trung bình [min, max]:

| Ảnh nhãn mỗi lớp | Từ đầu | Linear probe | Fine-tune toàn bộ |
| --- | --- | --- | --- |
| 10 | 0.838 [0.828, 0.849] | 0.764 [0.755, 0.780] | 0.852 [0.839, 0.877] |
| 50 | 0.923 [0.919, 0.927] | 0.839 [0.832, 0.846] | 0.919 [0.916, 0.924] |
| 200 | 0.948 [0.945, 0.952] | 0.873 [0.859, 0.881] | 0.953 [0.950, 0.957] |

Đọc kết quả, đây là điều quan trọng nhất của bài:

- **Linear probe thua train từ đầu ở mọi mức**, kém 7.4–8.4 điểm. Đặc trưng học từ áo, quần, váy không
  đủ để phân biệt giày, sandal, túi: khoảng cách miền (domain gap) giữa nguồn và đích lớn, và nguồn
  chỉ có 5 lớp, quá hẹp để học đặc trưng tổng quát.
- **Fine-tune toàn bộ ngang bằng từ đầu**: nhỉnh hơn ở 10 ảnh mỗi lớp (0.852 so với 0.838, nhưng
  khoảng min–max chồng nhau) và 200 ảnh, thua nhẹ ở 50. Không có bằng chứng transfer giúp đáng kể.
- Đích ở đây dễ (giày, túi, sandal khác hình dạng rõ), nên train từ đầu với 50 ảnh mỗi lớp đã đạt
  92%. Transfer có giá trị nhất khi tác vụ đích khó và dữ liệu nhãn ít.

Test của bài cho thấy chiều ngược lại: khi nguồn dạy đúng đặc trưng mà đích cần (phát hiện đường
thẳng), linear probe với 6 ảnh mỗi lớp đạt 0.99–1.00 trên 10 seed, còn backbone ngẫu nhiên chỉ
0.60–0.82. Hai kết quả cùng nói một điều: **transfer tốt khi nguồn rộng và gần đích**.

## Báo cáo tốt nói gì về thực tế

- Pretrain thật nghĩa là ImageNet (1.28 triệu ảnh, 1 000 lớp) hoặc model tự giám sát lớn, không phải 5
  lớp FashionMNIST. Với ảnh sản phẩm Olist (nếu có), điểm xuất phát hợp lý là
  `torchvision.models.resnet18(weights="IMAGENET1K_V1")`: thay `fc`, linear probe trước làm baseline,
  rồi fine-tune với lr backbone nhỏ, dùng đúng transform chuẩn hoá của weights đó.
- Chọn cách: ít dữ liệu và miền gần → linear probe (rẻ, khó overfit); dữ liệu vừa → fine-tune với lr
  phân tầng hoặc mở dần từng tầng (gradual unfreezing); miền rất xa và nhiều dữ liệu → train từ đầu
  có thể ngang bằng.
- BatchNorm: khi đóng băng, đặt các tầng BN ở `eval()` để running stats không đổi; fine-tune với batch
  rất nhỏ thì BN ước lượng thống kê kém.
- Chi phí: linear probe có thể tính trước đặc trưng một lần rồi train logistic regression; fine-tune
  cần GPU khi model lớn.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Các hàm và test | 15 | Test pass; giải thích được vì sao đóng băng phải loại khỏi optimizer |
| Thiết kế thí nghiệm | 20 | Có đối chứng train từ đầu; cùng dữ liệu đích và cùng tập test cho mọi cách; ≥ 3 seed; không chọn siêu tham số theo test |
| Báo cáo số liệu | 15 | Bảng trung bình và độ phân tán theo seed; ghi rõ số epoch, lr, thời gian, phần cứng |
| Diễn giải trung thực | 25 | Nhận ra transfer không giúp (hoặc giúp ít) ở thiết lập này và giải thích bằng domain gap / độ rộng nguồn; không kết luận vượt quá khoảng dao động seed |
| Khi nào dùng cách nào | 15 | Quy tắc theo lượng dữ liệu, độ gần miền, chi phí; nhắc BatchNorm và lr phân tầng |
| Áp dụng thực tế | 10 | Kế hoạch cụ thể với model pretrain thật (weights, transform, baseline linear probe) |

Đạt từ 70 điểm trở lên. Báo cáo chỉ khẳng định "fine-tune tốt hơn" dựa trên một seed mà không có đối
chứng train từ đầu không quá 40 điểm.
