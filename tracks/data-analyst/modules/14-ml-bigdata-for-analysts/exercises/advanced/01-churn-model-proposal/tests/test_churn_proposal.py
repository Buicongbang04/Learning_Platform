import re

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from sklearn.model_selection import train_test_split

from testkit import Exercise

ex = Exercise(__file__)
COLUMNS = ["churners_reached", "capture", "precision", "expected_saves", "cost", "expected_value", "net",
           "random_net", "net_vs_random"]
HEADINGS = ["## Đề xuất", "## Model làm được gì", "## Giá trị kinh doanh (giả định)", "## Rủi ro và giới hạn",
            "## Pilot và cách đo"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("churn_proposal.ipynb")


Y = [1, 0, 1, 0, 0, 1, 0, 0, 0, 0]
SCORE = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]


def test_campaign_table(nb):
    out = nb.campaign_table(Y, SCORE, [2, 0, 10], contact_cost=10, value_per_save=200, save_rate=0.5)
    assert list(out.columns) == COLUMNS
    assert out.index.name == "contacted" and list(out.index) == [2, 0, 10]
    row = out.loc[2]
    assert row["churners_reached"] == 1 and row["capture"] == pytest.approx(1 / 3)
    assert row["precision"] == pytest.approx(0.5)
    assert row["expected_saves"] == pytest.approx(0.5) and row["cost"] == pytest.approx(20)
    assert row["expected_value"] == pytest.approx(100) and row["net"] == pytest.approx(80)
    assert row["random_net"] == pytest.approx(2 * 0.3 * 0.5 * 200 - 20)          # 40
    assert row["net_vs_random"] == pytest.approx(40)
    assert out.loc[0, "precision"] == 0.0 and out.loc[0, "net"] == 0.0
    assert out.loc[10, "net_vs_random"] == pytest.approx(0.0)                  # gọi hết = ngẫu nhiên


def test_campaign_table_order_and_ties(nb):
    y = np.array([0, 1, 0, 1])
    score = np.array([0.5, 0.5, 0.9, 0.1])                                    # chưa sắp, hoà 0.5
    out = nb.campaign_table(y, score, [1, 2, 3], contact_cost=0, value_per_save=1, save_rate=1)
    # thứ tự: 0.9 (y=0), 0.5 (vị trí 0, y=0), 0.5 (vị trí 1, y=1), 0.1
    assert out["churners_reached"].tolist() == [0, 0, 1]
    assert out["churners_reached"].dtype.kind == "i"


@pytest.mark.parametrize("kwargs", [
    {"budgets": [11]}, {"budgets": [-1]}, {"budgets": [2.5]}, {"save_rate": 1.5}, {"contact_cost": -1},
    {"value_per_save": -5}, {"score": SCORE[:-1]},
])
def test_campaign_table_rejects_bad_input(nb, kwargs):
    args = {"y_true": Y, "score": SCORE, "budgets": [2], "contact_cost": 10, "value_per_save": 200, "save_rate": 0.5}
    args.update(kwargs)
    with pytest.raises(ValueError):
        nb.campaign_table(**args)


def test_real_campaign(nb):
    raw = pd.read_csv(ex.dataset("telco-churn") / "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    X = pd.DataFrame({
        "contract_one_year": (raw.Contract == "One year").astype(int),
        "contract_two_year": (raw.Contract == "Two year").astype(int),
        "tenure_years": raw.tenure / 12,
        "fiber_optic": (raw.InternetService == "Fiber optic").astype(int),
        "no_internet": (raw.InternetService == "No").astype(int),
        "electronic_check": (raw.PaymentMethod == "Electronic check").astype(int),
        "monthly_charges_10": raw.MonthlyCharges / 10,
        "senior": raw.SeniorCitizen,
        "tech_support": (raw.TechSupport == "Yes").astype(int),
        "paperless": (raw.PaperlessBilling == "Yes").astype(int),
    })
    y = (raw.Churn == "Yes").astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    score = sm.Logit(y_train, sm.add_constant(X_train)).fit(disp=0).predict(sm.add_constant(X_test))
    out = nb.campaign_table(y_test, score, [476, 1200], contact_cost=15, value_per_save=600, save_rate=0.25)
    assert out.loc[476, "churners_reached"] == 286
    assert out.loc[476, "net"] == pytest.approx(35_760)
    assert out.loc[1200, "churners_reached"] == 454


def test_proposal_written():
    text = ex.read("PROPOSAL.md")
    assert "TODO" not in text, "Còn dòng TODO trong PROPOSAL.md"
    words = len(text.split())
    assert 250 <= words <= 700, f"Đề xuất ba phút: 250-700 từ, hiện có {words}"
    title = text.strip().splitlines()[0]
    assert title.startswith("# ") and re.search(r"\d", title), "Dòng đầu là headline: kết luận có con số"
    for heading in HEADINGS:
        assert heading in text, f"Thiếu mục {heading}"
    assert re.search(r"giả định", text.split("## Giá trị kinh doanh (giả định)")[1], re.I), \
        "Mục giá trị kinh doanh phải nói rõ giả định"
