import hashlib
import math


def bucket(request_id: str, salt: str = "") -> float:
    digest = hashlib.sha256(f"{salt}:{request_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def route(request_id: str, canary_weight: float, salt: str = "") -> str:
    if not 0.0 <= canary_weight <= 1.0:
        raise ValueError("canary_weight phải trong [0, 1]")
    return "canary" if bucket(request_id, salt) < canary_weight else "stable"


def assign_variant(user_id: str, experiment: str, weights: dict[str, float]) -> str:
    if not weights or any(w < 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("weights phải không âm và có tổng bằng 1")
    point = bucket(user_id, experiment)
    cumulative = 0.0
    chosen = None
    for name in sorted(weights):
        if weights[name] == 0:
            continue
        cumulative += weights[name]
        chosen = name
        if point < cumulative:
            return name
    return chosen
