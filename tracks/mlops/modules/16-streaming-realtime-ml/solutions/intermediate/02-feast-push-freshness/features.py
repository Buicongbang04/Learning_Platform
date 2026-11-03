from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource, PushSource
from feast.types import Float64, Int64
from feast.value_type import ValueType

zone = Entity(name="zone", join_keys=["zone_id"], value_type=ValueType.INT64)

zone_window_batch = FileSource(path="data/zone_window.parquet", timestamp_field="event_timestamp")

zone_window_push = PushSource(name="zone_window_push", batch_source=zone_window_batch)

zone_window = FeatureView(
    name="zone_window",
    entities=[zone],
    ttl=timedelta(hours=6),
    schema=[Field(name="trips", dtype=Int64), Field(name="avg_fare", dtype=Float64)],
    source=zone_window_push,
    online=True,
)
