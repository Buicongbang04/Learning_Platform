def train_flow(config_path: str, months: list[str]) -> str:
    raise NotImplementedError("M05: flow Prefect train + đăng ký, cache theo data_version và params, trả version")


def batch_score_flow(month: str, config_path: str, out_dir: str) -> str:
    raise NotImplementedError("M05: chấm cả tháng bằng champion, ghi predictions_<month>.parquet, trả đường dẫn")


def replay_flow(start: str, end: str, config_path: str, out_dir: str) -> list[dict]:
    raise NotImplementedError("M05: phát lại từng tháng, mae chỉ tính khi nhãn đã công bố tại as_of")
