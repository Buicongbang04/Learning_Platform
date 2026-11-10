"""Phát hiện thiên lệch do model tự gây: nhãn chỉ có ở giao dịch model cho qua."""


def naive_rate(log: list[dict]) -> float | None:
    raise NotImplementedError("TODO 1: tỉ lệ gian lận trên các dòng có nhãn")


def ipw_rate(log: list[dict]) -> float | None:
    raise NotImplementedError("TODO 2: ước lượng tỉ lệ gian lận của mọi giao dịch")


def bias_report(log: list[dict], tolerance: float = 0.01) -> dict:
    raise NotImplementedError("TODO 3: {'naive', 'ipw', 'gap', 'biased'}")


def per_round(log: list[dict], tolerance: float = 0.01) -> list[dict]:
    raise NotImplementedError("TODO 4: bias_report cho từng vòng, thêm khoá 'round'")
