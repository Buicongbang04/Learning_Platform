import csv
import yaml

params = yaml.safe_load(open("params.yaml"))["prepare"]
with open("data/raw/trips.csv") as f:
    rows = [r for r in csv.DictReader(f) if float(r["trip_distance"]) > params["min_distance"]]
with open("data/clean.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["trip_id", "trip_distance"])
    writer.writeheader()
    writer.writerows(rows)
