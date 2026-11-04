from datetime import timedelta

from feast import FeatureView, Field, FileSource, PushSource
from feast.types import Float64, Int64
from features import pu_zone

zone_speed_15m_source = FileSource(
    name="zone_speed_15m_source",
    path="data/zone_speed_15m.parquet",
    timestamp_field="event_timestamp",
)

zone_speed_push = PushSource(name="zone_speed_push", batch_source=zone_speed_15m_source)

zone_speed_15m = FeatureView(
    name="zone_speed_15m",
    entities=[pu_zone],
    ttl=timedelta(minutes=30),
    schema=[Field(name="speed_15m_mph", dtype=Float64), Field(name="trips", dtype=Int64)],
    source=zone_speed_push,
    online=True,
    description="Tốc độ trung bình (dặm/giờ) theo zone đón trong cửa sổ 15 phút theo lúc trả khách; event_timestamp = cuối cửa sổ",
)
