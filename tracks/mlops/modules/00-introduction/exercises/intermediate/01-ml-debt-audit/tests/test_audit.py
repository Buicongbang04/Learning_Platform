import pytest

from testkit import Exercise

ex = Exercise(__file__)

CLEAN = {
    "pyproject.toml": "[project]\nname='eta'\n",
    "requirements.txt": "# deps\nscikit-learn==1.5.2\n-r base.txt\n\npandas==2.2.3\n",
    "src/eta/train.py": "from sklearn.model_selection import train_test_split\n"
    "X, y = train_test_split(a, b, random_state=0)\n",
    "tests/test_train.py": "def test_x():\n    pass\n",
    "tests/fixtures/sample.csv": "",
    "dvc.yaml": "stages: {}\n",
}

MESSY = {
    "notebooks/train.ipynb": "{}",
    "model.pkl": "",
    "data/trips.parquet": "",
    "data/raw.CSV": "",
    "requirements.txt": "pandas\nnumpy>=1.26\nscikit-learn==1.5.2\n",
    "requirements-dev.txt": "pytest==8.3.3\n",
}


@pytest.fixture(scope="module")
def audit():
    return ex.module("audit.py")


def test_clean_repo_has_no_findings(audit):
    assert audit.audit(CLEAN) == {}


def test_messy_repo_exact_findings(audit):
    assert audit.audit(MESSY) == {
        "model-artifact-in-git": ["model.pkl"],
        "data-in-git": ["data/raw.CSV", "data/trips.parquet"],
        "unpinned-dependency": ["requirements.txt"],
        "no-tests": ["."],
        "notebook-only-code": ["notebooks/train.ipynb"],
    }


@pytest.mark.parametrize("path", ["m.pkl", "a/b/m.joblib", "w/net.PT", "x.onnx", "k.h5", "s.pickle"])
def test_model_artifacts(audit, path):
    assert audit.model_artifact_in_git({path: "", "tests/test_a.py": ""}) == [path]


def test_model_artifact_not_substring(audit):
    assert audit.model_artifact_in_git({"docs/pkl-notes.md": "", "pklfile.py": ""}) == []


def test_data_allowed_in_tests_and_fixtures(audit):
    files = {"tests/data.csv": "", "pkg/fixtures/a.parquet": "", "data/a.feather": ""}
    assert audit.data_in_git(files) == ["data/a.feather"]


def test_data_dir_named_like_tests_but_not(audit):
    assert audit.data_in_git({"latests/a.csv": ""}) == ["latests/a.csv"]


@pytest.mark.parametrize(
    "line,hit",
    [
        ('DATA = "/home/bang/data/x.csv"', True),
        ("path: /Users/an/project", True),
        ('p = r"C:\\data\\x.csv"', True),
        ("# /home/bang/old.csv", False),
        ('DATA = Path(os.environ["DATA_DIR"])', False),
        ("url = 'https://example.com/home/'", False),
        ('msg = "Note:\\nnext line"', False),
        ('p = "D:\\\\models\\\\m.bin"', True),
    ],
)
def test_hardcoded_path(audit, line, hit):
    got = audit.hardcoded_path({"cfg.py": line + "\n"})
    assert got == (["cfg.py"] if hit else [])


def test_hardcoded_path_ignores_other_extensions(audit):
    assert audit.hardcoded_path({"README.md": "/home/bang/x", "n.ipynb": "/home/bang/x"}) == []


def test_unseeded_split(audit):
    files = {"a.py": "train_test_split(X, y, test_size=0.2)\n", "b.py": "train_test_split(X, y, random_state=1)\n"}
    assert audit.unseeded_randomness(files) == ["a.py"]


def test_unseeded_model_constructor(audit):
    files = {
        "a.py": "m = RandomForestRegressor(n_estimators=100)\n",
        "b.py": "m = GradientBoostingRegressor(random_state=7)\n",
        "c.py": "m = RandomForestClassifier()\n",
    }
    assert audit.unseeded_randomness(files) == ["a.py", "c.py"]


def test_one_unseeded_call_among_seeded_ones(audit):
    text = "train_test_split(a, random_state=1)\nRandomForestClassifier(max_depth=3)\n"
    assert audit.unseeded_randomness({"x.py": text}) == ["x.py"]


def test_unseeded_only_checks_py(audit):
    assert audit.unseeded_randomness({"x.md": "train_test_split(a)"}) == []


def test_unpinned_dependency_rules(audit):
    files = {
        "requirements.txt": "# c\n\n-r base.txt\n-e .\nnumpy==1.26.4\n",
        "sub/requirements-dev.txt": "pytest>=8\n",
        "requirements.in": "numpy\n",
        "notes.txt": "numpy\n",
    }
    assert audit.unpinned_dependency(files) == ["sub/requirements-dev.txt"]


def test_no_tests_variants(audit):
    assert audit.no_tests({"src/a.py": ""}) == ["."]
    assert audit.no_tests({"tests/conftest.py": ""}) == []
    assert audit.no_tests({"pkg/test_a.py": ""}) == []
    assert audit.no_tests({"src/contest.py": ""}) == ["."]
    assert audit.no_tests({"pkg/tests/conftest.py": ""}) == []
    assert audit.no_tests({"pkg/latests/conftest.py": ""}) == ["."]


def test_notebook_only_nested_tests(audit):
    assert audit.notebook_only_code({"a.ipynb": "", "pkg/tests/helpers.py": ""}) == ["a.ipynb"]


def test_notebook_only(audit):
    assert audit.notebook_only_code({"a.ipynb": "", "b.ipynb": ""}) == ["a.ipynb", "b.ipynb"]
    assert audit.notebook_only_code({"a.ipynb": "", "src/x.py": ""}) == []
    assert audit.notebook_only_code({"a.ipynb": "", "tests/test_x.py": ""}) == ["a.ipynb"]
    assert audit.notebook_only_code({"src/x.py": ""}) == []


def test_audit_sorted_and_unique(audit):
    files = {"z/m.pkl": "", "a/m.pkl": "", "tests/test_a.py": ""}
    assert audit.audit(files) == {"model-artifact-in-git": ["a/m.pkl", "z/m.pkl"]}


def test_verdict(audit):
    assert audit.verdict({}) == "ok"
    assert audit.verdict({"no-tests": ["."]}) == "warn"
    assert audit.verdict({"no-tests": ["."], "hardcoded-path": ["a.py"]}) == "block"
    assert audit.verdict({"data-in-git": ["d.csv"]}) == "block"
    assert audit.verdict({"unpinned-dependency": ["requirements.txt"], "unseeded-randomness": ["a.py"]}) == "warn"
