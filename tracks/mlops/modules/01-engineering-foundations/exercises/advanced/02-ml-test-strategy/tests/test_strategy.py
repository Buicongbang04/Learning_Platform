import yaml

from testkit import Exercise

ex = Exercise(__file__)
KINDS = {"unit", "data", "model-behavior", "model-quality", "contract", "smoke"}
RUNS = {"pr", "nightly", "release"}


def load():
    return yaml.safe_load(ex.read("test-strategy.yaml"))


def test_layers_are_complete_and_use_known_values():
    layers = load()["layers"]
    assert len(layers) >= 6, f"Cần ít nhất 6 lớp, mới có {len(layers)}"
    for layer in layers:
        assert layer["kind"] in KINDS, f"kind không hợp lệ: {layer.get('kind')}"
        assert layer["runs_on"] in RUNS, f"runs_on không hợp lệ ở {layer.get('name')}"
        assert isinstance(layer["budget_seconds"], int) and layer["budget_seconds"] > 0
        assert len(str(layer["what"])) >= 20 and len(str(layer["catches"])) >= 20, f"Mô tả quá ngắn ở {layer['name']}"
    assert len({layer["name"] for layer in layers}) == len(layers), "Tên lớp phải duy nhất"


def test_core_ml_layers_are_covered():
    kinds = {layer["kind"] for layer in load()["layers"]}
    assert {"unit", "data", "model-behavior", "model-quality"} <= kinds


def test_pr_stays_inside_the_budget_and_slow_layers_move_out_of_pr():
    config = load()
    pr = [layer for layer in config["layers"] if layer["runs_on"] == "pr"]
    assert sum(layer["budget_seconds"] for layer in pr) <= config["pr_budget_seconds"] <= 600
    assert any(layer["runs_on"] != "pr" for layer in config["layers"]), "Phải có lớp chạy ngoài PR"
    quality = [layer for layer in config["layers"] if layer["kind"] == "model-quality"]
    assert all(layer["runs_on"] != "pr" or layer["budget_seconds"] <= 120 for layer in quality), "Train lại model đầy đủ không thuộc PR"


def test_catches_are_distinct_and_not_copied_from_what():
    layers = load()["layers"]
    catches = [str(layer["catches"]).strip().lower() for layer in layers]
    assert len(set(catches)) == len(catches), "Mỗi lớp phải bắt một lỗi khác nhau"
    assert all(str(layer["catches"]).strip().lower() != str(layer["what"]).strip().lower() for layer in layers)


def test_flaky_policy_and_honest_gaps():
    config = load()
    policy = config["flaky_policy"]
    assert policy["max_retries"] in (0, 1), "Retry vô hạn che lỗi thật"
    assert isinstance(policy["quarantine"], bool) and policy["owner"] and int(policy["deadline_days"]) > 0
    gaps = config["gaps"]
    assert len(gaps) >= 3
    assert all(len(str(g["risk"])) >= 10 and len(str(g["reason"])) >= 20 for g in gaps)
