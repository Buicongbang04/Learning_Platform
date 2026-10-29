---
title: DAG, d-separation và backdoor criterion
level: basic
services: []
files:
  - path: starter/dag.py
    note: 4 hàm TODO
  - path: tests/test_dag.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/06-causal-inference/exercises/basic/01-dag-backdoor -q
---

## Mục tiêu

Tự cài thuật toán trả lời câu hỏi quan trọng nhất trước mọi phân tích quan sát: **điều chỉnh
(control) cho biến nào thì ước lượng được tác động nhân quả**. Rồi thấy bằng số rằng điều chỉnh
nhầm một collider cũng làm hỏng kết quả như quên một confounder.

## Đề bài

DAG được cho dưới dạng danh sách cạnh `[("Z", "T"), ("Z", "Y"), ("T", "Y")]`. Trong
`starter/dag.py`:

1. `descendants(edges, node) -> set`: mọi node đi tới được từ `node` theo chiều mũi tên.
2. `d_separated(edges, x, y, z) -> bool`: `x` và `y` có bị d-separated khi điều kiện trên tập `z`
   không. Dùng thuật toán moral ancestral graph ghi trong docstring.
3. `satisfies_backdoor(edges, treatment, outcome, z) -> bool`: tập `z` có thoả backdoor criterion
   không: không chứa hậu duệ của treatment, và chặn mọi đường backdoor.
4. `ols_effect(df, treatment, outcome, adjust) -> float`: hệ số của treatment trong hồi quy OLS
   `outcome ~ 1 + treatment + adjust`, tự viết bằng `np.linalg.lstsq`.

Không dùng `networkx` hay thư viện causal nào. Test có DAG Olist thu gọn: vùng xa (`region`) và mùa
cao điểm (`season`) gây cả giao trễ lẫn review xấu; giao trễ làm khách liên hệ CSKH
(`contact_cs`), và việc đó cũng ảnh hưởng review.

## Tiêu chí đạt

- `d_separated` đúng cho ba khối cơ bản (chain, fork, collider) và cho trường hợp điều kiện trên
  hậu duệ của collider.
- `satisfies_backdoor` đúng với confounder, collider, mediator, M-bias và DAG Olist.
- `ols_effect` khớp `statsmodels` tới 1e-8.
- Trên dữ liệu mô phỏng (tác động thật bằng 2.0): điều chỉnh confounder cho ước lượng trong khoảng
  ±0.05 quanh 2.0; điều chỉnh collider làm ước lượng lệch quá 0.5.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ "đi tới được" (BFS/DFS) nhận một tập điểm xuất phát và một dict hàng xóm. Dùng
nó ba lần: tìm hậu duệ (dict con), tìm tổ tiên (dict cha), và kiểm tra x còn nối với y trong đồ
thị vô hướng sau khi xoá z.

### Gợi ý 2

Bước moralize: với mỗi node `c` trong tập tổ tiên, mọi cặp cha `(p, q)` của `c` được nối với
nhau bằng một cạnh vô hướng. Đó là cách thuật toán "nhớ" rằng điều kiện trên collider `c` (hoặc hậu
duệ của nó, vì hậu duệ kéo `c` vào tập tổ tiên) mở đường giữa `p` và `q`. Với backdoor, bỏ mọi
cạnh `(treatment, *)` trước khi gọi `d_separated`: những gì còn nối treatment với outcome chính là
các đường backdoor.
