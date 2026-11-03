import csv
import random
import yaml

params = yaml.safe_load(open("params.yaml"))["split"]
with open("data/clean.csv") as f:
    rows = list(csv.DictReader(f))
random.Random(params["seed"]).shuffle(rows)
cut = int(len(rows) * params["test_size"])
for name, part in (("test", rows[:cut]), ("train", rows[cut:])):
    with open(f"data/{name}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trip_id", "trip_distance"])
        writer.writeheader()
        writer.writerows(part)
