from dataclasses import dataclass, field


@dataclass
class Policy:
    max_mae_regression: float = 0.0
    max_airport_regression: float = 0.05


@dataclass
class Decision:
    promote: bool
    reasons: list[str] = field(default_factory=list)


def decide(challenger: dict, champion: dict | None, policy: Policy) -> Decision:
    raise NotImplementedError("M04: luật promotion")


def promote_if_better(name: str, version: str, policy: Policy) -> Decision:
    raise NotImplementedError("M04: so với alias champion, đặt alias khi qua cổng")
