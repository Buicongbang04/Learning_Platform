---
title: Linear probe có đối chứng
level: basic
services: []
files:
  - path: starter/probe.py
    note: 7 hàm TODO
  - path: tests/test_probe.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/basic/03-linear-probe-controls -q
---

## Mục tiêu

Viết bộ công cụ probing mà một reviewer khó tính chấp nhận: linear probe tự cài (hồi quy logistic có weight decay), chia dữ liệu
theo nhóm để không rò rỉ, chuẩn hoá chỉ bằng thống kê của train, control task của Hewitt & Liang và các baseline. Làm xong bạn
biết vì sao "probe đạt 95%" một mình không nói lên điều gì, và cần thêm những con số nào bên cạnh.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 2 phần lý thuyết. Trong `starter/probe.py` (numpy và PyTorch, không dùng scikit-learn):

1. `group_split(groups, test_frac, seed)`: chia chỉ số mẫu thành train/test sao cho mọi mẫu của một nhóm (ví dụ cùng một câu,
   cùng một văn bản) nằm cùng một phía.
2. `standardize(X_train, X_test)`: chuẩn hoá từng cột bằng mean và std của **train**.
3. `train_linear_probe(X, y, n_classes, weight_decay, steps, seed)` và `probe_accuracy(probe, X, y)`.
4. `control_labels(token_ids, labels, seed)`: nhãn của control task, mỗi loại token một nhãn ngẫu nhiên cố định.
5. `majority_baseline(y_train, y_test)` và `mean_difference_direction(X, y)` (probe "diff-in-means", không cần train).

Thứ tự rút số ngẫu nhiên ghi trong docstring: test so với bản tham chiếu từng phần tử.

## Tiêu chí đạt

- `group_split` không để nhóm nào ở cả hai phía, phủ hết chỉ số, tái lập theo `seed`, đúng thứ tự hoán vị.
- `standardize` dùng thống kê của train cho cả test.
- `train_linear_probe` cho xác suất khớp `LogisticRegression` của scikit-learn với regularization tương đương (test tự dựng),
  weight decay lớn thu nhỏ trọng số, cùng seed cùng kết quả.
- `control_labels` cố định theo loại token, theo phân phối nhãn, khớp bản tham chiếu.
- Trên dữ liệu mà nhãn chỉ gắn với nhóm, probe học thuộc được train nhưng không đoán được test khi chia theo nhóm.
- `majority_baseline` (hoà thì lấy nhãn nhỏ nhất) và `mean_difference_direction` (độ dài 1) đúng.

## Gợi ý

### Gợi ý 1

`np.unique(..., return_inverse=True)` trả cả các giá trị duy nhất lẫn chỉ số để dựng lại mảng gốc từ chúng: rất tiện cho
`control_labels`. `np.isin` cho biết phần tử nào thuộc một tập.

### Gợi ý 2

Bài toán tối ưu của probe lồi và nhỏ: `torch.optim.LBFGS` với `line_search_fn="strong_wolfe"` hội tụ trong vài chục vòng full
batch; LBFGS cần một `closure` tính lại loss. scikit-learn tối thiểu $$\frac12\lVert W\rVert^2 + C\sum_i \ell_i$$; so với loss
của đề (trung bình cộng $$\lambda\lVert W\rVert^2$$) để thấy vì sao test chọn $$C = 1/(2\lambda N)$$.
