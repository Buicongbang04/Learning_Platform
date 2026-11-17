"""Tóm tắt log `docker compose logs --no-color` của quillo: nhóm cảnh báo/lỗi, HTTP 5xx và các đợt sự cố."""

import json
import re
import sys
from datetime import datetime

LINE = re.compile(r"^(?P<service>[A-Za-z0-9_.-]+?)-\d+\s+\|\s?(?P<payload>.*)$")
BAD_LEVELS = {"WARNING", "ERROR", "CRITICAL"}
GAP_S = 30


def parse(lines):
    services: dict[str, dict[str, int]] = {}
    events = []
    for raw in lines:
        match = LINE.match(raw.rstrip("\n"))
        if not match:
            continue
        service = match.group("service")
        counts = services.setdefault(service, {"events": 0, "unparsed": 0})
        try:
            entry = json.loads(match.group("payload"))
            when = datetime.strptime(entry["ts"], "%Y-%m-%dT%H:%M:%S%z")
            if not isinstance(entry["level"], str) or not isinstance(entry["msg"], str):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            counts["unparsed"] += 1
            continue
        counts["events"] += 1
        events.append((when, entry["ts"], service, entry))
    events.sort(key=lambda item: (item[0], item[2], item[3]["msg"]))
    return services, events


def span(bucket: dict, when: datetime, ts: str) -> None:
    bucket["count"] += 1
    if bucket["_first"] is None or when < bucket["_first"]:
        bucket["_first"], bucket["first"] = when, ts
    if bucket["_last"] is None or when >= bucket["_last"]:
        bucket["_last"], bucket["last"] = when, ts


def finish(buckets: dict) -> list[dict]:
    rows = sorted(buckets.items(), key=lambda item: (item[1]["_first"], item[0]))
    return [{k: v for k, v in row.items() if not k.startswith("_")} for _, row in rows]


def triage(lines) -> dict:
    services, events = parse(lines)
    groups: dict[tuple, dict] = {}
    errors: dict[tuple, dict] = {}
    bad = []
    for when, ts, service, entry in events:
        level = entry["level"]
        if level in BAD_LEVELS:
            key = (service, level, entry["msg"])
            bucket = groups.setdefault(key, {"service": service, "level": level, "msg": entry["msg"], "count": 0,
                                             "first": None, "last": None, "_first": None, "_last": None})
            span(bucket, when, ts)
            bad.append((when, ts, service))
        status = entry.get("status")
        if entry["msg"] == "request" and isinstance(status, int) and status >= 500:
            key = (entry.get("path", ""), status)
            bucket = errors.setdefault(key, {"path": entry.get("path", ""), "status": status, "count": 0,
                                             "first": None, "last": None, "_first": None, "_last": None})
            span(bucket, when, ts)
            bad.append((when, ts, service))
    incidents = []
    for when, ts, service in sorted(bad, key=lambda item: (item[0], item[2])):
        if incidents and (when - incidents[-1]["_end"]).total_seconds() <= GAP_S:
            current = incidents[-1]
            current["_end"], current["end"] = when, ts
            current["events"] += 1
            current["_services"].add(service)
        else:
            incidents.append({"start": ts, "end": ts, "events": 1, "_end": when, "_services": {service}})
    window = {"first": events[0][1], "last": max(events, key=lambda item: item[0])[1]} if events else None
    return {
        "services": {name: services[name] for name in sorted(services)},
        "window": window,
        "groups": finish(groups),
        "http_5xx": finish(errors),
        "incidents": [{"start": i["start"], "end": i["end"], "services": sorted(i["_services"]), "events": i["events"]}
                      for i in incidents],
    }


def main(argv: list[str]) -> int:
    lines = []
    for path in argv[1:]:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines.extend(handle)
    json.dump(triage(lines), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
