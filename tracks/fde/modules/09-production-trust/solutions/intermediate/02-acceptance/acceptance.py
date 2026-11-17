"""Acceptance test chạy cùng khách: health, độ trễ p95 của /api/ask, câu trả lời có trích dẫn, ACL theo thư mục."""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import requests

TIMEOUT = 120


class Quillo:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def get(self, path: str, token: str | None = None) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return requests.get(self.url + path, headers=headers, timeout=TIMEOUT)

    def ask(self, token: str, question: str, top_k: int) -> requests.Response:
        return requests.post(self.url + "/api/ask", headers={"Authorization": f"Bearer {token}"},
                             json={"question": question, "top_k": top_k}, timeout=TIMEOUT)


def item(name: str, ok: bool, detail: str) -> dict:
    return {"id": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def check_health(q: Quillo) -> dict:
    try:
        response = q.get("/healthz")
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        return item("health", False, f"/healthz không trả JSON: {type(error).__name__}")
    down = sorted(name for name, up in (body.get("checks") or {}).items() if not up)
    ok = response.status_code == 200 and body.get("status") == "ok" and not down and bool(body.get("checks"))
    detail = f"HTTP {response.status_code}, status {body.get('status')!r}"
    if down:
        detail += f", thành phần hỏng: {', '.join(down)}"
    return item("health", ok, detail)


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def check_latency(q: Quillo, cfg: dict) -> tuple[dict, float | None]:
    durations, errors = [], []
    questions = cfg["latency_questions"]
    for i in range(cfg["latency_samples"]):
        started = time.monotonic()
        try:
            status = q.ask(cfg["admin_token"], questions[i % len(questions)], cfg["top_k"]).status_code
        except requests.RequestException as error:
            status = type(error).__name__
        durations.append(time.monotonic() - started)
        if status != 200:
            errors.append(str(status))
    value = round(p95(durations), 3) if durations else None
    if errors:
        return item("latency", False, f"{len(errors)}/{len(durations)} câu hỏi lỗi ({', '.join(errors)})"), value
    ok = value is not None and value <= cfg["p95_max_seconds"]
    return item("latency", ok, f"p95 {value} s / ngưỡng {cfg['p95_max_seconds']} s, {len(durations)} mẫu"), value


def folders_of(q: Quillo, token: str) -> dict[str, str] | None:
    response = q.get("/api/documents", token)
    if response.status_code != 200:
        return None
    return {d["doc_id"]: d["filename"] for d in response.json()}


def check_citations(q: Quillo, cfg: dict) -> dict:
    try:
        names = folders_of(q, cfg["admin_token"])
        if names is None:
            return item("citations", False, "GET /api/documents bằng token quản trị lỗi")
        bad = []
        for case in cfg["questions"]:
            response = q.ask(cfg["admin_token"], case["question"], cfg["top_k"])
            if response.status_code != 200:
                bad.append(f"{case['question']!r}: HTTP {response.status_code}")
                continue
            cited = [names.get(c["doc_id"], "") for c in response.json().get("citations", [])]
            if not any(name.startswith(case["expect_folder"]) for name in cited):
                bad.append(f"{case['question']!r}: không trích tài liệu nào trong {case['expect_folder']}")
    except requests.RequestException as error:
        return item("citations", False, f"lỗi kết nối: {type(error).__name__}")
    return item("citations", not bad, "; ".join(bad) or f"{len(cfg['questions'])} câu đều có trích dẫn đúng thư mục")


def check_acl(q: Quillo, cfg: dict) -> dict:
    bad = []
    try:
        for user in cfg["users"]:
            seen = folders_of(q, user["token"])
            if seen is None:
                bad.append(f"{user['name']}: GET /api/documents lỗi")
                continue
            if not seen:
                bad.append(f"{user['name']}: không thấy tài liệu nào")
            outside = sorted(n for n in seen.values() if not any(n.startswith(f) for f in user["folders"]))
            if outside:
                bad.append(f"{user['name']}: thấy {len(outside)} tài liệu ngoài {user['folders']}")
            response = q.ask(user["token"], user["probe"], cfg["top_k"])
            if response.status_code != 200:
                bad.append(f"{user['name']}: câu hỏi thử trả HTTP {response.status_code}")
                continue
            leaked = [c["doc_id"] for c in response.json().get("citations", []) if c["doc_id"] not in seen]
            if leaked:
                bad.append(f"{user['name']}: câu trả lời trích {len(leaked)} đoạn ngoài quyền")
    except requests.RequestException as error:
        return item("acl", False, f"lỗi kết nối: {type(error).__name__}")
    return item("acl", not bad, "; ".join(bad) or f"{len(cfg['users'])} người dùng chỉ thấy thư mục của mình")


def run(cfg: dict) -> dict:
    q = Quillo(cfg["url"])
    latency, value = check_latency(q, cfg)
    items = [check_health(q), latency, check_citations(q, cfg), check_acl(q, cfg)]
    return {"items": items, "p95_seconds": value, "passed": all(i["status"] == "PASS" for i in items)}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv[1:])
    try:
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"acceptance: không đọc được cấu hình: {error}", file=sys.stderr)
        return 2
    report = run(cfg)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["items"]:
        print(f"{row['status']:4}  {row['id']:9}  {row['detail']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
