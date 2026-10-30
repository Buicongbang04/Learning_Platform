---
title: EDA một trang cho Head of Operations - 1 115 cửa hàng Rossmann khác nhau thế nào
level: advanced
services: []
files:
  - path: starter/store_eda.ipynb
    note: 1 hàm TODO (hồ sơ cửa hàng) + EDA tự do có khung gợi ý
  - path: starter/REPORT.md
    note: Báo cáo một trang - headline, phạm vi, 3 phát hiện, điều chưa biết, bước tiếp
  - path: tests/test_store_eda.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/advanced/01-store-eda-one-pager/starter/store_eda.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/advanced/01-store-eda-one-pager -q
---

## Mục tiêu

Đi hết một vòng EDA thật từ câu hỏi mơ hồ tới một trang kết luận: dựng bảng ở đúng grain (một dòng mỗi cửa hàng),
mô tả phân phối bằng center, spread, shape, định nghĩa "doanh số thấp" rõ ràng, tìm điểm chung bằng so sánh tỉ lệ,
tách tương quan khỏi nhân quả, và viết cho người không mở notebook.

## Đề bài

Head of Operations mới nhắn: *"Tôi vừa nhận 1 115 cửa hàng. Cho tôi biết chúng khác nhau thế nào về doanh số, và
những cửa hàng doanh số thấp có điểm gì chung. Tôi cần biết nên bắt đầu từ đâu, gửi tôi một trang trước thứ Sáu."*
Dữ liệu: bộ `store-sales` (`train.csv`, `store.csv`). Time-box khoảng 3 giờ. Mở `starter/store_eda.ipynb`:

1. `store_profile(train, stores)`: một dòng mỗi cửa hàng có ngày bán (`Open == 1`, `Sales > 0`), index `Store` sắp
   tăng, cột đúng thứ tự `open_days`, `mean_sales`, `median_sales`, `cv_sales` (SD mẫu / mean), `sales_per_customer`
   (tổng/tổng), `promo_lift` (mean ngày `Promo == 1` / mean ngày `Promo == 0` − 1, NaN nếu thiếu một loại ngày),
   `StoreType`, `Assortment`, `CompetitionDistance` (lấy từ `stores`, NaN nếu không có).
2. EDA trong các cell `explore` theo khung gợi ý: phân phối doanh số mỗi cửa hàng, định nghĩa nhóm doanh số thấp, so
   nhóm đó với phần còn lại theo đặc điểm cửa hàng, kiểm các bẫy của phần 5 lý thuyết (cửa hàng thiếu dữ liệu, ít
   khách hay giỏ nhỏ). Được dùng thêm cột bất kỳ của `store.csv` (ví dụ `Promo2`).
3. Viết `starter/REPORT.md` theo khung: 250-700 từ, dòng đầu là headline có con số, đủ các mục.

## Tiêu chí đạt

- `store_profile` đúng trên dữ liệu nhỏ: bỏ ngày đóng cửa và ngày doanh số 0, CV dùng SD mẫu, doanh số mỗi khách là
  tổng/tổng, `promo_lift` NaN khi thiếu loại ngày, cửa hàng không có trong `stores` vẫn giữ với thuộc tính NaN.
- Trên bộ thật: 1 115 cửa hàng, tổng 844 338 ngày bán; cửa hàng 817 bán TB 21 757.48 EUR/ngày; median của
  `mean_sales` 6 589.95 EUR, của `cv_sales` 0.2637, của `promo_lift` 0.4056.
- `REPORT.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Định nghĩa "doanh số thấp" trước khi tìm điểm chung, và viết nó vào báo cáo (quartile dưới? dưới 80% median?). So
**tỉ lệ** đặc điểm trong nhóm thấp với nhóm cao (`pd.crosstab(..., normalize="index")`), không so số đếm: nhóm nào
đông thì số đếm của nó lớn ở mọi đặc điểm.

### Gợi ý 2

Doanh số mỗi ngày = số khách × doanh số mỗi khách. Tách hai thành phần này trước khi đi tìm nguyên nhân: hai cửa hàng
cùng doanh số thấp có thể có hai vấn đề hoàn toàn khác nhau. Một thuộc tính đi kèm nhóm thấp (ví dụ một chương trình
khuyến mãi) có thể là hệ quả của việc cửa hàng yếu chứ không phải nguyên nhân.
