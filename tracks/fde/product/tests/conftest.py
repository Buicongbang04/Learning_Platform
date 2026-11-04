import time
import uuid

import psycopg
import pytest

import release
import testkit
from fake_llm import FakeOpenAI
from quillo_support import make_settings

PG_USER, PG_PASSWORD = "quillo", "quillo-test-only"


@pytest.fixture(scope="session")
def postgres() -> str:
    if not testkit.docker_ready():
        pytest.skip("Cần Docker đang chạy để dựng Postgres/pgvector (testkit.DockerLab)")
    image = release.IMAGES["db"]
    testkit.Exercise.require_image(image)
    with testkit.DockerLab() as lab:
        lab.start("db", image, ports=(5432,), env={"POSTGRES_USER": PG_USER, "POSTGRES_PASSWORD": PG_PASSWORD},
                  memory="512m")
        dsn = f"postgresql://{PG_USER}:{PG_PASSWORD}@127.0.0.1:{lab.port('db', 5432)}"
        deadline = time.monotonic() + 60
        while True:
            try:
                with psycopg.connect(f"{dsn}/postgres", connect_timeout=2) as conn:
                    conn.execute("SELECT 1")
                break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    pytest.fail(f"Postgres không sẵn sàng sau 60 giây. Log:\n{lab.logs('db')[-2000:]}")
                time.sleep(0.5)
        yield dsn


@pytest.fixture
def database_url(postgres: str):
    name = f"t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(f"{postgres}/postgres", autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    yield f"{postgres}/{name}"
    with psycopg.connect(f"{postgres}/postgres", autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")


@pytest.fixture
def fake_llm():
    with FakeOpenAI() as fake:
        yield fake


@pytest.fixture
def client(database_url, fake_llm):
    from fastapi.testclient import TestClient

    from quillo.app import create_app

    with TestClient(create_app(make_settings(database_url, fake_llm.url))) as test_client:
        yield test_client

