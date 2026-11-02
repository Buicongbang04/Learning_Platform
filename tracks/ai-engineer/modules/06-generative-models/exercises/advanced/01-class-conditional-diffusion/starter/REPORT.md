# Diffusion sinh ảnh CIFAR-10 theo class

TODO: viết theo khung trong README của bài (ít nhất 700 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp chưa xem code: họ cần biết
bạn làm gì, đạt bao nhiêu, các con số đáng tin tới đâu.

## Tóm tắt

TODO: 3–4 câu có số: model (số tham số), ngân sách train (bước, thời gian, GPU), FID/KID và class accuracy ở guidance bạn chọn, phát hiện
quan trọng nhất của bảng quét guidance.

## Model và train

TODO: kiến trúc U-Net (bảng hoặc sơ đồ), cách đưa class vào, nhãn rỗng và label dropout, schedule, loss, optimizer, EMA, batch, số bước,
mixed precision, thời gian và VRAM. Các quyết định thiết kế và lý do.

## Cách đánh giá

TODO: sampler và số bước; FID, KID tính thế nào (trọng số Inception nào, resize, bao nhiêu mẫu, so với tập nào); classifier giám khảo và
test accuracy của nó; mốc FID giữa ảnh thật với ảnh thật. Vì sao các con số này không so trực tiếp với paper.

## Kết quả: guidance

TODO: bảng w (gồm bản không điều kiện) × FID, KID, class accuracy, thời gian; câu đọc đường cong đánh đổi chất lượng và đa dạng. Chèn lưới
ảnh, vd. `![Mẫu sinh](samples.png)`, và nói bạn thấy gì.

## Thí nghiệm phụ

TODO: ít nhất hai: EMA so với trọng số thô, số bước DDIM, checkpoint sớm, mốc thật-với-thật. Bảng và diễn giải.

## Lỗi đã gặp

TODO: ít nhất 2 lỗi thật: triệu chứng (số đo, ảnh), cách khoanh vùng (oracle, overfit một batch, so tham chiếu), cách sửa.

## Giới hạn và bước tiếp theo

TODO: độ phân giải, số mẫu của FID, khả năng thuộc lòng (đã kiểm chưa, bằng cách nào), chi phí sinh, bạn sẽ làm gì tiếp (schedule cosine,
v-prediction, DPM-Solver, latent diffusion, text conditioning).
