# Mini framework numpy: MLP trên MNIST

TODO: viết theo khung trong README của bài (ít nhất 600 từ). Người đọc là nhà tuyển dụng hoặc đồng nghiệp
chưa xem code: họ cần biết bạn làm gì, đạt bao nhiêu, và bạn hiểu vì sao.

## Tóm tắt

TODO: 3–4 câu. Framework có gì, model nào, test accuracy bao nhiêu, train mất bao lâu trên máy gì, phát hiện
quan trọng nhất của ablation.

## Kiến trúc framework

TODO: các lớp và quan hệ giữa chúng (sơ đồ hoặc bảng), API forward/backward/parameters/state, train/eval, các
quyết định thiết kế (Param có cờ decay, state gồm running stats...) và lý do.

## Thiết lập thí nghiệm

TODO: chia dữ liệu (train/val/test), kiến trúc model, optimizer, lr, schedule, batch size, early stopping,
seed, phần cứng, số luồng BLAS, thời gian.

## Đường cong học

TODO: chèn hình (vd. `![Đường cong](curves.png)`) và đọc nó: epoch nào tốt nhất, có overfit không, early
stopping có kích hoạt không.

## Ablation

TODO: bảng các cấu hình (bỏ BatchNorm, bỏ dropout, lr cố định, SGD momentum...), ít nhất 2 seed mỗi cấu hình,
và diễn giải: chênh lệch nào thật, chênh lệch nào chỉ là dao động giữa seed.

## Lỗi đã gặp

TODO: ít nhất 2 lỗi thật bạn gặp khi viết framework: triệu chứng, cách phát hiện (gradient check, overfit một
batch, so với PyTorch...), cách sửa.

## Giới hạn và bước tiếp theo

TODO: framework còn thiếu gì so với PyTorch, kết quả này nói được gì và không nói được gì, bạn sẽ làm gì tiếp.
