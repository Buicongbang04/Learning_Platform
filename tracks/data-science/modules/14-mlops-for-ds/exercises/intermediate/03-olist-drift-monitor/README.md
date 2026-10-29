---
title: "Olist: giám sát drift cho model review xấu"
level: intermediate
services: []
files:
  - path: starter/drift_monitor.ipynb
    note: 5 hàm TODO + khuyến nghị
  - path: tests/test_drift_monitor.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/14-mlops-for-ds/exercises/intermediate/03-olist-drift-monitor/starter/drift_monitor.ipynb
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/intermediate/03-olist-drift-monitor -q
---

## Mục tiêu

Đóng vai job monitoring cho model review xấu trong 8 tháng "production" (01/2018 tới 08/2018): đo
drift từng feature so với dữ liệu train, theo dõi theo tháng, sinh cảnh báo, rồi làm phần khó nhất
là **phân biệt drift đáng lo với drift vô hại** bằng cách nhìn cả score và AUC khi nhãn về.

## Đề bài

Notebook có sẵn `load_olist_table`, `time_split`, `build_pipeline` (giống bài Intermediate 01).
Bạn viết:

1. `psi`, `psi_categorical`: chép từ bài Basic 01, cùng quy ước.
2. `drift_report(reference, current, numeric, categorical) -> DataFrame`: index là feature, cột
   `psi`, `ks` (thống kê `scipy.stats.ks_2samp` trên dữ liệu bỏ NaN, chỉ biến số; biến phân loại để
   NaN), `level` (`stable` < 0.1 ≤ `moderate` < 0.25 ≤ `major`), sắp theo `psi` giảm dần.
3. `monthly_psi(reference, current, features, date_col="order_purchase_timestamp") -> DataFrame`:
   index tháng `"YYYY-MM"` theo thứ tự, một cột PSI mỗi feature số, cộng cột `n`.
4. `alerts(monthly, threshold=0.25) -> list[tuple[str, str]]`: các cặp `(tháng, feature)` có PSI
   từ ngưỡng trở lên, sắp xếp; cột `n` không tính.

Chạy các cell `explore` (báo cáo drift, biểu đồ `freight`, PSI theo tháng, drift của score, AUC
theo tháng và theo nhóm đơn trễ/đúng hẹn) rồi viết khuyến nghị 6–10 câu trong cell markdown cuối.

## Tiêu chí đạt

- `psi` và `psi_categorical` đúng quy ước bài Basic 01.
- `drift_report` đúng cấu trúc, đúng thứ tự, phát hiện feature trôi và bang mới, không báo nhầm
  feature không đổi.
- `monthly_psi` đúng tháng, đúng số đơn, đúng PSI; `alerts` chỉ ra đúng tháng trôi.
- Trên Olist thật: hai feature trôi mạnh nhất train → test là `freight` (PSI ≈ 0.318) và
  `promised_days`; `delay_days` ổn định (≈ 0.073) trên cả giai đoạn nhưng PSI tháng 6/2018 ≈ 0.652.
- Khuyến nghị trả lời đủ 4 câu hỏi cuối notebook (chấm theo rubric trong lời giải).

## Gợi ý

### Gợi ý 1

`current[date_col].dt.strftime("%Y-%m")` cho nhãn tháng; `groupby(..., sort=True)` giữ thứ tự thời
gian vì chuỗi `"YYYY-MM"` sắp theo thứ tự từ điển cũng là thứ tự thời gian.

### Gợi ý 2

`monthly.drop(columns="n").stack()` cho Series có index `(tháng, feature)`, tiện để lọc theo ngưỡng.
Khi đọc bảng AUC, so cột `auc` với `auc_on_time`: nếu AUC toàn cục dao động mạnh mà AUC trong từng
nhóm gần như đứng yên, cái thay đổi là **tổ hợp** đơn trễ/đúng hẹn, không phải model.
