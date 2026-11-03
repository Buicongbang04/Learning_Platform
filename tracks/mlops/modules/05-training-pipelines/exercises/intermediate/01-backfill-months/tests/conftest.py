import pytest
from prefect.settings import PREFECT_LOCAL_STORAGE_PATH, temporary_settings
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(scope="session", autouse=True)
def prefect_harness(tmp_path_factory):
    storage = tmp_path_factory.mktemp("prefect-storage")
    with temporary_settings({PREFECT_LOCAL_STORAGE_PATH: storage}), prefect_test_harness():
        yield
