"""Chọn thư mục được chấm: `capstone/project/` của bạn, hoặc bản tham chiếu `capstone/solutions/project/` khi SOLUTION=1.

Test import package `eta` từ `<project>/src` qua `etakit.need("data")`: thiếu module hay thiếu tên thì test fail kèm
thông báo, không lỗi lúc thu thập test.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etakit import PROJECT, synthetic_month


@pytest.fixture(scope="session")
def project() -> Path:
    if not PROJECT.is_dir():
        pytest.fail(f"Chưa có thư mục {PROJECT}", pytrace=False)
    return PROJECT


@pytest.fixture
def tiny_parquet(tmp_path) -> Path:
    path = tmp_path / "yellow_tripdata_2019-01.parquet"
    synthetic_month(1_000, seed=1).to_parquet(path, index=False)
    return path


@pytest.fixture(scope="session")
def synthetic_trips() -> pd.DataFrame:
    frame = synthetic_month(6_000, seed=2, extra_columns=False)
    frame["duration_s"] = (frame["tpep_dropoff_datetime"] - frame["tpep_pickup_datetime"]).dt.total_seconds()
    return frame


@pytest.fixture
def dirty_frame() -> pd.DataFrame:
    rows = [
        ("2019-01-05 08:00:00", 900, 161, 236, 2.5),
        ("2019-01-10 12:00:00", 60, 48, 48, 0.3),
        ("2019-01-31 23:59:00", 10_800, 132, 230, 100.0),
        ("2019-01-01 00:00:00", 1_500, 138, 79, 9.1),
        ("2019-01-20 17:30:00", 2_000, 263, 1, 4.0),
        ("2019-01-12 09:00:00", -300, 161, 162, 1.2),
        ("2019-01-13 11:00:00", 10_801, 237, 236, 3.0),
        ("2019-01-14 12:00:00", 700, 237, 236, 0.0),
        ("2019-01-15 13:00:00", 1_800, 132, 1, 150.0),
        ("2018-12-31 23:50:00", 900, 161, 230, 2.0),
        ("2019-01-16 14:00:00", 600, 264, 161, 1.5),
        ("2019-01-17 15:00:00", 600, 161, 265, 1.5),
    ]
    pickup = pd.to_datetime([r[0] for r in rows]).astype("datetime64[us]")
    return pd.DataFrame(
        {
            "tpep_pickup_datetime": pickup,
            "tpep_dropoff_datetime": pickup + pd.to_timedelta([r[1] for r in rows], unit="s"),
            "PULocationID": [r[2] for r in rows],
            "DOLocationID": [r[3] for r in rows],
            "trip_distance": [r[4] for r in rows],
        }
    )


@pytest.fixture(scope="session")
def prefect_harness(tmp_path_factory):
    """Prefect không cần server: API tạm của `prefect_test_harness`, kết quả task lưu trong thư mục tạm."""
    from prefect.settings import PREFECT_HOME, PREFECT_LOCAL_STORAGE_PATH, temporary_settings
    from prefect.testing.utilities import prefect_test_harness

    home = tmp_path_factory.mktemp("prefect-home")
    with temporary_settings({PREFECT_HOME: home, PREFECT_LOCAL_STORAGE_PATH: home / "storage"}), prefect_test_harness():
        yield home
