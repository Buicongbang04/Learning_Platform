import copy


def _price(prices: dict, instance: str) -> float:
    try:
        return float(prices["compute_hourly"][instance])
    except KeyError:
        raise ValueError(f"instance không có trong bảng giá: {instance}") from None


def estimate(scenario: dict, prices: dict) -> dict:
    train, serve = scenario["train"], scenario["serve"]
    if not 0 <= serve["utilization"] <= 1:
        raise ValueError("utilization phải nằm trong [0, 1]")
    if serve["replicas"] < 0 or train["runs_per_month"] < 0:
        raise ValueError("replicas và runs_per_month không được âm")
    train_cost = _price(prices, train["instance"]) * train["hours_per_run"] * train["runs_per_month"]
    if train.get("spot"):
        train_cost *= prices["spot_multiplier"]
    scale_to_zero = bool(serve.get("scale_to_zero"))
    billed_hours = prices["hours_per_month"] * (serve["utilization"] if scale_to_zero else 1)
    serve_cost = _price(prices, serve["instance"]) * serve["replicas"] * billed_hours
    if serve.get("committed"):
        serve_cost *= prices["committed_multiplier"]
    idle = 0.0 if scale_to_zero else serve_cost * (1 - serve["utilization"])
    storage = scenario["storage_gb"] * prices["storage_gb_month"]
    egress = scenario["egress_gb"] * prices["egress_gb"]
    total = train_cost + serve_cost + storage + egress
    return {
        "train": round(train_cost, 2),
        "serve": round(serve_cost, 2),
        "idle_serve": round(idle, 2),
        "storage": round(storage, 2),
        "egress": round(egress, 2),
        "total": round(total, 2),
    }


def idle_share(est: dict) -> float:
    return round(est["idle_serve"] / est["total"], 4) if est["total"] else 0.0


def savings(scenario: dict, prices: dict, **overrides) -> dict:
    changed = copy.deepcopy(scenario)
    for key, value in overrides.items():
        if key in ("train", "serve"):
            changed[key].update(value)
        else:
            changed[key] = value
    before = estimate(scenario, prices)["total"]
    after = estimate(changed, prices)["total"]
    return {"before": before, "after": after, "saved": round(before - after, 2)}
