---
title: GAN trên dữ liệu đồ chơi và DCGAN trên MNIST, chẩn đoán mode collapse
level: intermediate
services: []
files:
  - path: starter/dcgan.ipynb
    note: 2 lớp, 5 hàm TODO
  - path: tests/test_dcgan.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/02-dcgan-mode-collapse/starter/dcgan.ipynb
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/intermediate/02-dcgan-mode-collapse -q
---

## Mục tiêu

Viết một vòng train GAN đúng tới từng chi tiết (detach, thứ tự bước, loss bằng logits), dựng DCGAN theo đúng các quy tắc kiến trúc của nó,
rồi học cách **đo** GAN: trên dữ liệu đồ chơi biết đáp án thì đếm mode, trên ảnh thật thì dùng classifier làm giám khảo. Làm xong bạn nhìn
một lần train GAN và nói được nó có đang collapse hay không bằng con số, không bằng cảm giác từ loss.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Env gốc (CPU): phần 2D khoảng 4 phút, DCGAN 3 epoch trên 20 000 ảnh mỗi epoch cùng hai cấu hình đối
chứng khoảng 8 phút; kernel `ai-gpu` (GPU 4GB) chạy DCGAN 15 epoch trên đủ 60 000 ảnh, khoảng 6 phút. Test chạy trên CPU với model tí hon, vài giây.

Đọc mục 4 phần lý thuyết. Mở `starter/dcgan.ipynb`:

1. `ring_centers`, `ring_data`: hỗn hợp 8 Gauss trên vòng tròn, mọi số ngẫu nhiên từ generator.
2. `Generator(z_dim=64, c=64)`, `Discriminator(c=64)` đúng bảng kiến trúc trong notebook (BatchNorm ở đâu, bias ở đâu, D trả logit),
   và `dcgan_init`.
3. `gan_step(G, D, opt_g, opt_d, real, generator, loss)`: một bước D rồi một bước G, đúng thứ tự và detach như mô tả; `loss` là `"ns"` hoặc
   `"saturating"`.
4. `class_histogram(pred, n_classes, min_frac)`: số lớp xuất hiện đủ nhiều và KL tới phân phối đều.

Rồi chạy các cell `explore`: 4 cấu hình GAN 2D × 3 seed (saturating, non-saturating, G cập nhật 5 lần mỗi vòng, WGAN-GP), vẽ mẫu; train
classifier giám khảo; train DCGAN và hai cấu hình đối chứng, log D(x), D(G(z)) và giám khảo mỗi epoch. Sau đó làm phần trắc nghiệm của bài
trong app.

## Tiêu chí đạt

- `ring_data` tái lập theo generator, 8 mode chọn đều, độ lệch quanh tâm đúng `std`; `ring_centers` đúng thứ tự góc.
- `Generator` có 1 329 921 tham số, `Discriminator` 138 689, đúng thứ tự lớp, conv trước BatchNorm không bias, G ra ảnh trong $$[-1, 1]$$, D ra logit
  shape `(B,)`; `dcgan_init` cho conv $$\mathcal{N}(0, 0.02^2)$$, BatchNorm $$\mathcal{N}(1, 0.02^2)$$, bias 0, không đụng module khác.
- `gan_step` sau hai bước cho đúng từng tham số của G và D như một cài đặt tham chiếu, với cả hai loại loss; bước D không làm đổi G; giá
  trị trả về là `float`.
- `class_histogram` đúng số lớp theo `min_frac` và đúng KL (0 khi đều, $$\log 10$$ khi chỉ một lớp).

## Gợi ý

### Gợi ý 1

Viết ra giấy tensor nào cần gradient chảy về đâu: loss D cần gradient về D, không về G; loss G cần gradient **qua** D về G, nhưng chỉ G được
cập nhật. `detach()` và việc gọi `opt.step()` của đúng optimizer là hai công cụ. Với BatchNorm trong D: đưa batch thật và batch giả qua D
riêng rẽ (như DCGAN gốc) hay gộp chung cho ra kết quả khác nhau; test theo cách riêng rẽ.

### Gợi ý 2

Thứ tự trong `gan_step`: lấy `z`, sinh `fake` một lần; logits của D trên `real` và trên `fake.detach()`; bước D; rồi cho chính `fake` (chưa detach)
qua D **lần nữa** để có logits mới cho bước G. `d_fake` báo trung bình $$D(G(z))$$ đo ở bước D. Với `class_histogram`, `torch.bincount(pred, minlength=n)`
cho số đếm mỗi lớp.
