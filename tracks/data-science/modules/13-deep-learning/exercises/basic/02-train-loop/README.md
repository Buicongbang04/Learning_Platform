---
title: Vòng train PyTorch có early stopping
level: basic
services: []
files:
  - path: starter/train_loop.py
    note: 3 hàm TODO
  - path: tests/test_train_loop.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/13-deep-learning/exercises/basic/02-train-loop -q
---

## Mục tiêu

Viết vòng train mà bạn sẽ dùng lại cho mọi model trong module: đúng thứ tự `zero_grad → forward →
backward → step`, đúng chế độ `train()` / `eval()`, loss trung bình theo mẫu, và early stopping
khôi phục trọng số tốt nhất. Đây là chỗ các bug "im lặng" của deep learning hay nằm.

## Đề bài

Trong `starter/train_loop.py`:

1. `train_one_epoch(model, loader, loss_fn, optimizer) -> float`: một lượt qua `loader`, mỗi batch
   `zero_grad`, forward, backward, `step`. Model ở chế độ train. Trả loss trung bình **theo mẫu**:
   `loss_fn` trả trung bình của batch, và batch cuối có thể nhỏ hơn, nên trung bình của các batch
   không bằng trung bình theo mẫu.
2. `evaluate(model, loader, loss_fn) -> {"loss", "accuracy"}`: chế độ eval, trong
   `torch.no_grad()`, loss trung bình theo mẫu, accuracy theo `argmax` của logits.
3. `fit(model, train_loader, val_loader, loss_fn, optimizer, max_epochs, patience) -> dict`: train
   tối đa `max_epochs`, sau mỗi epoch đo val loss bằng `evaluate`. Epoch đánh số từ 0; một epoch
   cải thiện khi val loss **nhỏ hơn hẳn** giá trị tốt nhất trước đó; dừng ngay khi đã có
   `patience` epoch liên tiếp không cải thiện. Trước khi trả về, nạp lại trọng số của epoch tốt
   nhất. Trả `{"train_loss": [...], "val_loss": [...], "best_epoch": int}`.

## Tiêu chí đạt

- Với `lr = 0` (tham số không đổi), loss của `train_one_epoch` bằng loss trên toàn bộ dữ liệu, kể
  cả khi batch cuối lệch cỡ.
- Mọi forward trong `train_one_epoch` chạy ở chế độ train và có gradient; mọi forward trong
  `evaluate` chạy ở chế độ eval và không có gradient (test gắn hook để kiểm).
- Một epoch với SGD momentum cho tham số giống hệt vòng train chuẩn.
- Trên dữ liệu 3 cụm tách được, `fit` đạt accuracy validation trên 95%.
- Khi model overfit (nhãn train ngẫu nhiên), `fit` dừng đúng `patience` epoch sau epoch tốt nhất,
  và val loss của model trả về bằng val loss tốt nhất trong lịch sử.

## Gợi ý

### Gợi ý 1

Cộng `loss.item() * len(yb)` và chia cho tổng số mẫu. `.item()` cũng cắt liên kết với graph: cộng
dồn chính tensor `loss` qua các batch sẽ giữ cả graph của mọi batch trong bộ nhớ.

### Gợi ý 2

`model.state_dict()` trả về **tham chiếu** tới các tensor đang được train. Lưu
`copy.deepcopy(model.state_dict())`, không thì "bản tốt nhất" bị optimizer sửa theo ở các epoch sau.
