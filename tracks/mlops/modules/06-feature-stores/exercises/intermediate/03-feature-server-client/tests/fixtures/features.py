from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource
from feast.types import Float32, Int64

zone = Entity(name="zone", join_keys=["zone_id"])

zone_stats = FileSource(path="data/zone_stats.parquet", timestamp_field="event_timestamp")

zone_speed = FeatureView(
    name="zone_speed",
    entities=[zone],
    ttl=timedelta(days=3),
    schema=[Field(name="avg_speed_mph", dtype=Float32), Field(name="trip_count", dtype=Int64)],
    source=zone_stats,
)

zone_service = FeatureService(name="zone_service", features=[zone_speed])
