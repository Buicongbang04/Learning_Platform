from collections import Counter
from statistics import fmean

SWAP_IO_LIMIT = 100
IOWAIT_LIMIT = 20
BLOCKED_LIMIT = 1
QUEUE_COLUMNS = ("aqu-sz", "avgqu-sz")


def parse_vmstat(text: str) -> list[dict[str, int]]:
    columns: list[str] = []
    rows: list[dict[str, int]] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] == "procs":
            continue
        if parts[0] == "r":
            columns = parts
            continue
        if columns and all(p.isdigit() for p in parts) and len(parts) == len(columns):
            rows.append(dict(zip(columns, map(int, parts))))
    return rows[1:]


def use_summary(samples: list[dict[str, int]], ncpu: int) -> dict[str, float]:
    if not samples or ncpu <= 0:
        raise ValueError("Cần ít nhất một mẫu và ncpu > 0")
    return {
        "cpu_util": fmean(s["us"] + s["sy"] for s in samples),
        "run_queue_per_cpu": fmean(s["r"] for s in samples) / ncpu,
        "iowait": fmean(s["wa"] for s in samples),
        "blocked": fmean(s["b"] for s in samples),
        "swap_io": fmean(s["si"] + s["so"] for s in samples),
    }


def diagnose(samples: list[dict[str, int]], ncpu: int) -> str:
    use = use_summary(samples, ncpu)
    if use["swap_io"] >= SWAP_IO_LIMIT:
        return "memory"
    if use["run_queue_per_cpu"] > 1:
        return "cpu"
    if use["iowait"] >= IOWAIT_LIMIT or use["blocked"] >= BLOCKED_LIMIT:
        return "disk"
    return "ok"


def parse_iostat(text: str) -> dict[str, dict[str, float]]:
    report: dict[str, dict[str, float]] = {}
    header: list[str] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            header = []
            continue
        if parts[0].rstrip(":") == "Device":
            header = parts[1:]
            report = {}
            continue
        if header and len(parts) == len(header) + 1:
            values = dict(zip(header, map(float, parts[1:])))
            for name in QUEUE_COLUMNS:
                if name in values:
                    values["aqu-sz"] = values[name]
            report[parts[0]] = values
    return report


def saturated_devices(text: str, util: float = 90.0, queue: float = 1.0) -> list[str]:
    devices = parse_iostat(text)
    return sorted(name for name, d in devices.items() if d["%util"] >= util and d["aqu-sz"] >= queue)


def _port(address: str) -> int | None:
    tail = address.rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


def socket_states(text: str, port: int | None = None) -> Counter:
    states: Counter = Counter()
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        if port is None or _port(parts[3]) == port:
            states[parts[0]] += 1
    return states


def listen_overflow(text: str) -> list[str]:
    full = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "LISTEN":
            recv_q, send_q = int(parts[1]), int(parts[2])
            if send_q > 0 and recv_q >= send_q:
                full.append(parts[3])
    return sorted(full)
