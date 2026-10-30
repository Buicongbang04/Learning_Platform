---
title: Phân loại và xếp lịch hàng đợi yêu cầu - self-serve, ad-hoc, dashboard hay dự án
level: basic
services: []
files:
  - path: starter/triage.py
    note: 4 hàm TODO
  - path: starter/backlog.csv
    note: Hàng đợi 12 yêu cầu (ví dụ giả định)
  - path: tests/test_triage.py
    note: Không sửa
run:
  - uv run python tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/basic/03-request-triage/starter/triage.py
  - uv run pytest tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/basic/03-request-triage -q
---

## Mục tiêu

Biến quy trình nhận yêu cầu ở phần 2-3 của lý thuyết thành quy tắc rõ ràng, chạy được: phân loại từng yêu cầu
(self-serve, hỏi lại, dashboard, dự án, ad-hoc), chấm góc phần tư impact/effort, xếp thứ tự và lập lịch một tuần
theo năng lực giờ. Viết thành code buộc bạn chốt từng ngưỡng mà trong đầu thường để mơ hồ.

## Đề bài

`starter/backlog.csv` là hàng đợi 12 yêu cầu của team data một công ty bán lẻ online trong một tuần (**ví dụ giả
định**, không phải dữ liệu thật: bài này luyện quy trình, không phân tích số). Cột: `id`, `requester`, `ask`,
`decision` (quyết định phía sau; trống là chưa rõ), `impact` (1-5), `effort_hours` (giờ ước lượng tới bản đủ để
quyết định), `recurring` (câu hỏi lặp lại), `in_dashboard` (số đã có trên dashboard chính thức).

Viết trong `starter/triage.py`:

1. `classify(request) -> str` nhận một dict (một dòng), áp **lần lượt**, quy tắc đầu tiên khớp thắng:
   1. `in_dashboard` đúng → `"self-serve"` (gửi link, kể cả khi chưa rõ quyết định);
   2. `decision` thiếu (`None`, `NaN`, chuỗi rỗng hoặc chỉ khoảng trắng) → `"clarify"`;
   3. `recurring` đúng → `"dashboard"`;
   4. `effort_hours > 4` (hơn nửa ngày) → `"project"`;
   5. còn lại → `"ad-hoc"`.
2. `quadrant(impact, effort_hours) -> str`: impact ≥ 4 là cao, effort ≤ 8 giờ là thấp; trả `"quick win"` (cao,
   thấp), `"big bet"` (cao, cao), `"fill-in"` (thấp, thấp), `"money pit"` (thấp, cao).
3. `prioritize(requests) -> DataFrame`: bản sao (không sửa đầu vào) thêm ba cột `route`, `quadrant`, `score` =
   `impact / effort_hours`. Thứ tự: các dòng có `route` là `dashboard`, `project`, `ad-hoc` lên trước, sắp theo
   góc phần tư (quick win, big bet, fill-in, money pit), rồi `score` giảm dần, rồi `id` tăng dần; các dòng
   `self-serve` và `clarify` ở cuối, sắp theo `id`. Index đánh lại 0..n-1.
4. `plan_week(requests, capacity_hours) -> list[str]`: duyệt theo thứ tự của `prioritize`, chỉ xét `dashboard`,
   `project`, `ad-hoc`, **bỏ qua money pit** (cần thương lượng, không tự xếp lịch); lấy yêu cầu nếu `effort_hours`
   còn vừa số giờ còn lại, không vừa thì bỏ qua và xét tiếp. Trả danh sách `id` theo thứ tự đã lấy.

Chạy `starter/triage.py` để in bảng ưu tiên và lịch tuần 30 giờ, rồi tự trả lời: với mỗi yêu cầu không được xếp
lịch, bạn sẽ nhắn gì cho người hỏi?

## Tiêu chí đạt

- `classify` đúng thứ tự quy tắc, xử lý được ô trống của CSV (`NaN`) và chuỗi chỉ có khoảng trắng.
- `quadrant` đúng ở các ngưỡng biên (impact 4, effort 8).
- `prioritize` không sửa đầu vào, đúng cột và đúng thứ tự, kể cả khi hoà `score`.
- `plan_week` tham lam theo thứ tự ưu tiên, bỏ qua việc không vừa và money pit.
- Trên `backlog.csv`: R02, R11 là self-serve, R03 phải hỏi lại, R04 là dashboard; lịch 30 giờ gồm R04, R09, R01,
  R08, R12, R07 (26 giờ).

## Gợi ý

### Gợi ý 1

`pandas.read_csv` đọc ô trống thành `float("nan")`, mà `bool(float("nan"))` là `True`. Kiểm thiếu bằng
`math.isnan` cho số thực và `str.strip()` cho chuỗi. Để lấy từng dòng dạng dict: `df.to_dict("records")`.

### Gợi ý 2

Sắp theo góc phần tư bằng một cột phụ `QUADRANT_ORDER.index(q)`, rồi
`sort_values([cột phụ, "score", "id"], ascending=[True, False, True])`, bỏ cột phụ, ghép phần còn lại bằng
`pd.concat` và `reset_index(drop=True)`.
