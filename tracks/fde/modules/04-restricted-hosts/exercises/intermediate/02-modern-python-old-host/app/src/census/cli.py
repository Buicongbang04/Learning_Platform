import csv
import itertools
import json
import platform
import sys
from collections import Counter
from datetime import date
from importlib.metadata import version

from pydantic import BaseModel, Field

type WardCounts = dict[str, int]


class Admission(BaseModel):
    patient: str = Field(min_length=1)
    ward: str = Field(min_length=1)
    admitted: date
    discharged: date | None = None


def read(path: str) -> list[Admission]:
    with open(path, newline="", encoding="utf-8") as handle:
        return [Admission.model_validate({k: v or None for k, v in row.items()}) for row in csv.DictReader(handle)]


def occupied(admissions: list[Admission], day: date) -> WardCounts:
    counts = Counter(a.ward for a in admissions if a.admitted <= day and (a.discharged is None or a.discharged > day))
    return dict(sorted(counts.items()))


def main() -> int:
    if len(sys.argv) != 3:
        print("Cách dùng: census <admissions.csv> <YYYY-MM-DD>", file=sys.stderr)
        return 2
    admissions = read(sys.argv[1])
    day = date.fromisoformat(sys.argv[2])
    wards = occupied(admissions, day)
    pages = [len(page) for page in itertools.batched(admissions, 100)]
    print(json.dumps({
        "day": day.isoformat(),
        "occupied": wards,
        "total": sum(wards.values()),
        "records": sum(pages),
        "versions": {"python": platform.python_version(), "pydantic": version("pydantic"),
                     "pydantic_core": version("pydantic-core")},
        "executable": sys.executable,
    }, ensure_ascii=False))
    return 0
