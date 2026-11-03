from eta.config import Config


def log_and_register(model, metrics: dict, config: Config, data_version: str) -> str:
    raise NotImplementedError("M04: log run, đăng ký model, tag git_commit và data_version, trả version")
