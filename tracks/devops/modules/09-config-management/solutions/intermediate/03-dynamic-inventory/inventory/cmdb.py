#!/usr/bin/env python3
"""Inventory động của Olist Shop: đọc bản export CMDB (JSON) ở đường dẫn trong OLIST_CMDB_FILE."""

import argparse
import json
import os
import re
import sys


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["hosts"]


def build(records: list[dict]) -> dict:
    groups: dict[str, set[str]] = {}
    hostvars: dict[str, dict] = {}
    for record in records:
        if str(record.get("status", "")).strip().lower() != "active":
            continue
        name = record["name"]
        az = record.get("az")
        hostvars[name] = {
            "ansible_host": record["ip"],
            "olist_role": record["role"].strip().lower(),
            "olist_env": record["env"].strip().lower(),
            "olist_az": az.strip().lower() if az else None,
            "olist_cpu": int(record.get("cpu", 1)),
            "olist_canary": bool(record.get("canary", False)),
        }
        keys = [f"role_{slug(record['role'])}", f"env_{slug(record['env'])}"]
        if az:
            keys.append(f"az_{slug(az)}")
        for key in keys:
            groups.setdefault(key, set()).add(name)
    inventory = {group: {"hosts": sorted(members)} for group, members in sorted(groups.items())}
    inventory["_meta"] = {"hostvars": hostvars}
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--host")
    args = parser.parse_args()
    path = os.environ.get("OLIST_CMDB_FILE")
    if not path:
        print("Chưa đặt OLIST_CMDB_FILE (đường dẫn bản export CMDB dạng JSON)", file=sys.stderr)
        return 2
    try:
        records = load(path)
    except (OSError, ValueError, KeyError) as error:
        print(f"Không đọc được CMDB ở OLIST_CMDB_FILE={path}: {error}", file=sys.stderr)
        return 2
    print(json.dumps(build(records) if args.list else {}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
