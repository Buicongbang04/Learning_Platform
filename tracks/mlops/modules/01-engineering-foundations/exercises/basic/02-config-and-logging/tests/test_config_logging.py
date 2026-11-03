import io
import json
import uuid
from pathlib import Path

import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def settings_mod():
    return ex.module("settings.py")


@pytest.fixture(scope="module")
def jsonlog():
    return ex.module("jsonlog.py")


def write_yaml(tmp_path, text):
    path = tmp_path / "conf" / "config.yaml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_come_from_dataclass_and_data_path_is_required(settings_mod, tmp_path):
    with pytest.raises(ValueError, match="data_path"):
        settings_mod.load_settings(env={})
    settings = settings_mod.load_settings(env={"ETA_DATA_PATH": "/data/trips.parquet"})
    assert settings.data_path == Path("/data/trips.parquet")
    assert settings.seed == 0 and settings.max_iter == 100 and settings.log_level == "INFO"
    assert settings.model_dir.is_absolute()


def test_yaml_overrides_defaults_and_env_overrides_yaml(settings_mod, tmp_path):
    path = write_yaml(tmp_path, "data_path: /data/a.parquet\nseed: 7\nlog_level: DEBUG\n")
    from_yaml = settings_mod.load_settings(path, env={})
    assert (from_yaml.seed, from_yaml.log_level) == (7, "DEBUG")
    from_env = settings_mod.load_settings(path, env={"ETA_SEED": "11", "ETA_DATA_PATH": "/data/b.parquet"})
    assert from_env.seed == 11
    assert from_env.data_path == Path("/data/b.parquet")
    assert from_env.log_level == "DEBUG"


def test_relative_yaml_paths_resolve_from_the_yaml_directory(settings_mod, tmp_path, monkeypatch):
    path = write_yaml(tmp_path, "data_path: ../data/trips.parquet\nmodel_dir: out\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    settings = settings_mod.load_settings(path, env={})
    assert settings.data_path == (tmp_path / "data" / "trips.parquet").resolve()
    assert settings.model_dir == (tmp_path / "conf" / "out").resolve()


def test_relative_env_and_default_paths_resolve_from_cwd(settings_mod, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = settings_mod.load_settings(env={"ETA_DATA_PATH": "data/x.parquet"})
    assert settings.data_path == (tmp_path / "data" / "x.parquet").resolve()
    assert settings.model_dir == (tmp_path / "models").resolve()


def test_unknown_yaml_key_and_bad_numbers_are_rejected(settings_mod, tmp_path):
    typo = write_yaml(tmp_path, "data_path: /d.parquet\nsed: 3\n")
    with pytest.raises(ValueError, match="sed"):
        settings_mod.load_settings(typo, env={})
    with pytest.raises(ValueError, match="seed"):
        settings_mod.load_settings(env={"ETA_DATA_PATH": "/d.parquet", "ETA_SEED": "abc"})


def test_reads_process_environment_when_env_is_none(settings_mod, monkeypatch):
    monkeypatch.setenv("ETA_DATA_PATH", "/from/os/environ.parquet")
    monkeypatch.setenv("ETA_MAX_ITER", "25")
    settings = settings_mod.load_settings()
    assert settings.data_path == Path("/from/os/environ.parquet")
    assert settings.max_iter == 25


def test_example_config_is_loadable(settings_mod, tmp_path):
    example = ex.path("config.example.yaml")
    settings = settings_mod.load_settings(example, env={})
    assert settings.data_path.name == "yellow_tripdata_2019-01.parquet"


def logger_with_buffer(jsonlog, level="INFO"):
    buffer = io.StringIO()
    return jsonlog.configure_logging(level, buffer, name=f"eta-test-{uuid.uuid4().hex[:6]}"), buffer


def test_each_log_line_is_one_json_object_with_extras(jsonlog):
    logger, buffer = logger_with_buffer(jsonlog)
    logger.info("train done", extra={"run_id": "r1", "mae": 3.2})
    logger.warning("slow")
    lines = buffer.getvalue().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["level"] == "INFO" and first["msg"] == "train done"
    assert first["run_id"] == "r1" and first["mae"] == 3.2
    assert first["ts"].endswith("+00:00") and first["logger"].startswith("eta-test-")
    assert json.loads(lines[1])["level"] == "WARNING"


def test_secrets_are_redacted_and_exceptions_are_kept(jsonlog):
    logger, buffer = logger_with_buffer(jsonlog)
    logger.info("connect", extra={"db_password": "hunter2", "Api_Key": "abc", "host": "db"})
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("boom")
    first, second = (json.loads(line) for line in buffer.getvalue().strip().splitlines())
    assert first["db_password"] == "***" and first["Api_Key"] == "***" and first["host"] == "db"
    assert "hunter2" not in buffer.getvalue()
    assert "ZeroDivisionError" in second["exc"]


def test_configure_twice_does_not_duplicate_lines_and_respects_level(jsonlog):
    name = f"eta-test-{uuid.uuid4().hex[:6]}"
    first, second = io.StringIO(), io.StringIO()
    jsonlog.configure_logging("INFO", first, name=name)
    logger = jsonlog.configure_logging("ERROR", second, name=name)
    logger.info("hidden")
    logger.error("shown")
    assert first.getvalue() == ""
    assert len(second.getvalue().strip().splitlines()) == 1
    assert len(logger.handlers) == 1
    assert logger.propagate is False
