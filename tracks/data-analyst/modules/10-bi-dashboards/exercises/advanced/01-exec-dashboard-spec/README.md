---
title: Spec và bản dựng dashboard điều hành cho một stakeholder thật
level: advanced
services: [postgres, metabase, superset]
files:
  - path: starter/DASHBOARD_SPEC.md
    note: Spec 7 phần + bảng KPI; viết xong không còn TODO
  - path: starter/spec_lint.py
    note: 2 TODO - đọc bảng KPI, kiểm spec
  - path: tests/test_spec.py
    note: Không sửa
run:
  - docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset
  - uv run python setup/bi/load_da.py
  - uv run python setup/bi/init_bi.py
  - uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/01-exec-dashboard-spec/starter/spec_lint.py
  - uv run pytest tracks/data-analyst/modules/10-bi-dashboards/exercises/advanced/01-exec-dashboard-spec -q
---

## Mục tiêu

Đi trọn vòng thiết kế một dashboard như DA senior: từ một yêu cầu mơ hồ của stakeholder tới spec viết ra (người
dùng, quyết định, câu hỏi, KPI có định nghĩa, bố cục, bộ lọc, drill-down, refresh), rồi tới bản dựng chạy được
trên công cụ bạn chọn, có đối chiếu số. Bài không có một đáp án đúng; được chấm theo rubric trong `SOLUTION.md`.

## Đề bài

Chọn **một** trong hai yêu cầu (cả hai dùng dữ liệu thật đã nạp vào schema `da`):

- **A. Giám đốc thương mại** của nhà bán buôn quà tặng (Online Retail II, `da.online_retail_ii`): "Tôi muốn một
  dashboard để họp tháng với các trưởng thị trường. Mỗi tháng tôi phải quyết định dồn ngân sách khuyến mãi và
  nhân sự chăm khách cho thị trường nào."
- **B. Trưởng vận hành** Capital Bikeshare (Bike Sharing, `da.bike_hour`): "Tôi cần biết mỗi tuần nên tăng xe ở
  khung giờ nào, và thời tiết xấu thì giảm ca điều phối bao nhiêu."

Việc cần làm:

1. **Viết `starter/DASHBOARD_SPEC.md`** theo khung có sẵn, giữ 7 heading `## ` và các cột bảng KPI:
   - **Người dùng và quyết định**: ai, nhịp dùng, quyết định nào thay đổi; ai không phải người dùng chính.
   - **Câu hỏi dashboard trả lời**: 3-5 câu có động từ so sánh; câu nào để dành cho ad-hoc.
   - **KPI**: 3-7 KPI, mỗi dòng đủ `Định nghĩa`, `Công thức`, `Grain`, `So sánh`, `Refresh`, `Owner`. Doanh thu
     theo định nghĩa chung của track (doanh thu gộp, dòng hợp lệ); tỉ lệ là measure (tổng/tổng).
   - **Bố cục**, **Bộ lọc và drill-down**, **Refresh và cache** (kỳ chưa đủ hiển thị thế nào).
   - **Bản dựng**: công cụ đã chọn và vì sao, đường dẫn script, ba con số đã đối chiếu.
2. **Viết `starter/spec_lint.py`** (2 TODO) để tự kiểm spec trước khi dựng:
   - `parse_kpi_table(md)`: bảng markdown đầu tiên trong phần `## KPI` thành list dict `{tên cột: ô}` (đã strip,
     bỏ dòng `| --- |`); không có phần hoặc bảng thì `[]`.
   - `lint_spec(md)`: list lỗi bằng tiếng Việt: mỗi phần thiếu (một lỗi mỗi phần, nêu tên phần), phần rỗng hoặc
     còn `TODO`; bảng KPI thiếu cột bắt buộc (nêu tên cột), ít hơn 3 hoặc nhiều hơn 7 KPI, tên KPI trùng (không
     phân biệt hoa thường và khoảng trắng hai đầu), mỗi ô bắt buộc rỗng một lỗi (nêu tên KPI và tên cột). Spec
     tốt trả `[]`.
3. **Dựng dashboard** trên Metabase, Superset hoặc Streamlit bằng script đặt trong `starter/` (ví dụ
   `starter/build_dashboard.py`, dùng lại cách làm của các bài Basic 02, Intermediate 01, 02), idempotent, tên
   đối tượng bắt đầu bằng một tiền tố riêng. Lưu ảnh chụp dashboard vào `starter/` và ghi đường dẫn trong phần
   **Bản dựng**.
4. **Đối chiếu ba con số** trên dashboard (một tổng kỳ, một breakdown, một ô khi đã lọc) với SQL hoặc pandas độc
   lập, ghi cả hai giá trị vào phần **Bản dựng**.

## Tiêu chí đạt

- `spec_lint.py` đúng trên các spec mẫu trong test (thiếu phần, còn TODO, quá ít/quá nhiều KPI, tên trùng, ô
  rỗng, thiếu cột).
- `DASHBOARD_SPEC.md` của bạn qua `lint_spec` và không còn chữ TODO.
- Dashboard dựng được bằng script, chạy lại không tạo bản trùng; ba con số đối chiếu khớp.
- Thiết kế chấm theo rubric trong `SOLUTION.md` (người dùng và quyết định, KPI có định nghĩa, bố cục, bộ lọc,
  kỳ chưa đủ, chọn công cụ, đối chiếu số); từ 70/100 là đạt.

## Gợi ý

### Gợi ý 1

Viết phần **Người dùng và quyết định** trước, rồi gạch mọi KPI không làm quyết định đó thay đổi. Với yêu cầu A,
"thị trường" là `country`, nhưng United Kingdom chiếm khoảng 85% doanh thu: một bar chart theo nước sẽ chỉ thấy
UK; cân nhắc tách UK và "các nước còn lại", hoặc xếp hạng theo tăng trưởng. Với yêu cầu B, câu hỏi theo giờ và
loại ngày (làm việc / nghỉ) đã có ở Intermediate 01; tuần cuối của dữ liệu chỉ có một ngày.

### Gợi ý 2

`split_sections` đã có sẵn: lấy phần `KPI`, tìm dòng đầu tiên bắt đầu bằng `|`, đọc liên tiếp các dòng bảng,
tách ô bằng `line.strip().strip("|").split("|")`. Dòng phân cách là dòng mà mọi ô khớp `:?-{3,}:?`. Để kiểm tên
trùng, chuẩn hoá bằng `name.strip().lower()`.
