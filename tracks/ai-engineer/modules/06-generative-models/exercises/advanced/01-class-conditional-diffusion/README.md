---
title: Diffusion sinh ảnh theo class trên CIFAR-10 với classifier-free guidance (portfolio)
level: advanced
services: []
files:
  - path: starter/cond_diffusion.ipynb
    note: 5 hàm chấm điểm + khung thí nghiệm tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_cond_diffusion.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cifar10
  - uv run --project setup/gpu python -m ipykernel install --user --name ai-gpu
  - uv run jupyter lab tracks/ai-engineer/modules/06-generative-models/exercises/advanced/01-class-conditional-diffusion/starter/cond_diffusion.ipynb
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/advanced/01-class-conditional-diffusion -q
---

## Mục tiêu

Xây trọn một diffusion model có điều kiện class trên CIFAR-10, từ U-Net tới sampler có classifier-free guidance, rồi chứng minh bằng số
nó tốt tới đâu: FID và KID so với ảnh thật, độ chính xác class theo một classifier độc lập, và đường cong đánh đổi giữa chất lượng và đa
dạng khi tăng guidance. Đây là bài portfolio: một người chưa mở notebook đọc `REPORT.md` trong 5 phút phải biết bạn làm gì, đạt bao nhiêu,
và các con số đó đáng tin tới đâu.

## Đề bài

**Phần cứng:** GPU 12GB (PC) · ~480 phút

Thời gian trên là thời gian làm bài (thiết kế, code, thí nghiệm, báo cáo). Thời gian máy của bản tham chiếu trên RTX 3060 12GB đang chia GPU
với một bài khác: train 35 000 bước khoảng 62 phút (61.8 phút gồm cả biên dịch; bf16, `torch.compile`, VRAM đỉnh 1.4 GB), classifier ResNet-20 khoảng 3.5 phút, đánh giá
đầy đủ (6 cấu hình × 5 000 ảnh + các thí nghiệm phụ) khoảng 25 phút: tổng dưới 2 giờ. **Laptop GPU 4GB**: cùng model, không compile (VRAM
đỉnh 2.6 GB), 10 000 tới 15 000 bước; bảng checkpoint sớm trong `SOLUTION.md` cho biết bạn nên kỳ vọng FID cỡ nào ở ngân sách đó. Không có
GPU: làm cùng bài trên FashionMNIST 28×28 một kênh (U-Net của bài Intermediate 03 thêm class embedding), báo FID trên feature của một
classifier FashionMNIST thay cho Inception và ghi rõ trong báo cáo.

Đọc mục 5, 6, 7 phần lý thuyết.

1. Trong `starter/cond_diffusion.ipynb`, viết năm hàm có chữ ký cố định (mô tả trong notebook): `drop_labels`, `cfg_eps`,
   `ddim_sample_cfg`, `fid_from_features`, `kid_from_features`. Test chấm chúng trên dữ liệu nhỏ.
2. Tự thiết kế phần còn lại trong các cell `explore` (khung có sẵn): U-Net có điều kiện class (10 class + một nhãn rỗng), vòng train với
   label dropout, EMA, checkpoint; classifier ResNet-20 làm giám khảo; feature Inception-v3 của `torchvision` (tải trọng số khoảng 100 MB lần
   đầu vào `~/.cache/torch`) cho 10 000 ảnh test.
3. Thí nghiệm tối thiểu, cùng seed và cùng tập 5 000 nhãn (500 mỗi class): quét guidance $$w \in \{0, 0.5, 1, 2, 4\}$$ và bản không điều kiện
   (nhãn rỗng), DDIM 50 bước; mỗi cấu hình báo FID, KID, class accuracy, thời gian sinh. Thêm ít nhất hai trong: EMA so với trọng số thô;
   số bước DDIM; checkpoint sớm; FID giữa ảnh thật và ảnh thật cùng số mẫu (mốc).
4. Lưu lưới ảnh 10 × 10 (mỗi hàng một class) ở $$w$$ bạn chọn, viết `starter/REPORT.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` portfolio tốt** mở bằng tóm tắt có số ("U-Net 9 triệu tham số, 35 000 bước trong 62 phút trên RTX 3060, FID 5k ... ở
$$w = $$ ..., class accuracy ..."); có bảng quét $$w$$ và câu đọc đường cong đánh đổi; nói rõ FID ở đây tính bằng trọng số Inception nào, bao nhiêu
mẫu, so với tập nào, và **vì sao không so được với số trong paper**; có lưới ảnh không chọn tay; có mục "lỗi đã gặp" với triệu chứng và cách
phát hiện; có giới hạn (độ phân giải, thuộc lòng, ngân sách).

## Tiêu chí đạt

- `drop_labels` thay đúng các vị trí theo `rand` của generator, không sửa input; `cfg_eps` đúng công thức trộn và dùng đúng nhãn rỗng, $$w = 0$$
  chỉ chạy nhánh có điều kiện.
- `ddim_sample_cfg` trả đúng ảnh của từng class khi model là "oracle" của dữ liệu một điểm mỗi class, và khớp từng số với một DDIM tham chiếu
  có guidance.
- `fid_from_features` khớp một cài đặt FID độc lập tới 1e-6, đối xứng, bằng 0 với chính nó, khớp dạng đóng $$\lVert m\rVert^2 + d(1 - s)^2$$ trên Gauss
  lớn; `kid_from_features` khớp ước lượng không chệch tham chiếu (cùng cách lấy tập con), gần 0 với hai mẫu cùng phân phối.
- `REPORT.md` không còn TODO, ít nhất 700 từ, có bảng số và hình (tệp hình tồn tại cạnh báo cáo).
- Nội dung chấm theo rubric trong `SOLUTION.md`; mức tham chiếu: FID (5 000 mẫu, Inception torchvision, so với 10 000 ảnh test) tốt nhất dưới
  25 và class accuracy ở $$w = 1$$ trên 0.75 với cấu hình PC.

## Gợi ý

### Gợi ý 1

$$\Sigma_a\Sigma_b$$ không đối xứng, nhưng cùng trị riêng với $$\Sigma_a^{1/2}\Sigma_b\Sigma_a^{1/2}$$, ma trận đối xứng nửa xác định dương. Nên
$$\mathrm{tr}\big((\Sigma_a\Sigma_b)^{1/2}\big)$$ là tổng căn bậc hai các trị riêng của nó, và $$\Sigma_a^{1/2}$$ lấy từ `eigh` của $$\Sigma_a$$. Kẹp các trị riêng âm nhỏ
(sai số số học) về 0 trước khi lấy căn. Với KID, ước lượng không chệch bỏ đường chéo của $$K_{xx}$$ và $$K_{yy}$$.

### Gợi ý 2

Thứ tự làm: (1) năm hàm và test; (2) U-Net có điều kiện, overfit 1 batch 64 ảnh (loss phải xuống rõ dưới 0.02 trong vài trăm bước); (3) train
2 000 bước, sinh 100 ảnh với $$w = 0$$ và $$w = 3$$ để chắc pipeline đúng trước khi train dài; (4) train đủ, lưu checkpoint thường xuyên; (5) giám khảo và
đánh giá. Nhãn rỗng là một hàng riêng trong `nn.Embedding(11, ...)`, không trùng class nào. Sinh có guidance thì gộp hai nhánh thành batch
`2B`. Bản tham chiếu: U-Net ch 64, mults (1, 2, 2, 2), 2 ResBlock mỗi mức, attention ở 8×8, dropout 0.1, schedule linear $$T = 1000$$, AdamW lr 2e-4
với warmup 1 000 bước, batch 128, EMA 0.9995, $$p_{uncond} = 0.1$$.
