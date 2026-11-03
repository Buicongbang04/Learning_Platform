"""Feature repo Feast: tốc độ trung bình theo zone. Chỉ chạy trong container (mlops-feast), không import ở host."""
from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64

zone = None
zone_speed = None
