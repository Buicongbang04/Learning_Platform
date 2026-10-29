---
title: Target encoding out-of-fold
level: intermediate
services: []
files:
  - path: starter/target_encoding.py
    note: 3 hàm TODO
  - path: tests/test_target_encoding.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/intermediate/01-oof-target-encoding -q
---

## Mục tiêu

Tự cài target encoding có smoothing và phiên bản out-of-fold (OOF), rồi thấy tận mắt vì sao mã hoá
ngây thơ trên chính tập train là leakage: nó "dự đoán" được cả nhãn ngẫu nhiên.

## Đề bài

Trong `starter/target_encoding.py`:

1. `fit_target_encoding(categories, y, smoothing=20)` trả `(mapping, prior)`. `prior` là trung bình
   `y` trên mọi dòng. Category $$c$$ có $$n_c$$ dòng với tổng nhãn $$s_c$$ được mã hoá thành
   (m-estimate, $$m$$ là `smoothing`):

   $$
   \mathrm{enc}(c) = \frac{s_c + m \cdot \text{prior}}{n_c + m}
   $$

   Category ít dòng bị kéo về prior; category nhiều dòng gần với trung bình riêng của nó. NaN không
   được học.
2. `transform_target_encoding(categories, mapping, prior)`: tra bảng, category lạ hoặc NaN nhận
   `prior`. Trả `np.ndarray`.
3. `oof_target_encoding(categories, y, n_splits=5, smoothing=20, seed=0)`: chia
   `KFold(n_splits, shuffle=True, random_state=seed)`; dòng thuộc fold k được mã hoá bằng bảng (và
   prior) học từ các fold còn lại.

Sau khi xong, thử trên Olist thật với `customer_zip_code_prefix` (12 036 giá trị trong train): so
AUC của mã hoá ngây thơ trên train, trên validation, và AUC của mã OOF trên train.

## Tiêu chí đạt

- Đúng công thức; `smoothing=0` cho trung bình thô; smoothing lớn kéo về prior mạnh hơn.
- Đổi nhãn của dòng i không làm đổi mã OOF của dòng i (nhưng đổi mã của dòng khác cùng nhóm).
- Nhãn ngẫu nhiên, 1 500 category: mã ngây thơ cho AUC trên 0.8, mã OOF quanh 0.5.
- Trên Olist thật (smoothing 20): mã ngây thơ AUC 0.856 trên train nhưng 0.536 trên validation;
  mã OOF trên train dưới 0.56.

## Gợi ý

### Gợi ý 1

`pd.Series(y, index=categories.index).groupby(categories.to_numpy()).agg(["sum", "count"])`. Đặt
`y` cùng index với `categories`, nếu không pandas sẽ căn theo index và ra NaN.

### Gợi ý 2

Mã OOF trên nhãn ngẫu nhiên thường cho AUC **dưới** 0.5 một chút. Lý do: bảng của fold k không chứa
nhãn của chính các dòng fold k, nên trong một category, dòng có nhãn 1 thấy tỉ lệ thấp hơn dòng có
nhãn 0. Đó là dấu hiệu đúng, không phải lỗi.
