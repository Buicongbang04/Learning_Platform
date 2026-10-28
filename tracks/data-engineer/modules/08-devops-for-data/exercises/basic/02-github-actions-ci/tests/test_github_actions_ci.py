import yaml

from testkit import Exercise

ex = Exercise(__file__)


def load():
    doc = yaml.safe_load(ex.read("ci.yml"))
    assert isinstance(doc, dict), "ci.yml phải là một mapping YAML"
    return doc


def triggers(doc):
    # PyYAML (YAML 1.1) đọc `on` thành True
    on = doc.get("on", doc.get(True))
    assert on is not None, "Thiếu khoá on"
    if isinstance(on, str):
        on = {on: None}
    if isinstance(on, list):
        on = {k: None for k in on}
    return on


def steps(doc):
    job = doc["jobs"]["test"]
    return job.get("steps") or []


def test_name():
    assert load().get("name") == "ci"


def test_triggers():
    on = triggers(load())
    assert "push" in on, "Thiếu trigger push"
    push = on["push"] or {}
    assert "main" in (push.get("branches") or []), "push phải giới hạn ở nhánh main"
    assert "pull_request" in on, "Thiếu trigger pull_request"


def test_permissions():
    assert load().get("permissions") == {"contents": "read"}


def test_job_runner_and_timeout():
    doc = load()
    assert "test" in doc.get("jobs", {}), "Cần job tên test"
    job = doc["jobs"]["test"]
    assert str(job.get("runs-on", "")).startswith("ubuntu")
    timeout = job.get("timeout-minutes")
    assert isinstance(timeout, int) and 1 <= timeout <= 30, "timeout-minutes phải trong 1..30"


def test_checkout_first():
    st = steps(load())
    uses = [i for i, s in enumerate(st) if s.get("uses") == "actions/checkout@v4"]
    assert uses, "Thiếu actions/checkout@v4"
    runs = [i for i, s in enumerate(st) if "run" in s]
    assert all(uses[0] < r for r in runs), "Checkout phải đứng trước mọi step run"


def test_setup_python():
    st = steps(load())
    setup = [s for s in st if str(s.get("uses", "")).startswith("actions/setup-python@v5")]
    assert setup, "Thiếu actions/setup-python@v5"
    with_ = setup[0].get("with") or {}
    assert with_.get("python-version") == "3.12", "python-version phải là chuỗi \"3.12\""
    assert with_.get("cache") == "pip"


def test_install_then_pytest():
    st = steps(load())
    runs = [str(s["run"]) for s in st if "run" in s]
    install = [i for i, r in enumerate(runs) if "pip install -r requirements.txt" in r]
    tests = [i for i, r in enumerate(runs) if "pytest" in r and "echo" not in r]
    assert install, "Thiếu bước pip install -r requirements.txt"
    assert tests, "Thiếu bước chạy pytest"
    assert install[0] < tests[-1]
