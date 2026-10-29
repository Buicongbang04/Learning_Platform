import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

from testkit import Exercise

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"data_{name}", DATA / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass cần module có trong sys.modules lúc exec
    sys.path.insert(0, str(DATA))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(DATA))
    return module


@pytest.fixture()
def no_kaggle_env(monkeypatch, tmp_path):
    for key in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
        monkeypatch.setenv(key, "")  # ghi nhận giá trị gốc để khôi phục sau test
        monkeypatch.delenv(key)
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path / "no-kaggle"))
    return tmp_path


def test_registry_entries_complete():
    dd = load("download_dataset")
    assert {"cookie-cats", "ab-data", "hillstrom", "lalonde", "prop99", "card", "store-sales", "telco-churn", "movielens", "creditcard-fraud"} <= set(dd.DATASETS)
    for ds in dd.DATASETS.values():
        assert ds.source in ("kaggle", "url")
        assert ds.ref and ds.files and ds.license and ds.homepage


def test_token_from_env_file_is_exported(no_kaggle_env, monkeypatch):
    env = no_kaggle_env / ".env"
    env.write_text("# x\nKAGGLE_API_TOKEN='KGAT_abc'\n")
    assert load("download_olist").ensure_kaggle_credentials(env_file=env) is True
    assert __import__("os").environ["KAGGLE_API_TOKEN"] == "KGAT_abc"


def test_legacy_username_key_still_supported(no_kaggle_env, monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "me")
    monkeypatch.setenv("KAGGLE_KEY", "k")
    assert load("download_olist").ensure_kaggle_credentials(env_file=no_kaggle_env / "none") is True


def test_no_credentials_detected(no_kaggle_env):
    assert load("download_olist").ensure_kaggle_credentials(env_file=no_kaggle_env / "none") is False


def test_missing_kaggle_credentials_exits_cleanly(no_kaggle_env, monkeypatch):
    dd = load("download_dataset")
    monkeypatch.setattr(dd, "ENV_FILE", no_kaggle_env / "none")
    with pytest.raises(SystemExit) as exc:
        dd.main(["cookie-cats", "--out", str(no_kaggle_env / "out")])
    assert exc.value.code not in (0, None)
    assert "KAGGLE_API_TOKEN" in str(exc.value.code)


def test_kaggle_download_copies_only_listed_files(monkeypatch, tmp_path):
    olist = load("download_olist")
    cache = tmp_path / "cache"
    (cache / "sub").mkdir(parents=True)
    (cache / "sub" / "cookie_cats.csv").write_text("userid,version\n1,gate_30\n")
    (cache / "readme.txt").write_text("x")
    monkeypatch.setattr(olist.kagglehub, "dataset_download", lambda ref: str(cache))
    out = tmp_path / "out"
    assert olist.kaggle_download("a/b", out, ["cookie_cats.csv"]) == [out / "cookie_cats.csv"]
    assert sorted(p.name for p in out.iterdir()) == ["cookie_cats.csv"]


def test_kaggle_download_reports_missing_file(monkeypatch, tmp_path):
    olist = load("download_olist")
    monkeypatch.setattr(olist.kagglehub, "dataset_download", lambda ref: str(tmp_path))
    with pytest.raises(SystemExit, match="cookie_cats.csv"):
        olist.kaggle_download("a/b", tmp_path / "out", ["cookie_cats.csv"])


def test_url_download_writes_file(monkeypatch, tmp_path):
    dd = load("download_dataset")

    class Resp:
        status_code = 200
        content = b"recency,history\n10,142.44\n"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(dd.requests, "get", lambda *a, **k: Resp())
    paths = dd.download("hillstrom", tmp_path)
    assert paths == [tmp_path / "hillstrom.csv"]
    assert (tmp_path / "hillstrom.csv").read_bytes() == Resp.content


def test_dataset_skips_when_missing():
    ex = Exercise(str(Path(__file__).parent / "fixtures/nb_exercise/exercises/basic/01-demo/tests/locate.py"))
    with pytest.raises(pytest.skip.Exception, match="download_dataset.py khong-co"):
        ex.dataset("khong-co")


def _url_dataset(dd, ref, files):
    return dd.Dataset("url", ref, files, license="x", homepage="x")


def test_url_base_dir_downloads_each_name(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-dir", _url_dataset(dd, "http://h/d/", ["a.csv", "b.csv"]))
    asked = []
    monkeypatch.setattr(dd, "_get", lambda url: asked.append(url) or url.encode())
    out = tmp_path / "out"
    paths = dd.download("t-dir", out)
    assert asked == ["http://h/d/a.csv", "http://h/d/b.csv"]
    assert paths == [out / "a.csv", out / "b.csv"]
    assert (out / "b.csv").read_bytes() == b"http://h/d/b.csv"


def _zip_bytes(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members:
            zf.writestr(name, data)
    return buf.getvalue()


def test_zip_extracts_only_requested_and_ignores_shadows(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-zip", _url_dataset(dd, "http://h/x.zip", ["ratings.csv"]))
    blob = _zip_bytes([
        ("ml-latest-small/ratings.csv", b"REAL"),
        ("__MACOSX/ml-latest-small/ratings.csv", b"SHADOW"),
        ("__MACOSX/._ratings.csv", b"SHADOW2"),
        ("../evil.csv", b"EVIL"),
        ("ml-latest-small/other.csv", b"OTHER"),
    ])
    monkeypatch.setattr(dd, "_get", lambda url: blob)
    out = tmp_path / "sub" / "out"
    paths = dd.download("t-zip", out)
    assert paths == [out / "ratings.csv"]
    assert (out / "ratings.csv").read_bytes() == b"REAL"
    assert sorted(p.name for p in out.iterdir()) == ["ratings.csv"]
    assert not (tmp_path / "evil.csv").exists() and not (tmp_path / "sub" / "evil.csv").exists()


def test_zip_missing_member_names_it(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-zip2", _url_dataset(dd, "http://h/x.zip", ["nope.csv"]))
    monkeypatch.setattr(dd, "_get", lambda url: _zip_bytes([("d/a.csv", b"1")]))
    with pytest.raises(SystemExit, match="nope.csv"):
        dd.download("t-zip2", tmp_path)
