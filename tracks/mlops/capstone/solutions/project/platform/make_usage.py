"""Sinh `platform/usage.csv` (log sử dụng 30 ngày của cụm dùng chung, tháng 11/2019) cho M17. Chạy lại cho ra đúng tệp đó.

Số giả lập theo cấu hình thật của capstone: ETA serve 2 replica (M12, M14), retrain Ray hằng đêm (M15), model tip của đội
pricing onboard từ ngày 11 (M17), notebook không gắn nhãn, và một namespace thử nghiệm chưa đăng ký đội.
"""

import csv
import random
import sys
from pathlib import Path

FIELDS = ["date", "namespace", "model", "workload", "cpu_hours", "gpu_hours", "mem_gb_hours"]


def rows(seed: int = 2019) -> list[dict]:
    rng = random.Random(seed)
    out = []

    def add(day, namespace, model, workload, cpu, gpu, mem):
        out.append({"date": f"2019-11-{day:02d}", "namespace": namespace, "model": model, "workload": workload,
                    "cpu_hours": f"{cpu:.2f}", "gpu_hours": f"{gpu:.2f}", "mem_gb_hours": f"{mem:.2f}"})

    for day in range(1, 31):
        replicas = 2 + (rng.random() < 0.3)
        add(day, "eta-prod", "eta", "serve", 24 * replicas * 1.0, 0.0, 24 * replicas * 2.0)
        add(day, "eta-train", "eta", "train", rng.uniform(10, 14), 0.0, rng.uniform(40, 56))
        if day % 7 == 3:
            add(day, "eta-train", "eta", "train", 6.0, rng.uniform(1.5, 2.5), 24.0)
        if day % 3 == 0:
            add(day, "eta-train", "", "notebook", rng.uniform(2, 5), 0.0, rng.uniform(8, 16))
        if day >= 11:
            add(day, "pricing", "pricing-tip-amount", "serve", 24 * 0.5, 0.0, 24 * 1.0)
            if day % 7 == 4:
                add(day, "pricing", "pricing-tip-amount", "train", rng.uniform(0.5, 1.0), 0.0, rng.uniform(2, 3))
        if day % 5 == 1:
            add(day, "ds-sandbox", "", "notebook", rng.uniform(3, 8), rng.uniform(0, 1.5), rng.uniform(10, 30))
    return out


def main(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows())


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("usage.csv"))
