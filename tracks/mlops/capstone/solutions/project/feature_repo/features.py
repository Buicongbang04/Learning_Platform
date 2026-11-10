from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource, ValueType
from feast.types import Float64

pu_zone = Entity(name="pu_zone", join_keys=["PULocationID"], value_type=ValueType.INT64,
                 description="Zone đón khách (TLC LocationID 1..263)")
pickup_hour = Entity(name="pickup_hour", join_keys=["pickup_hour"], value_type=ValueType.INT64,
                     description="Giờ đón theo giờ địa phương New York, 0..23")

zone_hour_speed_source = FileSource(
    name="zone_hour_speed_source",
    path="data/zone_hour_speed.parquet",
    timestamp_field="event_timestamp",
)

zone_hour_speed = FeatureView(
    name="zone_hour_speed",
    entities=[pu_zone, pickup_hour],
    ttl=timedelta(days=62),
    schema=[Field(name="avg_speed_mph", dtype=Float64)],
    source=zone_hour_speed_source,
    online=True,
    description="Trung vị tốc độ (dặm/giờ) theo zone đón và giờ của tháng trước; event_timestamp = đầu tháng sau",
)
