def estimate(scenario: dict, prices: dict) -> dict:
    """{"train", "serve", "idle_serve", "storage", "egress", "total"}, mỗi số round 2 chữ số.

    Công thức và luật kiểm tra đầu vào nằm trong README.
    """
    # TODO
    raise NotImplementedError


def idle_share(est: dict) -> float:
    """idle_serve / total, round 4 chữ số; 0.0 khi total bằng 0."""
    # TODO
    raise NotImplementedError


def savings(scenario: dict, prices: dict, **overrides) -> dict:
    """Áp overrides lên một bản sao kịch bản; trả {"before", "after", "saved"}."""
    # TODO
    raise NotImplementedError
