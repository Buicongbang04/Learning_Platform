import configparser
import os
import uuid

import pytest

import mlopskit
from testkit import Exercise, run_sandboxed

ex = Exercise(__file__)
KEY = os.environ.get("MINIO_ROOT_USER", "minioadmin")
SECRET = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
BUCKET = "dvc"


def s3():
    import boto3

    return boto3.client(
        "s3", endpoint_url=f"http://127.0.0.1:{mlopskit.stack_port('minio')}",
        aws_access_key_id=KEY, aws_secret_access_key=SECRET, region_name="us-east-1",
    )


def sh(repo, cmd, args=()):
    env = {
        "DVC_NO_ANALYTICS": "1",
        "DVC_SITE_CACHE_DIR": str(repo / ".site"),
        "DVC_GLOBAL_CONFIG_DIR": str(repo / ".gc"),
        "AWS_ACCESS_KEY_ID": KEY, "AWS_SECRET_ACCESS_KEY": SECRET, "AWS_DEFAULT_REGION": "us-east-1",
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    result = run_sandboxed(["bash", "-c", cmd, "bash", *args], writable=[repo], cwd=repo, env=env, timeout=180)
    assert result.returncode == 0, f"{cmd}\n{result.stdout}\n{result.stderr}"
    return result


@pytest.fixture()
def lab(tmp_path):
    ex.require_tool("dvc")
    ex.require_tool("git")
    mlopskit.require_stack("minio")
    prefix = f"mlops-ex-m03-{uuid.uuid4().hex[:10]}"
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "remote.sh").write_text(ex.read("remote.sh"))
    (repo / "data" / "trips.csv").write_text("trip_id,distance\n" + "".join(f"{i},{i * 0.7}\n" for i in range(200)))
    sh(repo, "git init -q -b main . && dvc init -q && printf '/.site\\n/.gc\\n' >> .git/info/exclude && dvc add data/trips.csv")
    client = s3()
    try:
        yield repo, prefix, client
    finally:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                client.delete_object(Bucket=BUCKET, Key=obj["Key"])


def run_script(repo, prefix):
    endpoint = f"http://127.0.0.1:{mlopskit.stack_port('minio')}"
    sh(repo, 'bash remote.sh "$1" "$2" "$3"', (f"s3://{BUCKET}/{prefix}", endpoint, "data/trips.csv"))
    return endpoint


def test_config_has_remote_without_secrets(lab):
    repo, prefix, _ = lab
    endpoint = run_script(repo, prefix)
    text = (repo / ".dvc" / "config").read_text()
    assert SECRET not in text
    parser = configparser.ConfigParser()
    parser.read(repo / ".dvc" / "config")
    section = parser["'remote \"storage\"'"]
    assert section["url"] == f"s3://{BUCKET}/{prefix}"
    assert section["endpointurl"] == endpoint
    assert parser["core"]["remote"] == "storage"
    assert "secret" not in text.lower() and "access_key" not in text.lower()


def test_objects_land_under_prefix(lab):
    repo, prefix, client = lab
    run_script(repo, prefix)
    keys = [o["Key"] for o in client.list_objects_v2(Bucket=BUCKET, Prefix=prefix).get("Contents", [])]
    assert keys, f"Không có đối tượng nào dưới s3://{BUCKET}/{prefix}"
    assert any("/md5/" in k for k in keys)


def test_pull_restores_after_cache_wipe(lab):
    repo, prefix, _ = lab
    run_script(repo, prefix)
    original = (repo / "data" / "trips.csv").read_text()
    sh(repo, "rm -rf .dvc/cache data/trips.csv")
    assert not (repo / "data" / "trips.csv").exists()
    sh(repo, "dvc pull")
    assert (repo / "data" / "trips.csv").read_text() == original
