---
title: FinOps - chi phí, rightsizing và chia tiền cụm Kubernetes của Olist
level: basic
services: []
files:
  - path: starter/finops.py
    note: 8 TODO
  - path: data/usage-2026-10.csv
    note: Request và mức dùng thật của 10 workload, tháng 10/2026
  - path: data/pricing.yaml
    note: Đơn giá, chi phí chung, số đơn hàng
  - path: tests/test_finops.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/basic/03-finops-rightsizing -q
---

## Mục tiêu

Biến số liệu usage thành ba câu trả lời FinOps: mỗi team tốn bao nhiêu (kể cả phần chi phí chung), cắt bớt request thì tiết kiệm
bao nhiêu và chỗ nào phải **tăng**, và mỗi 1000 đơn hàng tốn bao nhiêu tiền hạ tầng.

## Đề bài

Cụm Kubernetes của Olist tính tiền theo **request** (tài nguyên đặt trước), không theo mức dùng thật. `data/usage-2026-10.csv` có một
dòng cho mỗi workload trong tháng 10/2026:

| Cột | Ý nghĩa |
| --- | --- |
| `workload`, `team`, `env` | Tên, team sở hữu (trống là chưa gắn nhãn), môi trường |
| `replicas`, `hours` | Số pod và số giờ chạy trong tháng |
| `cpu_request_m`, `mem_request_mi` | Request mỗi pod (millicore, MiB) |
| `cpu_p95_m`, `mem_max_mi` | CPU p95 và RAM cao nhất mỗi pod đo được trong tháng |

`data/pricing.yaml`: `vcpu_hour`, `gib_hour` (USD), `shared` (chi phí chung mỗi tháng: control plane, observability, NAT), `orders`
(số đơn hàng trong tháng).

Điền 8 hàm trong `starter/finops.py`:

1. `load_usage(path)`: list dict cùng khoá với cột, các cột số là `int`, `team` trống là `None`. Cột khác `FIELDS` hay số âm thì
   `ValueError`.
2. `load_pricing(path)`: dict từ YAML; `vcpu_hour`, `gib_hour`, `orders` thiếu hay không phải số dương thì `ValueError`.
3. `cost(row, pricing, cpu_m=None, mem_mi=None)`: chi phí tháng (USD) = `replicas` nhân `hours` nhân (vCPU nhân `vcpu_hour` cộng GiB
   nhân `gib_hour`), vCPU = millicore / 1000, GiB = MiB / 1024. Mặc định dùng request hiện tại; truyền `cpu_m`, `mem_mi` để tính với
   request khác.
4. `rightsize(row, headroom=0.2)`: request đề xuất mỗi pod:
   - CPU = CPU p95 nhân (1 + headroom), làm tròn **lên** bội số 50, tối thiểu 50;
   - RAM = RAM **cao nhất** nhân (1 + headroom), làm tròn lên bội số 64, tối thiểu 128;
   - `action`: `"up"` nếu CPU hay RAM đề xuất lớn hơn hiện tại, `"keep"` nếu cả hai bằng, còn lại `"down"`.
   Trả `{"cpu_m": int, "mem_mi": int, "action": str}`.
5. `allocate(rows, pricing)`: chi phí mỗi team = chi phí trực tiếp của team cộng phần của tổng `shared` chia theo tỉ lệ chi phí trực
   tiếp. Workload không có team gom vào `"unallocated"`. Trả dict team sang USD, làm tròn 2 chữ số.
6. `savings(rows, pricing)`: tổng (chi phí hiện tại trừ chi phí với request đề xuất) của mọi workload, làm tròn 2 chữ số. Workload
   `"up"` làm giảm con số này.
7. `idle(rows, cpu_ratio=0.05, mem_ratio=0.2)`: danh sách `(workload, env)` đã sắp, có CPU p95 **nhỏ hơn** 5% request **và** RAM cao
   nhất nhỏ hơn 20% request.
8. `unit_cost(rows, pricing)`: (tổng chi phí trực tiếp cộng tổng `shared`) chia (số đơn hàng / 1000), làm tròn 4 chữ số.

## Tiêu chí đạt

- `uv run pytest ... -q` pass.
- Viết được ba dòng gửi trưởng nhóm: team nào tốn nhất, tiết kiệm được bao nhiêu nếu rightsizing, và hai workload nào phải **tăng**
  request (kèm lý do). Phần `unallocated` lớn cỡ nào và nên làm gì với nó?

## Gợi ý

### Gợi ý 1

`math.ceil(value / step) * step` làm tròn lên bội số. `olist-api` prod: CPU 310 nhân 1,2 là 372, lên 400; RAM 780 nhân 1,2 là 936, lên
960.

### Gợi ý 2

Chi phí chung chia theo tỉ lệ: phần của team bằng tổng `shared` nhân (chi phí trực tiếp của team chia tổng chi phí trực tiếp). Tổng
mọi team cộng lại phải bằng chi phí trực tiếp cộng chi phí chung.
