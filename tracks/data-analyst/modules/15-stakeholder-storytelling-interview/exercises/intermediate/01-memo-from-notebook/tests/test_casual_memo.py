import re

import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
KEYS = ["casual_share", "offday_days_share", "offday_casual_share", "casual_share_offday", "casual_share_workday",
        "window_hours_share", "window_casual_share", "casual_share_in_window"]
HEADINGS = ["## Bối cảnh và câu hỏi", "## Khuyến nghị", "## Bằng chứng", "## Giới hạn", "## Bước tiếp theo"]
JARGON = ["groupby", "dataframe", "notebook", "pandas", "workingday", "weathersit", "hour.csv", "nan", "dteday"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("casual_memo.ipynb")


def small_hour():
    rows = [
        # dteday, hr, workingday, casual, registered
        ("2011-04-02", 9, 0, 10, 10),    # ngày nghỉ, ngoài khung giờ
        ("2011-04-02", 10, 0, 30, 10),   # khung
        ("2011-04-02", 17, 0, 20, 20),   # khung (17h thuộc khung)
        ("2011-04-02", 18, 0, 5, 15),    # ngoài khung giờ
        ("2011-04-04", 12, 1, 5, 45),    # ngày làm việc
        ("2011-04-04", 17, 1, 5, 95),
        ("2011-11-05", 12, 0, 20, 20),   # ngày nghỉ, tháng 11: ngoài khung tháng
        ("2011-03-07", 12, 1, 5, 45),    # ngày làm việc tháng 3
    ]
    df = pd.DataFrame(rows, columns=["dteday", "hr", "workingday", "casual", "registered"])
    df["cnt"] = df["casual"] + df["registered"]
    return df


def test_memo_facts_keys_and_values(nb):
    df = small_hour()
    before = df.copy()
    facts = nb.memo_facts(df)
    pd.testing.assert_frame_equal(df, before)
    assert sorted(facts) == sorted(KEYS)
    # casual tổng 100, cnt tổng 360; ngày nghỉ: casual 85 / cnt 160; ngày làm việc: casual 15 / cnt 200
    assert facts["casual_share"] == pytest.approx(100 / 360)
    assert facts["offday_days_share"] == pytest.approx(2 / 4)     # 2/4, 5/11 nghỉ; 4/4, 7/3 làm việc
    assert facts["offday_casual_share"] == pytest.approx(85 / 100)
    assert facts["casual_share_offday"] == pytest.approx(85 / 160)
    assert facts["casual_share_workday"] == pytest.approx(15 / 200)
    assert facts["window_hours_share"] == pytest.approx(2 / 8)
    assert facts["window_casual_share"] == pytest.approx(50 / 100)
    assert facts["casual_share_in_window"] == pytest.approx(50 / 80)


def test_memo_facts_accepts_datetime(nb):
    df = small_hour()
    df["dteday"] = pd.to_datetime(df["dteday"])
    assert nb.memo_facts(df)["window_hours_share"] == pytest.approx(2 / 8)


def test_real_facts(nb):
    hour = pd.read_csv(ex.dataset("bike-sharing-uci") / "hour.csv")
    facts = nb.memo_facts(hour)
    expected = {"casual_share": 0.1883, "offday_days_share": 0.3160, "offday_casual_share": 0.5108,
                "casual_share_offday": 0.3166, "casual_share_workday": 0.1323, "window_hours_share": 0.0612,
                "window_casual_share": 0.2758, "casual_share_in_window": 0.3889}
    for key, value in expected.items():
        assert facts[key] == pytest.approx(value, abs=1e-4), key


# ---------- MEMO.md ----------

def number_forms(facts: dict) -> set[str]:
    forms = set()
    for v in facts.values():
        pct = v * 100
        forms |= {f"{pct:.0f}", f"{pct:.1f}"}
    return forms


def section(memo: str, heading: str) -> str:
    start = memo.index(heading) + len(heading)
    nxt = memo.find("\n## ", start)
    return memo[start:] if nxt == -1 else memo[start:nxt]


@pytest.fixture(scope="module")
def memo():
    return ex.read("MEMO.md")


def test_memo_finished_and_length(memo):
    assert "TODO" not in memo, "Còn dòng TODO trong MEMO.md"
    words = len(memo.split())
    assert 200 <= words <= 450, f"Memo một trang: 200-450 từ, hiện có {words}"


def test_memo_sections_in_order(memo):
    pos = []
    for heading in HEADINGS:
        assert heading in memo, f"Thiếu mục {heading}"
        pos.append(memo.index(heading))
        body = section(memo, heading)
        assert body.strip() and "TODO" not in body, f"Mục {heading} chưa viết"
    assert pos == sorted(pos), "Các mục phải theo thứ tự: " + ", ".join(HEADINGS)


def test_memo_headline_has_fact(nb, memo):
    title = memo.strip().splitlines()[0]
    assert title.startswith("# "), "Dòng đầu là headline dạng '# ...'"
    hour = pd.read_csv(ex.dataset("bike-sharing-uci") / "hour.csv")
    found = {n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", title)}
    forms = number_forms(nb.memo_facts(hour))
    assert found & forms, f"Headline cần ít nhất một con số (phần trăm) lấy từ memo_facts; tìm thấy {sorted(found)}"


def test_memo_evidence_bullets(memo):
    bullets = [line for line in section(memo, "## Bằng chứng").splitlines() if line.lstrip().startswith(("- ", "* "))]
    assert len(bullets) >= 3, "Mục Bằng chứng cần ít nhất ba gạch đầu dòng"
    assert all(re.search(r"\d", b) for b in bullets), "Mỗi bằng chứng cần một con số"


def test_memo_no_jargon(memo):
    assert "TODO" not in memo, "Viết xong memo trước (còn TODO)"
    words = set(re.findall(r"[a-z_.]+", memo.lower()))
    hit = [w for w in JARGON if w in words]
    assert not hit, f"Memo cho người không đọc code: bỏ {hit}"
