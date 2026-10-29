# Lời giải: Hybrid ingestion trên Wikimedia EventStreams

Bài advanced không có đáp án duy nhất: số liệu phụ thuộc lúc bạn ghi, và câu hỏi Lambda/Kappa cần lập
luận chứ không có một câu đúng. Dưới đây là hướng làm, các quyết định thiết kế, rubric, code tham chiếu
(đã chạy qua toàn bộ test). Báo cáo bài học là phần trắc nghiệm trong app.

## Hướng làm

1. **Ghi trước, xử lý sau.** `record` chỉ làm một việc: lưu nguyên bản từng event kèm `received_at`. Không
   lọc, không đổi field. Đây là lớp raw bất biến; mọi logic sau đó (stream hay batch) đều chạy lại được
   trên nó. Ghi qua tệp `.part` rồi đổi tên, để tệp `.jsonl` nào cũng là tệp hoàn chỉnh.
2. **SSE tự parse.** Giao thức đơn giản: dòng `field: value`, dòng trống kết thúc event, `:` là comment.
   Ba chi tiết dễ sai: nhiều dòng `data:` nối bằng `\n`; `id` là "last event id" giữ qua các event; event
   dở dang khi luồng đứt phải bỏ (nếu phát ra sẽ ghi một JSON hỏng hoặc thiếu).
3. **Nối lại có `Last-Event-ID`.** Server EventStreams định kỳ đóng kết nối; mạng chập chờn. Gửi lại
   id cuối đã ghi thì server phát tiếp từ offset đó trong Kafka phía sau: không mất, nhưng có thể trùng
   (at-least-once). Lỗi 4xx (trừ 429) là lỗi của ta, ném ra ngay thay vì thử lại mãi.
4. **`parse_event` là hợp đồng dữ liệu.** Mọi chỗ khác chỉ dùng dict phẳng này. Dòng hỏng, thiếu trường
   bắt buộc, canary thì trả `None` thay vì ném lỗi: một dòng xấu không được làm sập pipeline.
5. **Stream = một lượt, state giới hạn.** `stream_counts` chỉ giữ dict đếm và bộ nhớ id có TTL; quyết
   định late dựa trên watermark lúc event đến, không bao giờ nhìn về sau. Đó chính là điều khiến nó
   nhanh, và cũng là lý do nó có thể sai.
6. **Batch = nhìn toàn cục.** `build_clean` đọc hết, dedup toàn bộ, `batch_counts` group by. Không có
   khái niệm "trễ": event đến lúc nào cũng được tính vào đúng window event time của nó.
7. **Đối soát theo khoá**, không theo tổng: outer join `(window_start, wiki)`, điền 0, `diff = batch - stream`.

## Các quyết định cần cân nhắc

- **Khoá dedup là `meta.id`**, không phải `event.id`. `event.id` là id dòng recent change *trong từng wiki*:
  hai wiki khác nhau có thể có cùng số. `meta.id` là UUID của chính event, giữ nguyên khi phát lại.
- **Đếm gì là "sửa đổi"**: chọn `edit` + `new`. `categorize` (chiếm gần một nửa luồng) là hệ quả của
  sửa đổi ở trang khác, `log` là hành động quản trị. Định nghĩa phải **giống hệt** ở stream và batch;
  khác định nghĩa là nguồn lệch phổ biến nhất khi đối soát ngoài đời, trước cả late data.
- **Event time là `timestamp`** (lúc sửa xảy ra), không phải `meta.dt` (lúc event được tạo) hay
  `received_at` (lúc ta nhận). Window theo processing time thì kết quả đổi theo mỗi lần chạy lại.
- **Nhớ id trước khi xét late**: bản trùng của một event trễ được đếm là trùng, nhờ vậy
  `batch - stream == late` khi TTL đủ dài. Thứ tự này là bắt buộc: xét late trước thì bản trùng của event
  trễ bị đếm late lần hai, `late` vượt số sự kiện thật sự mất và đối soát không còn khớp (test có sẵn
  một bản trùng của event trễ để bắt lỗi này).
- **`allowed_lateness`**: đọc từ dữ liệu, không đoán. Trên lần ghi mẫu, p95 độ trễ khoảng 6 giây, 10 giây
  bỏ 0,07% sửa đổi, 30 giây không bỏ event nào. Dashboard chấp nhận chậm thêm 30 giây thì đầy đủ.
- **`dedup_ttl`** phải ≥ khoảng cách lớn nhất giữa hai bản trùng: với nguồn này là thời gian một lần nối lại
  (cỡ giây tới phút). TTL quá ngắn gây lỗi kiểu "tổng khớp, window sai" (test `test_short_dedup_ttl_hides_errors_in_totals`).
- **Lambda hay Kappa cho nguồn này**: EventStreams chỉ giữ lịch sử để replay khoảng 7–31 ngày tuỳ stream, nên "Kappa thuần" (replay
  từ nguồn) không đủ để tính lại lịch sử dài: phải tự giữ lớp raw (tệp JSONL ở đây, ngoài đời là topic
  Kafka retention dài hoặc bảng Iceberg/Delta). Có lớp raw rồi thì Kappa (một code path, tính lại bằng
  replay raw) đơn giản hơn. Lambda đáng khi cần số chốt theo ngày khớp tuyệt đối và đội chấp nhận giữ hai
  code path; khi đó batch cũng đọc chính lớp raw này. Câu trả lời nào cũng được nếu lập luận dựa trên
  retention, độ trễ chấp nhận được và chi phí giữ hai code path.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt khi |
| --- | --- | --- |
| Ghi stream | 20 | `iter_sse` đúng spec SSE (comment, data nhiều dòng, bỏ event dở); `record` có User-Agent mô tả, timeout, nối lại với `Last-Event-ID`, ghi `.part` rồi đổi tên; đã ghi ít nhất 2–3 phút thật |
| Parse và làm sạch | 15 | Dòng hỏng/canary không làm sập; dedup theo `meta.id`, giữ bản đầu; UTC; kiểu đúng; `write_clean` idempotent |
| Stream | 20 | Một lượt theo thứ tự đến; watermark trước khi cập nhật; dedup có TTL; state có giới hạn; stats đúng |
| Batch và đối soát | 15 | Cùng định nghĩa với stream; outer join theo khoá, điền 0; giải thích được mỗi loại `diff` |
| Insight và biểu đồ | 15 | Ít nhất 3 biểu đồ đọc được (có nhãn trục, tiêu đề); số liệu khớp notebook; có chọn `allowed_lateness` dựa trên số đo |
| Lập luận thiết kế | 15 | Nêu giới hạn (thời lượng ghi, phút bị cắt, cờ bot); chọn Lambda hoặc Kappa có lý do gắn với retention của nguồn |

Trừ điểm: dedup theo `event.id`; window theo `received_at`; đếm `categorize` ở một phía mà không ở phía
kia; `record` không có timeout (treo mãi khi mạng đứt); ghi thẳng vào `.jsonl` để lại tệp dở khi bị ngắt.

## Lời giải tham khảo

Code dưới đây pass toàn bộ test (fixture và dữ liệu thật) khi chép vào các cell tương ứng của
`starter/hybrid_wikimedia.ipynb`. Cell import và hằng:

```python
import json
import time
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

STREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
# Chính sách của Wikimedia: User-Agent phải cho biết ai gọi và cách liên hệ. Sửa phần contact.
USER_AGENT = "de-track-learner/1.0 (hybrid ingestion exercise; contact: your-email@example.com)"
EDIT_TYPES = ("edit", "new")   # sửa trang và tạo trang mới; categorize/log không tính là "sửa"
```

### SSE và ghi stream

```python
def iter_sse(lines: Iterable[str]) -> Iterator[tuple[str | None, str]]:
    """Dòng SSE -> (last event id, data). Bỏ comment ':'; data nhiều dòng nối bằng '\\n';
    event chỉ phát khi gặp dòng trống; event dở dang ở cuối luồng bị bỏ."""
    last_id, data = None, []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        line = line.rstrip("\r\n")
        if not line:
            if data:
                yield last_id, "\n".join(data)
            data = []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "data":
            data.append(value)
        elif field == "id":
            last_id = value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def record(seconds: float, out_path: Path, *, session=None, max_events: int | None = None,
           retry_wait: float = 1.0, max_retries: int = 5) -> dict:
    """Ghi stream ra JSONL {"received_at", "event"} trong `seconds` giây (hoặc tới max_events).
    Mất kết nối thì nối lại với Last-Event-ID; ghi vào tệp .part rồi đổi tên khi xong."""
    session = session or requests.Session()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    part = out_path.with_name(out_path.name + ".part")
    deadline = time.monotonic() + seconds
    last_id, written, reconnects, failures = None, 0, 0, 0

    def done() -> bool:
        return time.monotonic() >= deadline or (max_events is not None and written >= max_events)

    with part.open("w", encoding="utf-8") as fh:
        while not done():
            headers = {"User-Agent": USER_AGENT, "Accept": "text/event-stream"}
            if last_id:
                headers["Last-Event-ID"] = last_id
            try:
                with session.get(STREAM_URL, headers=headers, stream=True, timeout=(10, 60)) as resp:
                    resp.raise_for_status()
                    for event_id, data in iter_sse(resp.iter_lines(decode_unicode=True)):
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        fh.write(json.dumps({"received_at": _now_iso(), "event": event}, ensure_ascii=False) + "\n")
                        written += 1
                        failures = 0
                        last_id = event_id or last_id
                        if done():
                            break
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                if status != 429 and status < 500:
                    part.unlink(missing_ok=True)
                    raise
                failures += 1
            except requests.RequestException:
                failures += 1
            if done():
                break
            if failures > max_retries:
                raise RuntimeError(f"Mất kết nối {failures} lần liên tiếp, dừng ghi")
            reconnects += 1
            time.sleep(retry_wait * min(2 ** max(failures - 1, 0), 30))
    part.replace(out_path)
    return {"path": str(out_path), "events": written, "reconnects": reconnects}
```

### Parse

```python
def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def parse_event(line: str) -> dict | None:
    """Một dòng JSONL đã ghi -> dict phẳng, hoặc None (dòng hỏng, thiếu trường, canary)."""
    try:
        rec = json.loads(line)
        ev = rec["event"]
        meta = ev["meta"]
        if meta.get("domain") == "canary":
            return None
        length = ev.get("length") or {}
        new_len = length.get("new")
        return {
            "event_id": str(meta["id"]),
            "wiki": ev["wiki"],
            "domain": meta.get("domain"),
            "type": ev["type"],
            "bot": bool(ev.get("bot", False)),
            "namespace": int(ev.get("namespace", 0)),
            "title": ev.get("title"),
            "user": ev.get("user"),
            "event_time": int(ev["timestamp"]),
            "received_at": _epoch(rec["received_at"]),
            "len_delta": None if new_len is None else int(new_len) - int(length.get("old") or 0),
        }
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
```

### Phần stream

```python
def _counts_frame(counts: dict) -> pd.DataFrame:
    rows = [(start, wiki, n) for (start, wiki), n in sorted(counts.items())]
    df = pd.DataFrame(rows, columns=["window_start", "wiki", "edits"])
    df["window_start"] = pd.to_datetime(df["window_start"].astype("int64"), unit="s", utc=True)
    df["edits"] = df["edits"].astype("int64")
    return df


def stream_counts(events: Iterable[dict], window: int = 60, allowed_lateness: int = 10,
                  dedup: bool = True, dedup_ttl: int = 600) -> tuple[pd.DataFrame, dict]:
    """Đếm sửa đổi theo (window, wiki) như một stream processor: một lượt, theo thứ tự đến."""
    counts: dict[tuple[int, str], int] = {}
    seen: dict[str, int] = {}
    max_time = None
    stats = {"events": 0, "duplicates": 0, "late": 0, "counted": 0}
    for e in events:
        if e["type"] not in EDIT_TYPES:
            continue
        stats["events"] += 1
        t = e["event_time"]
        if dedup:
            if e["event_id"] in seen:
                stats["duplicates"] += 1
                continue
            seen[e["event_id"]] = t
        start = t - t % window
        if max_time is not None and start + window <= max_time - allowed_lateness:
            stats["late"] += 1
            continue
        if max_time is None or t > max_time:
            max_time = t
            if dedup:
                horizon = max_time - dedup_ttl
                for key in [k for k, seen_t in seen.items() if seen_t < horizon]:
                    del seen[key]
        counts[(start, e["wiki"])] = counts.get((start, e["wiki"]), 0) + 1
        stats["counted"] += 1
    return _counts_frame(counts), stats
```

### Phần batch

```python
COLUMNS = ["event_id", "wiki", "domain", "type", "bot", "namespace", "title", "user",
           "event_time", "received_at", "len_delta"]


def build_clean(lines: Iterable[str]) -> tuple[pd.DataFrame, dict]:
    """Batch: đọc hết, bỏ dòng hỏng/canary, dedup theo event_id (giữ bản đến đầu), ép kiểu."""
    stats = {"lines": 0, "parsed": 0, "dropped": 0, "duplicates": 0}
    rows = []
    for line in lines:
        stats["lines"] += 1
        event = parse_event(line)
        if event is None:
            stats["dropped"] += 1
        else:
            rows.append(event)
    stats["parsed"] = len(rows)
    df = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates("event_id", keep="first")
    stats["duplicates"] = stats["parsed"] - len(df)
    df["event_time"] = pd.to_datetime(df["event_time"].astype("int64"), unit="s", utc=True)
    df["received_at"] = pd.to_datetime(df["received_at"].astype("float64"), unit="s", utc=True)
    df["lag_s"] = (df["received_at"] - df["event_time"]).dt.total_seconds()
    df["bot"] = df["bot"].astype(bool)
    df["namespace"] = df["namespace"].astype("int64")
    df["len_delta"] = df["len_delta"].astype("Int64")
    df = df.sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    return df, stats


def batch_counts(df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Batch: số sửa đổi (EDIT_TYPES) theo (window event time, wiki) trên dữ liệu sạch."""
    edits = df[df["type"].isin(EDIT_TYPES)]
    out = (edits.assign(window_start=edits["event_time"].dt.floor(f"{window}s"))
           .groupby(["window_start", "wiki"]).size().rename("edits").reset_index())
    out["edits"] = out["edits"].astype("int64")
    return out.sort_values(["window_start", "wiki"]).reset_index(drop=True)
```

### Đối soát

```python
def reconcile(stream: pd.DataFrame, batch: pd.DataFrame) -> pd.DataFrame:
    """Outer join theo (window_start, wiki); thiếu bên nào thì 0; diff = batch - stream."""
    keys = ["window_start", "wiki"]
    s = stream[keys + ["edits"]].rename(columns={"edits": "stream_edits"})
    b = batch[keys + ["edits"]].rename(columns={"edits": "batch_edits"})
    for frame in (s, b):
        frame["window_start"] = frame["window_start"].astype("datetime64[ns, UTC]")
    out = s.merge(b, on=keys, how="outer")
    out[["stream_edits", "batch_edits"]] = out[["stream_edits", "batch_edits"]].fillna(0).astype("int64")
    out["diff"] = out["batch_edits"] - out["stream_edits"]
    return out.sort_values(keys).reset_index(drop=True)
```

### Insight

```python
def insights(df: pd.DataFrame, stats: dict) -> dict:
    edits = df[df["type"].isin(EDIT_TYPES)]
    duration_min = (df["received_at"].max() - df["received_at"].min()).total_seconds() / 60
    by_wiki = edits.groupby("wiki").size().reset_index(name="n").sort_values(["n", "wiki"], ascending=[False, True])
    human = edits[~edits["bot"]].groupby("wiki").size().reset_index(name="n").sort_values(
        ["n", "wiki"], ascending=[False, True])
    return {
        "events": len(df),
        "duplicates": stats["duplicates"],
        "duplicate_rate": stats["duplicates"] / stats["parsed"] if stats["parsed"] else 0.0,
        "dropped": stats["dropped"],
        "duration_min": duration_min,
        "edits": len(edits),
        "edits_per_min": len(edits) / duration_min if duration_min else float("nan"),
        "bot_share": float(edits["bot"].mean()),
        "wikis": int(df["wiki"].nunique()),
        "top_wiki": by_wiki.iloc[0]["wiki"],
        "top_wiki_edits": int(by_wiki.iloc[0]["n"]),
        "top_human_wiki": human.iloc[0]["wiki"] if len(human) else None,
        "type_counts": {k: int(v) for k, v in df["type"].value_counts().items()},
        "lag_p50_s": float(df["lag_s"].quantile(0.5)),
        "lag_p95_s": float(df["lag_s"].quantile(0.95)),
        "lag_max_s": float(df["lag_s"].max()),
    }
```

### Ghi dữ liệu sạch

```python
def write_clean(df: pd.DataFrame, out_dir: Path) -> Path:
    """Ghi đè out_dir/recentchange.parquet qua tệp tạm; trả đường dẫn."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "recentchange.parquet"
    tmp = out_dir / "recentchange.parquet.tmp"
    df.to_parquet(tmp, index=False)
    tmp.replace(target)
    return target
```

### Các cell `explore`: chạy, thử lateness, biểu đồ

```python
# explore: chạy cả hai phần trên dữ liệu đã ghi, đối soát, và thử nhiều mức allowed_lateness
EVENTS = [e for e in map(parse_event, LINES) if e is not None]
df, STATS = build_clean(LINES)
BATCH = batch_counts(df)
STREAM, SSTATS = stream_counts(EVENTS, allowed_lateness=10)
RECON = reconcile(STREAM, BATCH)
print("build_clean:", STATS)
print("stream (lateness 10s):", SSTATS)
print("window lệch:", int((RECON["diff"] != 0).sum()), "/", len(RECON), "- tổng diff:", int(RECON["diff"].sum()))

LATENESS = [0, 1, 2, 5, 10, 20, 30, 60, 120]
LATE = pd.DataFrame([{"allowed_lateness": a, **stream_counts(EVENTS, allowed_lateness=a)[1]} for a in LATENESS])
LATE["late_rate"] = LATE["late"] / LATE["events"]
LATE

# explore: sửa đổi mỗi phút, bot vs người
edits = df[df["type"].isin(EDIT_TYPES)]
per_min = (edits.assign(minute=edits["event_time"].dt.floor("min"))
           .pivot_table(index="minute", columns="bot", values="event_id", aggfunc="count", fill_value=0)
           .rename(columns={False: "người", True: "bot"}))
ax = per_min.plot.bar(stacked=True, figsize=(10, 4), width=0.9)
ax.set_xticks(range(len(per_min)), [t.strftime("%H:%M") for t in per_min.index], rotation=0)
ax.set_xlabel("phút (UTC, event time) - phút đầu và cuối chỉ ghi được một phần")
ax.set_ylabel("số sửa đổi")
ax.set_title("Sửa đổi mỗi phút trên mọi wiki")
plt.tight_layout()
plt.show()

# explore: top 10 wiki, bot vs người
top = (edits.pivot_table(index="wiki", columns="bot", values="event_id", aggfunc="count", fill_value=0)
       .rename(columns={False: "người", True: "bot"}))
top = top.assign(total=top.sum(axis=1)).nlargest(10, "total").drop(columns="total").iloc[::-1]
ax = top.plot.barh(stacked=True, figsize=(8, 5))
ax.set_xlabel("số sửa đổi")
ax.set_title("Top 10 wiki theo số sửa đổi")
plt.tight_layout()
plt.show()

# explore: độ trễ đến (received_at - event_time) và tỉ lệ late theo allowed_lateness
import numpy as np

fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
lag = df["lag_s"].clip(lower=0.1)
a1.hist(lag, bins=np.logspace(-1, np.log10(lag.max() + 1), 40))
a1.set_xscale("log")
a1.set_xlabel("lag (giây, log)")
a1.set_ylabel("số event")
a1.set_title("Độ trễ từ lúc sửa tới lúc ta nhận")
a2.plot(LATE["allowed_lateness"], LATE["late_rate"] * 100, marker="o")
a2.set_xscale("symlog", linthresh=1)
a2.set_xlabel("allowed_lateness (giây)")
a2.set_ylabel("% sửa đổi bị bỏ vì trễ")
a2.set_title("Đánh đổi độ trễ - độ đầy đủ")
plt.tight_layout()
plt.show()

# explore: đối soát theo phút: stream (lateness 10s) vs batch
by_min = RECON.groupby("window_start")[["stream_edits", "batch_edits"]].sum()
ax = by_min.plot(figsize=(10, 3.5), marker=".")
ax.set_ylabel("số sửa đổi")
ax.set_title("Stream (allowed_lateness=10s) và batch theo phút")
plt.tight_layout()
plt.show()
```
