import pandas as pd

FEATURES = ["trip_distance", "hour", "dow", "PULocationID", "DOLocationID"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: trả DataFrame đúng các cột và thứ tự của FEATURES (hour, dow lấy từ giờ đón)
    raise NotImplementedError
