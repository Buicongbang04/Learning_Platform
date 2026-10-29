"""Test hạ tầng tải bộ dữ liệu (không cần mạng)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data import download_dataset as dd  # noqa: E402


def test_ensure_skips_download_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)
    (tmp_path / "nyc-tlc").mkdir()
    (tmp_path / "nyc-tlc" / "x").write_text("1")

    def boom(*a, **k):
        raise AssertionError("không được tải")

    monkeypatch.setattr(dd, "download", boom)
    assert dd.ensure("nyc-tlc") == tmp_path / "nyc-tlc"


def test_cli_without_out_uses_ensure(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(dd, "ensure", lambda name: calls.append(name) or tmp_path / name)
    monkeypatch.setattr(dd, "download", lambda *a, **k: pytest.fail("không được gọi download trực tiếp"))
    dd.main(["nyc-tlc"])
    assert calls == ["nyc-tlc"]


def test_cli_with_out_downloads_directly(tmp_path, monkeypatch):
    got = []
    monkeypatch.setattr(dd, "download", lambda name, out: got.append((name, out)) or [out / "x"])
    monkeypatch.setattr(dd, "ensure", lambda name: pytest.fail("không được gọi ensure"))
    dd.main(["nyc-tlc", "--out", str(tmp_path)])
    assert got == [("nyc-tlc", tmp_path)]


def test_ensure_atomic_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)

    def fail(name, out):
        out.mkdir(parents=True)
        (out / "half").write_text("x")
        raise RuntimeError("mất mạng")

    monkeypatch.setattr(dd, "download", fail)
    with pytest.raises(RuntimeError):
        dd.ensure("nyc-tlc")
    assert list(tmp_path.iterdir()) == []


def test_ensure_renames_temp_dir_on_success(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)

    def ok(name, out):
        out.mkdir(parents=True)
        (out / "a.csv").write_text("1")
        return [out / "a.csv"]

    monkeypatch.setattr(dd, "download", ok)
    path = dd.ensure("nasa-http-logs")
    assert (path / "a.csv").exists()
    assert [p.name for p in tmp_path.iterdir()] == ["nasa-http-logs"]


def test_multi_url_dataset_downloads_each_file(tmp_path, monkeypatch):
    ds = dd.Dataset("url", ("http://h/a", "http://h/b"), ["a.bin", "b.bin"], license="x", homepage="http://h")
    monkeypatch.setitem(dd.DATASETS, "fake-multi", ds)
    calls = []

    class Resp:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=None):
            yield self.url.encode()

        content = b""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    def fake_get(url, **kw):
        calls.append(url)
        return Resp(url)

    monkeypatch.setattr(dd.requests, "get", fake_get)
    paths = dd.download("fake-multi", tmp_path / "out")
    assert calls == ["http://h/a", "http://h/b"]
    assert [p.name for p in paths] == ["a.bin", "b.bin"]
    assert (tmp_path / "out" / "b.bin").read_bytes() == b"http://h/b"


def test_de_datasets_declared():
    assert {"nyc-tlc", "nasa-http-logs", "air-quality-uci"} <= dd.DATASETS.keys()
    for name in ("nyc-tlc", "nasa-http-logs", "air-quality-uci"):
        ds = dd.DATASETS[name]
        assert ds.license and ds.homepage
        if isinstance(ds.ref, tuple):
            assert len(ds.ref) == len(ds.files)
    assert len(dd.DATASETS["nyc-tlc"].ref) == 13


def test_old_datasets_untouched():
    assert {"cookie-cats", "ab-data", "hillstrom"} <= dd.DATASETS.keys()
    assert dd.DATASETS["hillstrom"].files == ["hillstrom.csv"]
