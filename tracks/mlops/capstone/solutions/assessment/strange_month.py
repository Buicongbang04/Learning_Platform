"""Sinh "tháng lạ" của M13 từ tháng thật 2019-10 của `nyc-tlc`. Đáp án của bài đánh giá: đừng mở khi đang làm M13.

Ba lỗi cài vào một mẫu 400 000 chuyến xác định theo `SEED`, mô phỏng sự cố thật của nguồn dữ liệu:

- `timezone_shift`: cả tháng, hai cột thời gian bị ghi theo UTC thay vì giờ New York (EDT, UTC-4): cộng 4 giờ.
- `unit_change`: cả tháng, `trip_distance` bị đổi sang km (nhân 1.609344, làm tròn 2 chữ số) như thể nguồn đổi đơn vị.
- `clock_error`: chuyến của hãng `VendorID == 1` đón từ 2019-10-15 tới hết 2019-10-17 (giờ địa phương) bị đảo pickup và
  dropoff (firmware đồng hồ của một hãng lỗi ba ngày), nên thời lượng âm.

Mỗi lỗi lộ ra bằng đúng công cụ người học đã dựng: `validate` của M03 chặn tỉ lệ thời lượng âm, PSI giờ đón và PSI
`trip_distance` của M10 vọt lên, `bias_s` của `monthly_quality` dương mạnh.
"""

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

MONTH = "2019-10"
SOURCE = ("nyc-tlc", MONTH)
CONTEXT = {"2019-08": "nyc-tlc", "2019-09": "nyc-tlc", "2019-11": "nyc-tlc"}
ROWS = 400_000
SEED = 1313
FAULTS = ("timezone_shift", "unit_change", "clock_error")
KEEP = ["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", "trip_distance",
        "PULocationID", "DOLocationID", "fare_amount", "total_amount"]
SHIFT = np.timedelta64(4, "h")
KM_PER_MILE = 1.609344
CLOCK_VENDOR = 1
CLOCK_START, CLOCK_END = np.datetime64("2019-10-15T00:00:00"), np.datetime64("2019-10-18T00:00:00")


def build(source: Path, out: Path) -> Path:
    table = pq.read_table(source, columns=KEEP)
    rng = np.random.default_rng(SEED)
    table = table.take(np.sort(rng.choice(table.num_rows, size=ROWS, replace=False)))
    frame = table.to_pandas()
    pickup = frame["tpep_pickup_datetime"].to_numpy()
    dropoff = frame["tpep_dropoff_datetime"].to_numpy()
    broken = (frame["VendorID"].to_numpy() == CLOCK_VENDOR) & (pickup >= CLOCK_START) & (pickup < CLOCK_END)
    pickup, dropoff = np.where(broken, dropoff, pickup), np.where(broken, pickup, dropoff)
    frame["tpep_pickup_datetime"] = pickup + SHIFT
    frame["tpep_dropoff_datetime"] = dropoff + SHIFT
    frame["trip_distance"] = (frame["trip_distance"] * KM_PER_MILE).round(2)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".parquet.tmp")
    pq.write_table(pa.Table.from_pandas(frame[KEEP], schema=table.schema, preserve_index=False), tmp)
    tmp.replace(out)
    return out
