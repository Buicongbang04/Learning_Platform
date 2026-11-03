import random


def bucket(request_id: str, salt: str = "") -> float:
    return random.random()


def route(request_id: str, canary_weight: float, salt: str = "") -> str:
    return "canary" if random.random() < canary_weight else "stable"


def assign_variant(user_id: str, experiment: str, weights: dict[str, float]) -> str:
    return next(iter(weights))
