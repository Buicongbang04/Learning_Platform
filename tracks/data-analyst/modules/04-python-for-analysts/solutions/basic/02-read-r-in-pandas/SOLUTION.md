# Lời giải: đọc code R và chọn bản pandas tương đương

## Cách làm

Dịch từng động từ theo bảng ở phần 5 lý thuyết, rồi tự hỏi ba câu trước khi chọn:

1. Kết quả có **bao nhiêu dòng**? (`summarise` → một dòng mỗi nhóm; `mutate` → giữ nguyên; `slice_*` → chọn dòng.)
2. Đếm **dòng** hay đếm **giá trị khác nhau**, và giá trị thiếu được xử lý thế nào ở mỗi bên?
3. Có tham số nào chỉ để **kiểm** (báo lỗi khi dữ liệu sai), như `relationship` hay việc `pivot_wider` gặp khoá trùng?
   Bản dịch phải giữ cả phần kiểm, không chỉ phần tính.

## Đáp án từng câu

| Câu | Đáp án | Lý do ngắn |
| --- | --- | --- |
| `filter-summarise` | b | Dấu phẩy trong `filter` là AND; `!is.na(iso_code)` là `notna()`. (a) quên bỏ dòng tổng, (c) lấy đúng dòng tổng, (d) tính trung bình |
| `na-rm` | c | `mean()` của R không bỏ `NA` nếu thiếu `na.rm = TRUE`; pandas `skipna=True` mặc định |
| `n-vs-n-distinct` | b | `n_distinct` = `nunique`, `n()` = `size`. `count` đếm giá trị khác null, không phải giá trị khác nhau |
| `group-mutate` | a | `group_by` + `mutate` giữ số dòng = `transform`. (b) thu về một dòng mỗi nước, (c) chia cho tổng toàn bảng |
| `lag-gap` | b | `lag` và `shift` đều lấy **dòng** liền trước: năm 1944. Muốn "năm trước" phải ghép theo `year + 1` (bài Basic 01) |
| `pivot-longer` | d | `cols = -country` nghĩa là mọi cột trừ `country` → `id_vars="country"`. Trong R cột `year` là chuỗi (lấy từ tên cột); pandas giữ kiểu nhãn cột, đọc từ CSV/Excel thường cũng là chuỗi: ép số |
| `pivot-wider` | b | `pivot_wider` gặp khoá trùng thì cảnh báo và tạo cột list, không cộng; bản pandas giữ tinh thần "không cộng lặng lẽ" là `pivot` (báo lỗi). `pivot_table(aggfunc="sum")` cộng mất dấu |
| `left-join-relationship` | a | `relationship = "many-to-one"` = `validate="many_to_one"`: báo lỗi khi bảng tra trùng khoá. (d) che lỗi nhân dòng bằng `drop_duplicates`, còn xoá cả dòng trùng thật |
| `geom-bar` | c | `geom_bar()` không có `y` thì đếm dòng mỗi nhóm = `countplot`. (a) `barplot` vẽ trung bình `Quantity` kèm khoảng tin cậy |
| `facet-free-y` | d | `facet_wrap(~country)` = `col="country"`; `scales = "free_y"` = `facet_kws={"sharey": False}`. (c) thả trục x, không phải trục y |
| `slice-max` | b | `idxmax` theo nhóm trả nhãn dòng lớn nhất mỗi nước, `loc` lấy đủ cột. (a), (d) chỉ lấy một dòng cho cả bảng; (c) mất các cột khác |
| `keep-r` | c | Chọn công cụ theo nhóm đang dùng: codebase R có test và CI, 6 người viết R. Viết lại (a) tốn tháng và rủi ro ra số khác; hai ngôn ngữ song song (b) làm báo cáo khó bảo trì |

## Ghi chú về `pivot-wider`

Trong tidyr, `pivot_wider` gặp hai dòng cùng `(country, year)` không báo lỗi cứng mà cảnh báo "values are not uniquely
identified" và tạo cột kiểu list. Đó vẫn là tín hiệu dữ liệu bẩn mà người đọc thấy được; `pivot` của pandas báo lỗi
hẳn. Bản dịch sai là bản làm tín hiệu đó biến mất (`pivot_table` với `aggfunc="sum"`, hoặc `groupby().sum()`).

## Ghi chú về `keep-r`

Không có ngôn ngữ "tốt hơn" cho DA. Câu hỏi chọn công cụ luôn gồm: ai dùng kết quả, dữ liệu ở đâu, có cần tái lập và
review không, và **nhóm đang dùng gì**. Ở đây câu cuối quyết định: chi phí chuyển đổi (viết lại, kiểm lại mọi con
số, đào tạo lại 6 người) lớn hơn nhiều chi phí bạn học đọc và viết R ở mức đủ dùng trong vài tuần.
