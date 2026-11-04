---
title: River online learning so với model batch, khi có và không có drift
level: basic
services: []
files:
  - path: starter/online.py
    note: 5 TODO
  - path: tests/test_online.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/basic/02-river-online-vs-batch -q
---

## Mục tiêu

Đo chứ không đoán: online learning thắng model batch khi nào, và hoà hay thua khi nào. Bạn viết vòng đánh giá prequential
(test-then-train) chuẩn của River, so với một model sklearn huấn luyện một lần rồi đóng băng, trên hai luồng: một luồng có concept
drift đột ngột, một luồng ổn định. Kết luận phải ra từ số, và hàm `choose` phải chọn đúng cho cả hai.

## Đề bài

Luồng là list `(x, y)` với `x` là dict feature (`x0`, `x1`, `x2`), `y` là 0/1. Test sinh luồng 4 000 mẫu (seed cố định); luồng
drift đổi ranh giới quyết định ở giữa luồng. Điền `starter/online.py`:

1. `make_online_model()`: một model River (lớp thuộc package `river`, có `learn_one`/`predict_one`). Gợi ý:
   `preprocessing.StandardScaler() | linear_model.LogisticRegression(...)`; bạn chọn model và tham số.
2. `prequential(stream, model, start=0)`: với từng mẫu theo thứ tự, **gọi `predict_one(x)` trước rồi mới `learn_one(x, y)`**
   (test kiểm đúng chuỗi lời gọi). Độ chính xác chỉ tính trên các mẫu có chỉ số `>= start`, nhưng model học từ mọi mẫu.
3. `frozen_batch(stream, train_n)`: `sklearn.linear_model.LogisticRegression()` mặc định, cột feature theo thứ tự tên đã sắp
   xếp, fit trên `train_n` mẫu đầu, trả độ chính xác trên phần còn lại (test so với cách tính đó, sai số 0.005).
4. `compare(stream, train_n)`: `{"online": prequential(stream, make_online_model(), start=train_n), "batch": frozen_batch(...)}`,
   hai số trên **cùng đoạn** mẫu sau `train_n` (test thay `make_online_model` bằng một model cố định để kiểm đoạn tính điểm).
5. `choose(result, margin=0.05)`: `"online"` khi `online > batch + margin` (chặt), ngược lại `"batch"`.

Test ép: với luồng drift (3 seed) `online >= batch + 0.15` và `choose` trả `"online"`; với luồng ổn định (3 seed)
`batch >= 0.9`, `batch - 0.05 <= online <= batch + 0.02` và `choose` trả `"batch"`.

## Tiêu chí đạt

- Test pass.
- Bạn giải thích được vì sao trên luồng ổn định online learning không thắng, và vẫn nên giữ model batch (tái lập được, kiểm duyệt
  được, có cổng đánh giá trước khi lên production).
- Bạn kể được ít nhất hai rủi ro của online learning khi chạy thật: dữ liệu bẩn hay bị đầu độc đi thẳng vào model, nhãn về trễ
  nên "online" thực ra chậm, khó rollback một model đổi mỗi giây.

## Gợi ý

### Gợi ý 1

Prequential là cách đánh giá công bằng duy nhất cho model học liên tục: mỗi mẫu là dữ liệu test trước khi thành dữ liệu train.
Đảo thứ tự (học rồi mới đoán) cho độ chính xác đẹp giả.

### Gợi ý 2

Nếu model online của bạn thích nghi chậm sau drift, tăng learning rate (`optim.SGD(0.05)`), hoặc thử
`forest.ARFClassifier(seed=0)` (Adaptive Random Forest, mỗi cây có bộ phát hiện drift và được thay khi drift; chậm hơn hồi quy
logistic khoảng 20 lần nhưng vẫn vài giây). Cả hai đã kiểm qua mọi seed của test. Không phải model online nào cũng đủ:
`tree.HoeffdingAdaptiveTreeClassifier` mặc định chỉ hơn batch khoảng 0.1 ở một seed. Đừng chỉnh để thắng luồng ổn định: ở đó hoà
là đúng.
