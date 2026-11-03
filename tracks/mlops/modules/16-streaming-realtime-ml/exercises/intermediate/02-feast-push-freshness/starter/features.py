from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource, PushSource
from feast.types import Float64, Int64
from feast.value_type import ValueType

# TODO 1: entity `zone` (join key `zone_id`, INT64)
# TODO 2: FileSource `data/zone_window.parquet` (timestamp_field `event_timestamp`) làm batch source
# TODO 3: PushSource tên `zone_window_push`
# TODO 4: FeatureView `zone_window`: trips (Int64), avg_fare (Float64), nguồn là push source, ttl từ 1 đến 24 giờ
