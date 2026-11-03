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
    assert {"cookie-cats", "ab-data", "hillstrom", "lalonde", "prop99", "card", "store-sales", "telco-churn", "movielens", "creditcard-fraud", "bike-sharing-uci", "online-retail-ii", "dunnhumby-complete-journey", "grocery-sales-synthetic", "marketing-ab", "ecommerce-events", "owid-co2", "mnist", "zalo-legal"} <= set(dd.DATASETS)
    for ds in dd.DATASETS.values():
        assert ds.source in ("kaggle", "url", "hf")
        assert ds.ref and ds.files and ds.license and ds.homepage
        assert ds.homepage.startswith("https://")


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
        headers = {"content-type": "text/csv"}
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


def _html_resp():
    class Resp:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        content = b"<html>Quota exceeded</html>"

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield self.content

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return Resp()


def test_html_response_single_url_is_rejected(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setattr(dd.requests, "get", lambda *a, **k: _html_resp())
    with pytest.raises(SystemExit, match="HTML"):
        dd.download("hillstrom", tmp_path)


def test_html_response_tuple_url_is_rejected(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-tuple", _url_dataset(dd, ("http://h/a", "http://h/b"), ["a.csv", "b.csv"]))
    monkeypatch.setattr(dd.requests, "get", lambda *a, **k: _html_resp())
    with pytest.raises(SystemExit, match="HTML"):
        dd.download("t-tuple", tmp_path)
    assert not (tmp_path / "a.csv").exists()


def _hf_dataset(dd, needs_token):
    return dd.Dataset("hf", "o/r", ["sub/a.json"], license="x", homepage="x", needs_token=needs_token)


def test_hf_dataset_requires_token_exits_cleanly(monkeypatch, tmp_path, capsys):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-hf", _hf_dataset(dd, True))
    monkeypatch.setenv("HF_TOKEN", "")
    monkeypatch.delenv("HF_TOKEN")
    monkeypatch.setattr(dd, "ENV_FILE", tmp_path / "none")
    with pytest.raises(SystemExit) as exc:
        dd.main(["t-hf", "--out", str(tmp_path / "out")])
    assert exc.value.code not in (0, None)
    msg = str(exc.value.code)
    assert "HF_TOKEN" in msg and "https://huggingface.co/settings/tokens" in msg


def test_hf_download_calls_hub(monkeypatch, tmp_path):
    dd = load("download_dataset")
    monkeypatch.setitem(dd.DATASETS, "t-hf", _hf_dataset(dd, False))
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    cached = tmp_path / "cache" / "a.json"
    cached.parent.mkdir()
    cached.write_text("{}")
    calls = []

    def fake(**kw):
        calls.append(kw)
        return str(cached)

    monkeypatch.setattr(dd, "hf_hub_download", fake)
    out = tmp_path / "out"
    assert dd.download("t-hf", out) == [out / "sub" / "a.json"]
    assert (out / "sub" / "a.json").read_text() == "{}"
    assert calls[0]["repo_id"] == "o/r" and calls[0]["filename"] == "sub/a.json"
    assert calls[0]["repo_type"] == "dataset" and calls[0]["token"] == "hf_x"


def test_hf_revision_is_passed_to_hub(monkeypatch, tmp_path):
    dd = load("download_dataset")
    ds = dd.Dataset("hf", "o/r", ["sub/a.json"], license="x", homepage="x", revision="refs/convert/parquet")
    monkeypatch.setitem(dd.DATASETS, "t-hf", ds)
    cached = tmp_path / "a.json"
    cached.write_text("{}")
    calls = []
    monkeypatch.setattr(dd, "hf_hub_download", lambda **kw: calls.append(kw) or str(cached))
    dd.download("t-hf", tmp_path / "out")
    assert calls[0]["revision"] == "refs/convert/parquet"


def _fake_stream(payloads):
    class Resp:
        headers = {"Content-Type": "application/octet-stream"}

        def __init__(self, data):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield self.data

    it = iter(payloads)
    return lambda *a, **k: Resp(next(it))


def test_tuple_url_extract_keeps_dirs_and_removes_archives(monkeypatch, tmp_path):
    import tarfile

    dd = load("download_dataset")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("Ped/img/a.png", "x")
        zf.writestr("Ped/mask/a_mask.png", "y")
    tbuf = io.BytesIO()
    with tarfile.open(fileobj=tbuf, mode="w:gz") as tf:
        info = tarfile.TarInfo("batches/data_1")
        info.size = 3
        tf.addfile(info, io.BytesIO(b"abc"))
    ds = dd.Dataset("url", ("http://x/a.zip", "http://x/b.tgz"), ["a.zip", "b.tgz"], license="x", homepage="x", extract=True)
    monkeypatch.setitem(dd.DATASETS, "t-ex", ds)
    monkeypatch.setattr(dd.requests, "get", _fake_stream([zbuf.getvalue(), tbuf.getvalue()]))
    out = tmp_path / "out"
    paths = dd.download("t-ex", out)
    assert (out / "Ped" / "img" / "a.png").read_text() == "x"
    assert (out / "batches" / "data_1").read_bytes() == b"abc"
    assert not (out / "a.zip").exists() and not (out / "b.tgz").exists()
    assert out / "Ped" / "mask" / "a_mask.png" in paths


def test_extract_rejects_path_traversal(monkeypatch, tmp_path):
    dd = load("download_dataset")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("../evil.txt", "x")
    ds = dd.Dataset("url", ("http://x/a.zip",), ["a.zip"], license="x", homepage="x", extract=True)
    monkeypatch.setitem(dd.DATASETS, "t-ex", ds)
    monkeypatch.setattr(dd.requests, "get", _fake_stream([zbuf.getvalue()]))
    with pytest.raises(SystemExit):
        dd.download("t-ex", tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_phase3_datasets_registered():
    dd = load("download_dataset")
    assert {"cifar10", "oxford-pets", "penn-fudan", "uit-vsfc", "iwslt15-en-vi", "wikipedia-vi", "openorca-viet", "gsm8k", "prompt-injections", "fleurs-vi", "cord-v2"} <= set(dd.DATASETS)


_NYC_TLC_OLD = {
    "source": "url",
    "ref": tuple(f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2019-{m:02d}.parquet" for m in range(1, 13))
    + ("https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv",),
    "files": [f"yellow_tripdata_2019-{m:02d}.parquet" for m in range(1, 13)] + ["taxi_zone_lookup.csv"],
    "license": "Dữ liệu mở của NYC Taxi & Limousine Commission (NYC Open Data), dùng tự do",
    "homepage": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
    "about": "Chuyến Yellow Taxi NYC, ghim 12 tháng 2019-01..2019-12 (Parquet, ~1,2 GB, ~84 triệu chuyến) + taxi_zone_lookup.csv",
}
_OXFORD_PETS_OLD = {
    "source": "hf",
    "ref": "timm/oxford-iiit-pet",
    "files": ["data/train-00000-of-00001.parquet", "data/test-00000-of-00001.parquet"],
    "license": "CC BY-SA 4.0 (Parkhi, Vedaldi, Zisserman, Jawahar 2012, VGG Oxford); bản mirror HF của timm vì thor.robots.ox.ac.uk tải rất chậm (~1 MB/phút)",
    "homepage": "https://huggingface.co/datasets/timm/oxford-iiit-pet",
    "about": "Oxford-IIIT Pet: ảnh chó/mèo 37 giống (parquet: image {bytes}, label, image_id...), dùng cho transfer learning; không có trimap",
}


def test_nyc_tlc_2020_entry():
    dd = load("download_dataset")
    ds, old = dd.DATASETS["nyc-tlc-2020"], dd.DATASETS["nyc-tlc"]
    months = [f"yellow_tripdata_2020-{m:02d}.parquet" for m in range(1, 13)]
    assert ds.source == "url"
    assert ds.files == months + ["taxi_zone_lookup.csv"]
    assert len(ds.ref) == len(ds.files) == 13
    assert [u.rsplit("/", 1)[1] for u in ds.ref[:12]] == months
    assert {u.split("/")[2] for u in ds.ref} == {u.split("/")[2] for u in old.ref}
    assert ds.license == old.license and ds.homepage == old.homepage
    assert "COVID" in ds.about and "2020" in ds.about


def test_oxford_trimaps_entry():
    dd = load("download_dataset")
    ds = dd.DATASETS["oxford-pets-trimaps"]
    assert ds.extract is True
    assert ds.source == "url"
    assert ds.files == ["annotations.tar.gz"]
    assert "CC BY-SA 4.0" in ds.license
    assert "oxford-pets" in ds.about


def test_old_entries_unchanged():
    dd = load("download_dataset")
    for name, old in (("nyc-tlc", _NYC_TLC_OLD), ("oxford-pets", _OXFORD_PETS_OLD)):
        ds = dd.DATASETS[name]
        assert {k: getattr(ds, k) for k in old} == old
        assert not ds.extract and not ds.needs_token and ds.revision is None
