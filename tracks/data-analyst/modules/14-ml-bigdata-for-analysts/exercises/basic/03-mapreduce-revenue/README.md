---
title: MapReduce bằng tay - doanh thu theo nước và từ khoá sản phẩm trên Online Retail II
level: basic
services: []
files:
  - path: starter/mapreduce_revenue.ipynb
    note: 7 hàm TODO + so kết quả và thời gian với pandas
  - path: tests/test_mapreduce_revenue.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/basic/03-mapreduce-revenue/starter/mapreduce_revenue.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/basic/03-mapreduce-revenue -q
---

## Mục tiêu

Hiểu MapReduce (nền của Hadoop và Spark) bằng cách tự làm: chia khối, map trên từng khối, reduce các kết quả từng
phần, chạy song song bằng `multiprocessing`; kiểm kết quả khớp `groupby` của pandas và thấy vì sao song song không
tự động nhanh hơn.

## Đề bài

Đội data platform muốn chuyển báo cáo doanh thu sang Spark. Head of Analytics hỏi Spark làm gì khác pandas, kết quả
có giống nhau không, và với dữ liệu hiện tại có nhanh hơn không. Dữ liệu: bộ `online-retail-ii`, sheet
`Year 2010-2011`, dòng hợp lệ theo định nghĩa dùng chung của track. Mở `starter/mapreduce_revenue.ipynb`:

1. `valid_lines(tx)`: dòng hợp lệ kèm cột `revenue`; `split_chunks(df, n_chunks)`: `n_chunks` khối liên tiếp, cỡ chênh
   tối đa 1 dòng, `ValueError` khi `n_chunks < 1`.
2. `map_revenue(chunk)`: doanh thu theo `Country` của một khối; `map_words(chunk)`: đếm từ `a-z` (chữ thường) trong
   `Description` của dòng hợp lệ, bỏ NaN.
3. `reduce_counts(partials)`: cộng các dict từng phần theo khoá.
4. `run_mapreduce(df, mapper, n_workers)`: chia khối, map (tuần tự khi 1 worker, `multiprocessing.Pool` khi nhiều hơn),
   reduce; `pandas_revenue(tx)`: cùng câu hỏi bằng một lần `groupby`.
5. Chạy các cell `explore`: so kết quả, top nước, top từ, đo thời gian với 1, 2, 4 worker.

Cell đầu notebook đọc xlsx một lần (20-90 giây) rồi lưu bản parquet vào thư mục tạm của hệ điều hành. Không ghi gì vào
`data/raw/`. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: lọc đúng định nghĩa dùng chung, chia khối đúng cỡ và nối lại ra dữ liệu gốc, tách từ
  đúng (dấu `/`, `,`, hai khoảng trắng), reduce giữ khoá chỉ có ở một khối, kết quả 1 và 3 worker khớp pandas.
- Trên bộ thật: 38 nước, tổng 10 666 702.54 GBP, United Kingdom 9 025 222.08 GBP, top 3 là United Kingdom,
  Netherlands, EIRE; 2 062 từ khác nhau, top 5 là `set`, `of`, `bag`, `red`, `heart`.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`np.array_split(np.arange(len(df)), n)` cho vị trí dòng của từng khối; `df.iloc[idx]` lấy khối. Đừng chia theo giá trị
`Country`: map phải chạy được trên một khối bất kỳ, như một block HDFS không biết gì về nội dung.

### Gợi ý 2

`Pool.map` gửi hàm và khối dữ liệu sang tiến trình con bằng `pickle`. Với start method `"fork"` (Linux) tiến trình con
thừa hưởng mọi hàm đã định nghĩa trong notebook. Với `"spawn"` (mặc định trên Windows, macOS) hàm định nghĩa trong
notebook không gửi được; khi đó chạy bài trên Linux/WSL, hoặc chuyển hàm map ra một tệp `.py` rồi import. Trên hệ điều
hành không có `"fork"` (Windows), các test chạy nhiều worker và hai test trên dữ liệu thật tự SKIP kèm lý do.
