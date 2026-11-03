"""Client cho Feast feature server (REST). Chỉ dùng thư viện chuẩn: tệp này chạy cả ở host lẫn trong container."""


def build_request(feature_refs: list[str], zone_ids: list[int]) -> dict:
    raise NotImplementedError("TODO: thân JSON cho POST /get-online-features")


def parse_response(response: dict, defaults: dict) -> tuple[dict, dict]:
    raise NotImplementedError("TODO: trả (values, defaulted), xem đề bài")
