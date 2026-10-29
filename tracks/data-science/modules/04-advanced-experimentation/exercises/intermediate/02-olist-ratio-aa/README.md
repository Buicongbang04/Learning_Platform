---
title: Ratio metric trên Olist thật, kiểm bằng A/A
level: intermediate
services: []
files:
  - path: starter/ratio_aa.ipynb
    note: 6 hàm TODO + phần kết luận
  - path: tests/test_ratio_aa.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/04-advanced-experimentation/exercises/intermediate/02-olist-ratio-aa/starter/ratio_aa.ipynb
  - uv run pytest tracks/data-science/modules/04-advanced-experimentation/exercises/intermediate/02-olist-ratio-aa -q
---

## Mục tiêu

Kiểm chứng một phương pháp thống kê theo cách các experimentation platform làm: chạy hàng nghìn thí
nghiệm A/A trên dữ liệu thật, xem tỉ lệ báo động nhầm có đúng 5% không, rồi cài một tác động đã
biết để đo power. Áp lên metric dạng tỉ số "giá trung bình mỗi sản phẩm" của Olist, random theo
`customer_unique_id`.

## Đề bài

Mở `starter/ratio_aa.ipynb`:

1. `load_items(raw_dir)`: sản phẩm trong đơn giao xong (định nghĩa chung của track), cột
   `order_id`, `customer_unique_id`, `price`.
2. `hash_assign(ids, salt, share=0.5)`: phân nhóm nhất quán bằng SHA-256 như module 03.
3. `customer_table(items)`: bảng theo khách, cột `revenue`, `n_items`.
4. `delta_test(table, treat)`: `ratio_a`, `ratio_b`, `diff`, `se`, `p_value`, SE bằng delta method.
5. `naive_test(prices_a, prices_b)`: Welch trên mức sản phẩm (cách tính sai, để so sánh).
6. `aa_study(items, n_sims=200, seed=0)`: tỉ lệ p < 0.05 của hai cách qua `n_sims` lần chia khách
   50/50 ngẫu nhiên.
7. Chạy các cell `explore`: A/A 2 000 lần, rồi cài tác động +2% để đo power. Viết kết luận.

## Tiêu chí đạt

- `hash_assign` tất định, khoảng 50/50, đổi salt thì phân nhóm độc lập, hỗ trợ `share`.
- `customer_table`, `delta_test`, `naive_test` đúng trên dữ liệu nhỏ.
- Trên dữ liệu mô phỏng có cụm mạnh: A/A của delta method báo nhầm 1.5–9.5%, của cách ngây thơ
  trên 20%.
- Trên Olist thật: khoảng 93 350 khách, giá trung bình mỗi sản phẩm khoảng 119.98, design effect
  với salt `olist-aov-aa` trong khoảng 1.05–1.35.
- Kết luận chấm theo `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Chạy `aa_study` nhanh: tính `customer_table` một lần, và mã khách của từng sản phẩm bằng
`pd.Categorical(items.customer_unique_id, categories=table.index).codes`. Mỗi vòng, `treat` là mảng
theo khách; `treat[codes]` cho nhánh của từng sản phẩm.

### Gợi ý 2

Design effect là $$\mathrm{var}_{\text{delta}} / \mathrm{var}_{\text{ngây thơ}}$$. Nếu nó bằng
$$D$$ thì z ngây thơ bị phóng to $$\sqrt D$$ lần, và tỉ lệ báo động nhầm thật là
$$2\,(1 - \Phi(1.96 / \sqrt D))$$. Tính con số này rồi so với kết quả A/A.
