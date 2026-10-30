---
title: Tăng GDP mà giảm CO2 - decoupling thật hay "xuất khẩu" phát thải? (merge, phân loại, seaborn)
level: intermediate
services: []
files:
  - path: starter/decoupling.ipynb
    note: 3 hàm TODO (thay đổi giữa hai năm, phân loại, bảng sản xuất vs tiêu dùng) + scatter seaborn + kiểm độ nhạy
  - path: tests/test_decoupling.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py owid-co2
  - uv run jupyter lab tracks/data-analyst/modules/04-python-for-analysts/exercises/intermediate/02-co2-decoupling/starter/decoupling.ipynb
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/intermediate/02-co2-decoupling -q
---

## Mục tiêu

Trả lời một câu hỏi của nhà đầu tư bằng pipeline pandas nhiều bước: ghép hai ảnh chụp theo năm bằng `merge` có
`validate`, lọc có chủ đích, phân loại bằng `np.select`, đối chiếu hai định nghĩa của cùng một chỉ số (CO2 sản xuất và
tiêu dùng), vẽ scatter có nhóm bằng seaborn, và **kiểm kết luận nhạy với lựa chọn của mình tới đâu**.

## Đề bài

Bộ `owid-co2` (Our World in Data, CC BY 4.0, ghim commit `382ee6c`); cột `co2` (sản xuất), `consumption_co2` (tiêu
dùng, có từ 1990), `gdp` (có tới 2022), `population`. Quỹ đầu tư hỏi: *"Từ 2005 tới 2022, bao nhiêu nền kinh tế lớn
tăng GDP mà giảm CO2? Hay họ chỉ chuyển nhà máy ra nước ngoài?"*. Mở `starter/decoupling.ipynb`:

1. `period_change(df, start, end, cols, min_population)`: chỉ dòng quốc gia, ghép năm đầu với năm cuối theo `country`
   (`merge` với `validate="one_to_one"`), giữ nước đủ dữ liệu và đủ dân số năm cuối, trả tỉ lệ thay đổi.
2. `classify(change, emissions)`: `absolute` / `relative` / `coupled` / `gdp_decline` theo thứ tự ưu tiên trong notebook.
3. `decoupling_table(change)`: nhãn theo CO2 sản xuất, theo CO2 tiêu dùng, và cờ `offshoring`.
4. Chạy các cell `explore` (bảng chéo, scatter seaborn, so sản xuất với tiêu dùng, độ nhạy theo năm đầu và ngưỡng dân
   số), viết đoạn 4–5 câu cho quỹ theo phần 3 notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy
   notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: bỏ dòng tổng, lọc thiếu dữ liệu theo đúng `cols`, ngưỡng dân số theo năm cuối, báo lỗi
  khi một nước có hai dòng cùng năm, thứ tự ưu tiên của nhãn (GDP bằng 0, CO2 tăng bằng GDP), cờ `offshoring`.
- Trên bộ thật (2005 → 2022, từ 10 triệu dân): 75 nước; theo CO2 sản xuất 17 `absolute`, 39 `relative`, 16 `coupled`,
  3 `gdp_decline`; 14 nước `absolute` cả theo tiêu dùng; `offshoring` là Australia, Mexico, Poland; Việt Nam `coupled`;
  Anh CO2 −45.5% với GDP +21.0%.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Lấy hai bảng con `year == start` và `year == end` (cột `country` + `cols`, bảng năm cuối thêm `population`), rồi
`a.merge(b, on="country", suffixes=("_start", "_end"), validate="one_to_one")`. `dropna(subset=[...])` trên đúng các
cột `<col>_start`, `<col>_end`, rồi lọc dân số. Chia cột bằng `.to_numpy()` để không lệch index.

### Gợi ý 2

`np.select([gdp <= 0, em < 0, em < gdp], ["gdp_decline", "absolute", "relative"], default="coupled")` chọn điều kiện
**đầu tiên** đúng, nên thứ tự trong danh sách chính là thứ tự ưu tiên. Bọc kết quả thành `pd.Series` cùng index.
