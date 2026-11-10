import pandas as pd
import pandera.pandas as pa


def trip_schema(month: str) -> pa.DataFrameSchema:
    start = pd.Timestamp(month + "-01")
    end = start + pd.offsets.MonthBegin(1)
    # TODO 1: cột tpep_pickup_datetime, tpep_dropoff_datetime kiểu datetime; pickup phải trong [start, end)
    # TODO 2: trip_distance kiểu float, lớn hơn 0
    # TODO 3: PULocationID, DOLocationID kiểu int, trong [1, 265]
    # TODO 4: passenger_count float, cho phép NaN
    # TODO 5: luật nhiều cột: dropoff phải muộn hơn pickup
    raise NotImplementedError


def validate_trips(df: pd.DataFrame, month: str) -> pd.DataFrame:
    # TODO: validate lazy để gom mọi lỗi
    raise NotImplementedError
