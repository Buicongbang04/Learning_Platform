import math
from dataclasses import dataclass, field

from eta.registry import ALIAS


@dataclass
class Policy:
    max_mae_regression: float = 0.0
    max_airport_regression: float = 0.05


@dataclass
class Decision:
    promote: bool
    reasons: list[str] = field(default_factory=list)


def _value(metrics: dict, key: str) -> float:
    try:
        value = float(metrics[key])
    except (KeyError, TypeError, ValueError):
        return math.nan
    return value


def _compare(key: str, challenger: dict, champion: dict, allowed: float) -> tuple[bool, str]:
    new, old = _value(challenger, key), _value(champion, key)
    if math.isnan(new):
        return False, f"{key}: challenger không có số đo, không thể so"
    if math.isnan(old):
        return True, f"{key}: champion không có số đo, bỏ qua tiêu chí này"
    limit = old * (1 + allowed)
    ok = new <= limit
    verdict = "đạt" if ok else "trượt"
    return ok, f"{key} {verdict}: challenger {new:.1f} so với ngưỡng {limit:.1f} (champion {old:.1f}, cho phép tệ hơn {allowed:.0%})"


def decide(challenger: dict, champion: dict | None, policy: Policy) -> Decision:
    if champion is None:
        ok = not math.isnan(_value(challenger, "mae"))
        reason = "chưa có champion, challenger thành champion đầu tiên" if ok else "mae: challenger không có số đo"
        return Decision(ok, [reason])
    checks = [
        _compare("mae", challenger, champion, policy.max_mae_regression),
        _compare("mae_airport", challenger, champion, policy.max_airport_regression),
    ]
    reasons = [reason for _, reason in checks]
    if not checks[1][0]:
        reasons.append("chặn vì nhóm chuyến sân bay (airport: JFK, LaGuardia) tệ hơn mức cho phép")
    return Decision(all(ok for ok, _ in checks), reasons)


def _version_metrics(client, name: str, version: str) -> dict:
    run_id = client.get_model_version(name, version).run_id
    return dict(client.get_run(run_id).data.metrics)


def promote_if_better(name: str, version: str, policy: Policy) -> Decision:
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    client = MlflowClient()
    challenger = _version_metrics(client, name, version)
    try:
        current = client.get_model_version_by_alias(name, ALIAS)
    except MlflowException:
        current = None
    if current is not None and current.version == str(version):
        return Decision(False, [f"version {version} đã là {ALIAS}"])
    champion = _version_metrics(client, name, current.version) if current is not None else None
    decision = decide(challenger, champion, policy)
    client.set_model_version_tag(name, str(version), "promotion", "passed" if decision.promote else "rejected")
    client.set_model_version_tag(name, str(version), "promotion_reasons", " | ".join(decision.reasons)[:5000])
    if decision.promote:
        client.set_registered_model_alias(name, ALIAS, str(version))
    return decision
