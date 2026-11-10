def build_request(feature_refs: list[str], zone_ids: list[int]) -> dict:
    if not feature_refs:
        raise ValueError("feature_refs rỗng")
    if not zone_ids:
        raise ValueError("zone_ids rỗng")
    unique = list(dict.fromkeys(int(z) for z in zone_ids))
    return {"features": list(feature_refs), "entities": {"zone_id": unique}}


def parse_response(response: dict, defaults: dict) -> tuple[dict, dict]:
    names = response["metadata"]["feature_names"]
    columns = dict(zip(names, response["results"]))
    zone_ids = [int(z) for z in columns["zone_id"]["values"]]
    values: dict[int, dict] = {z: {} for z in zone_ids}
    defaulted: dict[int, list[str]] = {}
    for name in names:
        if name == "zone_id":
            continue
        column = columns[name]
        for zone_id, value, status in zip(zone_ids, column["values"], column["statuses"]):
            if value is None or status != "PRESENT":
                values[zone_id][name] = defaults[name]
                defaulted.setdefault(zone_id, []).append(name)
            else:
                values[zone_id][name] = value
    return values, {z: sorted(n) for z, n in defaulted.items()}
