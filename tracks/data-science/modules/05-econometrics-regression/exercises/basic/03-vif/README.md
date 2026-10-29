---
title: VIF và loại biến đa cộng tuyến
level: basic
services: []
files:
  - path: starter/vif.py
    note: 2 hàm TODO
  - path: tests/test_vif.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/basic/03-vif -q
---

## Mục tiêu

Tự tính Variance Inflation Factor để hiểu nó đo đúng cái gì, nhận ra đa cộng tuyến hoàn hảo, và
viết thuật toán loại biến lặp mà nhiều pipeline dùng (cùng giới hạn của nó).

## Đề bài

Trong `starter/vif.py`, `df` là DataFrame các biến giải thích, **không** có cột hằng số:

1. `vif(df) -> pd.Series`: index là tên cột theo đúng thứ tự, giá trị là

$$
\mathrm{VIF}_j = \frac{1}{1 - R_j^2}
$$

   với $$R_j^2$$ của hồi quy cột $$j$$ lên **hằng số và mọi cột còn lại**. Nếu $$R_j^2 = 1$$ (sai số
   số học: $$1 - R_j^2 < 10^{-10}$$) thì trả `np.inf`. Cột hằng số (variance 0) thì raise `ValueError`.
2. `prune_by_vif(df, threshold=10.0) -> list[str]`: lặp: tính VIF, nếu VIF lớn nhất > `threshold`
   thì bỏ cột đó (hoà thì bỏ cột đứng trước), tính lại. Trả danh sách cột giữ lại theo thứ tự ban đầu.

## Tiêu chí đạt

- Khớp `variance_inflation_factor` của statsmodels **khi đã thêm hằng số** (tới 1e-8).
- Không đổi khi nhân hoặc cộng một cột với hằng số (VIF không phụ thuộc đơn vị đo).
- Đa cộng tuyến hoàn hảo cho `inf`; `prune_by_vif` bỏ đúng một trong các cột trùng và giữ biến
  độc lập.

## Gợi ý

### Gợi ý 1

Với mỗi cột: `y = X[:, j]`, `Z = [1, X[:, khác j]]`, giải `np.linalg.lstsq(Z, y)`, tính $$R^2$$ như
bài Basic 01.

### Gợi ý 2

Cách nhanh hơn khi nhiều biến: VIF là đường chéo của nghịch đảo ma trận tương quan,
`np.diag(np.linalg.inv(df.corr()))`. Đẹp, nhưng nổ (hoặc ra số âm vô nghĩa) khi ma trận suy biến; cách
hồi quy từng cột xử lý trường hợp đó gọn hơn.
