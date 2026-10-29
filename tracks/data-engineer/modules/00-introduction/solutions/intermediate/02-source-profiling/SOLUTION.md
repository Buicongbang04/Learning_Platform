# Lời giải: profile bốn nguồn thật

## Cách làm

1. **`profile`** sắp `ts` một lần, tính `diff()` giây. Mọi chỉ số còn lại là phép vector hoá:
   `duplicated()`, `duplicated(key)`, `isin(sentinels)`, `isna().mean()`. Không sửa `df` (profiler chỉ quan sát).
   Sentinel chỉ tính khi khai báo: profiler không đoán `-200` hay `0` là thiếu, người hiểu nguồn khai báo.
2. **`gaps`** lọc `step > min_gap_s`, ghép điểm trước/sau theo vị trí.
3. **`footprint`** đo cỡ tệp **sau khi ghi** (không ước lượng bằng `memory_usage`), ghi đè cùng đường dẫn.
4. **`compare`/`write_clean`**: `DataFrame.from_dict(orient="index")`; ghi qua tệp tạm.

## Vì sao

Ba câu hỏi đầu tiên trước khi chọn công nghệ (volume, velocity, chất lượng) đều trả lời được bằng một profiler
nhỏ chạy trên mẫu thật. Con số làm cho cuộc tranh luận "có cần Kafka không" ngắn lại: nguồn nhanh nhất ở đây là
2,7 GB/năm.

## Con số tham chiếu

| | Log NASA | IoT UCI |
| --- | --- | --- |
| `rows` | 1 891 714 | 9 357 |
| `rows_per_day` | 68 629 | 24,00 |
| `median_interval_s` / `max_gap_s` | 1 / 1 326 | 3 600 / 3 600 |
| `max_gap_start` | 1995-07-13 23:48:59 | |
| `duplicate_rows` / `duplicate_keys` | 835 / None | 0 / 0 |
| `sentinel_count` | 0 | 16 701 |
| `worst_null_column` (`share`) | | `NMHC(GT)` (0,902) |
| `raw_bytes_per_row` | 108,5 | 83,9 |
| `compression_ratio` (zstd) | 13,7 | 3,0 |

USGS (nếu đã thu thập 2 lượt): 6 398 dòng thô, `duplicate_keys = 1`, nén ×31.
