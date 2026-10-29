---
title: LightGBM với early stopping trên bài toán review xấu của Olist
level: intermediate
services: []
files:
  - path: starter/lgbm_olist.ipynb
    note: 3 hàm TODO + 3 câu hỏi
  - path: tests/test_lgbm.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/12-advanced-ml/exercises/intermediate/01-lightgbm-early-stopping/starter/lgbm_olist.ipynb
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/intermediate/01-lightgbm-early-stopping -q
---

## Mục tiêu

Dùng LightGBM đúng cách của người làm thật: chọn số cây bằng early stopping trên tập validation
theo thời gian, đánh giá ở đúng `best_iteration`, hiểu quan hệ learning rate với số cây, và đọc
được khi nào con số validation không đại diện cho production.

## Đề bài

Bài toán review xấu của Olist, cùng định nghĩa, cùng **điểm dự đoán** (lúc đơn vừa giao xong: dùng
được thời gian giao thực tế và cờ trễ, mọi cột của review là leakage) và cùng mốc chia thời gian với
module 10 và 11 (train trước 2018-01-01, validation quý 1/2018, test 2018-04 tới 2018-08). `build_dataset` và
`time_split` đã viết sẵn trong notebook. Mở `starter/lgbm_olist.ipynb`:

1. `fit_early_stopping(X_train, y_train, X_val, y_val, params=None, max_rounds=2000, patience=50)`:
   `lgb.train` với callback `lgb.early_stopping(patience)`, theo dõi `binary_logloss` trên
   validation. `params=None` dùng `PARAMS` của notebook; không sửa dict người gọi truyền vào.
2. `evaluate(booster, X, y) -> {"auc", "pr_auc", "logloss"}` dự đoán tại `best_iteration`.
3. `lr_sweep(..., rates=(0.2, 0.1, 0.05, 0.02), params=None)`: DataFrame index `learning_rate`, cột
   `best_iteration`, `val_logloss`, `test_auc`.
4. Trả lời 3 câu hỏi ở cell cuối (không chấm tự động; so với lời giải mẫu).

## Tiêu chí đạt

- Early stopping dừng trước `max_rounds`; `best_iteration` đúng là vòng có logloss validation nhỏ
  nhất (so với một lần train đủ 300 vòng cùng tham số).
- Nhãn ngẫu nhiên: dừng gần như ngay (`best_iteration ≤ 15`).
- Không sửa `params` truyền vào, không sửa `PARAMS`.
- `evaluate` khớp sklearn tại `best_iteration`.
- Learning rate nhỏ hơn cần nhiều cây hơn.
- Trên Olist thật: 95 824 đơn, chia 43 362 / 20 468 / 31 994; test AUC trong khoảng 0.67–0.75;
  AUC validation cao hơn test ít nhất 0.05; PR-AUC test hơn gấp đôi tỉ lệ review xấu.

## Gợi ý

### Gợi ý 1

```python
train_set = lgb.Dataset(X_train, y_train)
val_set = lgb.Dataset(X_val, y_val, reference=train_set)   # dùng chung cách chia bin của train
```

`reference=train_set` không phải tuỳ chọn trang trí: LightGBM chia mỗi feature thành bin dựa trên
train, và validation phải dùng đúng các bin đó.

### Gợi ý 2

`booster.predict(X)` mặc định đã dùng `best_iteration` khi model có early stopping, nhưng viết rõ
`num_iteration=booster.best_iteration` để code không phụ thuộc vào mặc định đó (và để đúng khi bạn
lưu model rồi nạp lại).
