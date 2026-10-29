import json
import re
from collections import Counter
from pathlib import Path

import nbformat
import pandas as pd
import pytest
import requests

from testkit import ROOT, Exercise

ex = Exercise(__file__)
SAMPLE = ex.fixtures / "recentchange_sample.jsonl"
RAW = ROOT / "data" / "raw" / "wikimedia-recentchange"
T = 1793255160  # mốc của fixture, chia hết cho 60


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("hybrid_wikimedia.ipynb")


def ts(offset: int) -> pd.Timestamp:
    return pd.Timestamp(T + offset, unit="s", tz="UTC")


def sample_lines() -> list[str]:
    return SAMPLE.read_text(encoding="utf-8").splitlines(keepends=True)


def sample_events(nb) -> list[dict]:
    return [e for e in map(nb.parse_event, sample_lines()) if e is not None]


def as_dict(counts: pd.DataFrame) -> dict:
    return {(row.window_start, row.wiki): int(row.edits) for row in counts.itertuples()}


def diffs(recon: pd.DataFrame) -> dict:
    return {(row.window_start, row.wiki): int(row.diff) for row in recon.itertuples() if row.diff != 0}


# ---------- SSE: đọc giao thức Server-Sent Events bằng tay ----------

def test_iter_sse_comments_multiline_and_ids(nb):
    lines = [":ok", "", "event: message", 'id: [{"offset":1}]', 'data: {"a": 1}', "",
             ": heartbeat", 'id: [{"offset":2}]', 'data: {"b":', "data: 2}", "", "data: {\"c\": 3}", ""]
    got = list(nb.iter_sse(lines))
    assert got == [('[{"offset":1}]', '{"a": 1}'), ('[{"offset":2}]', '{"b":\n2}'), ('[{"offset":2}]', '{"c": 3}')]


def test_iter_sse_drops_incomplete_event_at_eof(nb):
    # Mất kết nối giữa chừng: event chưa có dòng trống kết thúc thì không được phát ra
    got = list(nb.iter_sse(['id: 1', 'data: {"a": 1}', "", 'id: 2', 'data: {"b": ']))
    assert got == [("1", '{"a": 1}')]


class FakeResponse:
    def __init__(self, lines, error=None, status=200):
        self.lines, self.error, self.status_code = lines, error, status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_lines(self, decode_unicode=False, **kwargs):
        yield from self.lines
        if self.error:
            raise self.error


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, headers=None, stream=False, timeout=None, **kwargs):
        self.calls.append({"url": url, "headers": dict(headers or {}), "stream": stream, "timeout": timeout})
        return self.responses.pop(0)


def sse(event_id, payload):
    return [f"id: {event_id}", "data: " + json.dumps(payload), ""]


def test_record_reconnects_with_last_event_id(nb, tmp_path):
    first = FakeResponse([":ok", "", *sse("[1]", {"n": 1}), *sse("[2]", {"n": 2}), "id: [3]", 'data: {"n": 3'],
                         error=requests.exceptions.ChunkedEncodingError("connection reset"))
    second = FakeResponse([*sse("[3]", {"n": 3}), *sse("[4]", {"n": 4}), *sse("[5]", {"n": 5})])
    session = FakeSession([first, second])
    out = tmp_path / "raw" / "rec.jsonl"
    stats = nb.record(30, out, session=session, max_events=4, retry_wait=0)
    assert stats["events"] == 4 and stats["reconnects"] == 1
    assert Path(stats["path"]) == out and out.exists()
    assert not list(tmp_path.rglob("*.part")), "Ghi qua tệp .part rồi đổi tên khi xong"
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["event"]["n"] for r in rows] == [1, 2, 3, 4]
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", r["received_at"]) for r in rows)
    first_call, second_call = session.calls
    assert first_call["stream"] is True and first_call["timeout"] is not None
    assert "Last-Event-ID" not in first_call["headers"]
    assert second_call["headers"]["Last-Event-ID"] == "[2]", "Nối lại từ event cuối cùng đã ghi"
    ua = first_call["headers"].get("User-Agent", "")
    assert ua and "python-requests" not in ua, "Wikimedia yêu cầu User-Agent mô tả rõ ai đang gọi"


def test_record_gives_up_on_client_error(nb, tmp_path):
    session = FakeSession([FakeResponse([], status=403)])
    with pytest.raises(requests.HTTPError):
        nb.record(30, tmp_path / "rec.jsonl", session=session, retry_wait=0)


# ---------- parse_event ----------

def test_parse_event_flattens_record(nb):
    first = sample_lines()[0]
    got = nb.parse_event(first)
    assert got == {"event_id": "00000000-0000-4000-8000-000000000001", "wiki": "enwiki",
                   "domain": "en.wikipedia.org", "type": "edit", "bot": False, "namespace": 0,
                   "title": "Hanoi", "user": "Alice", "event_time": T + 5,
                   "received_at": pytest.approx(T + 6), "len_delta": 200}


def test_parse_event_edge_cases(nb):
    lines = sample_lines()
    assert nb.parse_event(lines[2])["len_delta"] == 500           # trang mới: không có length.old
    assert nb.parse_event(lines[3])["len_delta"] is None          # categorize: không có length
    assert nb.parse_event(lines[7]) is None                       # canary event
    assert nb.parse_event(lines[8]) is None                       # dòng ghi dở
    assert nb.parse_event("") is None
    assert nb.parse_event('{"received_at": "2026-10-29T06:26:00.000Z", "event": {"meta": {"id": "x"}}}') is None


# ---------- batch: làm sạch toàn bộ tệp rồi đếm ----------

def test_build_clean_dedups_and_types(nb):
    df, stats = nb.build_clean(sample_lines())
    assert stats == {"lines": 15, "parsed": 13, "dropped": 2, "duplicates": 3}
    assert len(df) == 10 and df["event_id"].is_unique
    assert "canary" not in set(df["domain"])
    assert str(df["event_time"].dt.tz) == "UTC" and str(df["received_at"].dt.tz) == "UTC"
    assert df["event_time"].is_monotonic_increasing
    assert df["bot"].dtype == bool
    e2 = df[df["event_id"].str.endswith("0002")].iloc[0]
    assert e2["received_at"] == ts(11), "Giữ bản đến đầu tiên"
    assert df.set_index("title").loc["Hue", "lag_s"] == pytest.approx(30)
    assert df["len_delta"].isna().sum() == 2


def test_batch_counts_on_sample(nb):
    df, _ = nb.build_clean(sample_lines())
    got = nb.batch_counts(df, window=60)
    assert list(got.columns) == ["window_start", "wiki", "edits"]
    assert as_dict(got) == {(ts(0), "enwiki"): 3, (ts(0), "wikidatawiki"): 1, (ts(60), "enwiki"): 1,
                            (ts(60), "wikidatawiki"): 1, (ts(120), "dewiki"): 1, (ts(180), "enwiki"): 1}


# ---------- stream: xử lý theo thứ tự đến, watermark + dedup có TTL ----------

def test_stream_matches_batch_after_dedup(nb):
    df, _ = nb.build_clean(sample_lines())
    stream, stats = nb.stream_counts(sample_events(nb), window=60, allowed_lateness=120)
    assert list(stream.columns) == ["window_start", "wiki", "edits"]
    assert stats == {"events": 11, "duplicates": 3, "late": 0, "counted": 8}
    recon = nb.reconcile(stream, nb.batch_counts(df, window=60))
    assert list(recon.columns) == ["window_start", "wiki", "stream_edits", "batch_edits", "diff"]
    assert len(recon) == 6 and (recon["diff"] == 0).all()


def test_stream_late_event_shows_up_in_reconcile(nb):
    df, _ = nb.build_clean(sample_lines())
    stream, stats = nb.stream_counts(sample_events(nb), window=60, allowed_lateness=10)
    assert stats == {"events": 11, "duplicates": 3, "late": 1, "counted": 7}
    recon = nb.reconcile(stream, nb.batch_counts(df, window=60))
    assert diffs(recon) == {(ts(0), "enwiki"): 1}
    # Bản trùng của event trễ (Hue) phải được đếm là trùng, không phải late lần hai: phải nhớ id TRƯỚC khi xét late
    assert recon["diff"].sum() == stats["late"] == 1


def test_stream_without_dedup_overcounts(nb):
    df, _ = nb.build_clean(sample_lines())
    stream, stats = nb.stream_counts(sample_events(nb), window=60, allowed_lateness=120, dedup=False)
    assert stats == {"events": 11, "duplicates": 0, "late": 0, "counted": 11}
    recon = nb.reconcile(stream, nb.batch_counts(df, window=60))
    assert diffs(recon) == {(ts(0), "wikidatawiki"): -1, (ts(0), "enwiki"): -1, (ts(60), "enwiki"): -1}


def test_short_dedup_ttl_hides_errors_in_totals(nb):
    # TTL 30 giây: bản trùng của e6 đến sau 60 giây thì id đã bị quên -> đếm hai lần.
    # Event trễ bị bỏ ở window khác. Tổng khớp, từng window thì sai: đối soát phải theo khoá.
    df, _ = nb.build_clean(sample_lines())
    stream, stats = nb.stream_counts(sample_events(nb), window=60, allowed_lateness=10, dedup_ttl=30)
    assert stats == {"events": 11, "duplicates": 2, "late": 1, "counted": 8}
    recon = nb.reconcile(stream, nb.batch_counts(df, window=60))
    assert recon["stream_edits"].sum() == recon["batch_edits"].sum()
    assert diffs(recon) == {(ts(0), "enwiki"): 1, (ts(60), "enwiki"): -1}


def test_stream_does_not_reorder_input(nb):
    events = sample_events(nb)
    before = [e["event_id"] for e in events]
    nb.stream_counts(events, window=60, allowed_lateness=10)
    assert [e["event_id"] for e in events] == before


def test_reconcile_outer_join_fills_zero(nb):
    stream = pd.DataFrame({"window_start": [ts(0), ts(60)], "wiki": ["enwiki", "enwiki"], "edits": [2, 5]})
    batch = pd.DataFrame({"window_start": [ts(0), ts(120)], "wiki": ["enwiki", "dewiki"], "edits": [3, 1]})
    got = nb.reconcile(stream, batch)
    rows = [(r.window_start, r.wiki, r.stream_edits, r.batch_edits, r.diff) for r in got.itertuples()]
    assert rows == [(ts(0), "enwiki", 2, 3, 1), (ts(60), "enwiki", 5, 0, -5), (ts(120), "dewiki", 0, 1, 1)]
    assert pd.api.types.is_integer_dtype(got["diff"])


# ---------- insight và ghi dữ liệu sạch ----------

def test_insights_on_sample(nb):
    df, stats = nb.build_clean(sample_lines())
    got = nb.insights(df, stats)
    assert got["events"] == 10 and got["duplicates"] == 3 and got["dropped"] == 2
    assert got["duplicate_rate"] == pytest.approx(3 / 13)
    assert got["duration_min"] == pytest.approx(3.0)
    assert got["edits"] == 8
    assert got["edits_per_min"] == pytest.approx(8 / 3)
    assert got["bot_share"] == pytest.approx(3 / 8)
    assert got["wikis"] == 4
    assert (got["top_wiki"], got["top_wiki_edits"]) == ("enwiki", 5)
    assert got["top_human_wiki"] == "enwiki"
    assert got["type_counts"] == {"edit": 7, "new": 1, "categorize": 1, "log": 1}
    assert got["lag_p50_s"] == pytest.approx(1.0)
    assert got["lag_p95_s"] == pytest.approx(16.95)
    assert got["lag_max_s"] == pytest.approx(30.0)


def test_write_clean_overwrites(nb, tmp_path):
    df, _ = nb.build_clean(sample_lines())
    first = nb.write_clean(df, tmp_path / "clean")
    second = nb.write_clean(df, tmp_path / "clean")
    assert first == second and first.suffix == ".parquet"
    back = pd.read_parquet(tmp_path / "clean")
    assert len(back) == len(df) and back["event_id"].is_unique
    assert str(back["event_time"].dt.tz) == "UTC"


# ---------- dữ liệu thật: tệp bạn tự ghi từ EventStreams ----------
# Stream trực tiếp không tái lập được, nên tham chiếu được tính lại ngay trong test, trên chính
# các tệp bạn đã ghi, bằng code độc lập (json thuần + Counter), rồi so với kết quả notebook.

_CACHE = {}


def recordings() -> list[Path]:
    files = sorted(RAW.glob("*.jsonl")) if RAW.is_dir() else []
    if not files:
        pytest.skip("Chưa ghi stream nào vào data/raw/wikimedia-recentchange/. Mở notebook, chạy cell "
                    "explore `record(...)` (vài phút) rồi chạy lại test")
    return files


def real_lines() -> list[str]:
    if "lines" not in _CACHE:
        lines = []
        for path in recordings():
            with path.open(encoding="utf-8") as fh:
                lines.extend(fh)
        _CACHE["lines"] = lines
    return _CACHE["lines"]


def reference() -> dict:
    """Tính lại độc lập: dedup theo meta.id, bỏ canary và dòng hỏng, đếm bằng Counter."""
    if "ref" in _CACHE:
        return _CACHE["ref"]
    seen, parsed = {}, 0
    for line in real_lines():
        try:
            rec = json.loads(line)
            ev = rec["event"]
            key = ev["meta"]["id"]
            int(ev["timestamp"]), ev["type"], ev["wiki"], pd.Timestamp(rec["received_at"])
            if ev["meta"].get("domain") == "canary":
                continue
        except (ValueError, KeyError, TypeError):
            continue
        parsed += 1
        seen.setdefault(key, (rec["received_at"], ev))
    received = pd.to_datetime([r for r, _ in seen.values()], utc=True)
    edits = [ev for _, ev in seen.values() if ev["type"] in ("edit", "new")]
    by_wiki = Counter(ev["wiki"] for ev in edits)
    top = min(by_wiki.items(), key=lambda kv: (-kv[1], kv[0]))
    windows = Counter((pd.Timestamp(ev["timestamp"] - ev["timestamp"] % 60, unit="s", tz="UTC"), ev["wiki"])
                      for ev in edits)
    lags = pd.Series([pd.Timestamp(r).timestamp() - ev["timestamp"] for r, ev in seen.values()])
    _CACHE["ref"] = ref = {
        "events": len(seen), "duplicates": parsed - len(seen), "edits": len(edits),
        "duration_min": (received.max() - received.min()).total_seconds() / 60,
        "bot_share": sum(bool(ev["bot"]) for ev in edits) / len(edits),
        "wikis": len({ev["wiki"] for _, ev in seen.values()}),
        "top_wiki": top[0], "top_wiki_edits": top[1],
        "type_counts": dict(Counter(ev["type"] for _, ev in seen.values())),
        "lag_p50_s": lags.quantile(0.5), "lag_max_s": lags.max(), "windows": windows,
    }
    return ref


def real_clean(nb):
    if "clean" not in _CACHE:
        _CACHE["clean"] = nb.build_clean(real_lines())
    return _CACHE["clean"]


def test_real_recording_is_long_enough():
    ref = reference()
    assert ref["duration_min"] >= 2, "Ghi ít nhất 2-3 phút để có vài window 1 phút trọn vẹn"
    assert ref["events"] >= 1000


def test_real_clean_matches_reference(nb):
    df, stats = real_clean(nb)
    ref = reference()
    assert len(df) == ref["events"] and df["event_id"].is_unique
    assert stats["duplicates"] == ref["duplicates"]
    assert "canary" not in set(df["domain"])
    assert str(df["event_time"].dt.tz) == "UTC"
    assert df["event_time"].is_monotonic_increasing


def test_real_batch_counts_match_reference(nb):
    df, _ = real_clean(nb)
    assert as_dict(nb.batch_counts(df, window=60)) == dict(reference()["windows"])


def test_real_stream_reconciles_with_batch(nb):
    df, _ = real_clean(nb)
    events = [e for e in map(nb.parse_event, real_lines()) if e is not None]
    batch = nb.batch_counts(df, window=60)
    stream, stats = nb.stream_counts(events, window=60, allowed_lateness=10**9, dedup_ttl=10**9)
    assert (nb.reconcile(stream, batch)["diff"] == 0).all(), "Chờ vô hạn + dedup đủ lâu thì stream phải khớp batch"
    stream, stats = nb.stream_counts(events, window=60, allowed_lateness=0, dedup_ttl=10**9)
    recon = nb.reconcile(stream, batch)
    assert (recon["diff"] >= 0).all(), "Chỉ có event trễ bị bỏ: stream không bao giờ đếm dư"
    assert recon["diff"].sum() == stats["late"]
    assert stats["counted"] == stats["events"] - stats["duplicates"] - stats["late"]


def test_real_insights_match_reference(nb):
    df, stats = real_clean(nb)
    got, ref = nb.insights(df, stats), reference()
    for key in ("events", "duplicates", "edits", "wikis", "top_wiki", "top_wiki_edits", "type_counts"):
        assert got[key] == ref[key], key
    for key in ("duration_min", "bot_share", "lag_p50_s", "lag_max_s"):
        assert got[key] == pytest.approx(ref[key], abs=1e-6), key
    assert got["edits_per_min"] == pytest.approx(ref["edits"] / ref["duration_min"])


# ---------- biểu đồ ----------

def test_notebook_draws_charts():
    book = nbformat.read(ex.path("hybrid_wikimedia.ipynb"), as_version=4)
    plots = [c for c in book.cells if c.cell_type == "code" and "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.barh\(|\.hist\(|\.imshow\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 3, "Cần ít nhất 3 cell explore vẽ biểu đồ"
