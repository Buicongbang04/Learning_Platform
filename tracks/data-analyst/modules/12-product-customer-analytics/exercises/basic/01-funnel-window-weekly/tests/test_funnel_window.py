import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
WEEK = pd.Timedelta(days=7)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("funnel_window.ipynb")


def events(rows):
    out = pd.DataFrame(rows, columns=["visitor_id", "event", "item_id", "event_time"])
    out["event_time"] = pd.to_datetime(out["event_time"])
    return out


def small_log():
    return events([
        (1, "view", 10, "2015-05-04 10:00"),          # v1: xem -> giỏ -> mua trong 1 giờ
        (1, "addtocart", 10, "2015-05-04 10:30"),
        (1, "transaction", 10, "2015-05-04 11:00"),
        (2, "addtocart", 11, "2015-05-04 09:00"),     # v2: thêm giỏ TRƯỚC lần xem đầu, không thêm lại
        (2, "view", 11, "2015-05-04 10:00"),
        (2, "transaction", 11, "2015-05-04 12:00"),   # mua nhưng không có giỏ hợp lệ: không tính
        (3, "view", 12, "2015-05-06 08:00"),          # v3: lần xem đầu là 05/05
        (3, "view", 12, "2015-05-05 08:00"),
        (3, "addtocart", 12, "2015-05-20 08:00"),     # giỏ và mua sau 15 ngày: ngoài cửa sổ 7 ngày
        (3, "transaction", 12, "2015-05-20 09:00"),
        (4, "transaction", 13, "2015-05-06 10:00"),   # v4: chỉ có mua, không vào funnel
        (5, "view", 14, "2015-05-11 08:00"),          # v5: tuần sau
        (5, "transaction", 14, "2015-05-11 08:01"),   # mua trước khi thêm giỏ: không tính lần này
        (5, "addtocart", 14, "2015-05-11 08:05"),
        (5, "transaction", 14, "2015-05-12 08:00"),   # đúng 24 giờ sau lần xem đầu
        (6, "view", 15, "2015-05-11 09:00"),          # v6: chỉ xem
    ])


def test_to_events(nb):
    raw = pd.DataFrame({"timestamp": [1433221332117, 1430622000000], "visitorid": [257597, 1],
                        "event": ["view", "addtocart"], "itemid": [355908, 2],
                        "transactionid": [None, None], "date": ["2015-06-02", "2015-05-03"]})
    out = nb.to_events(raw)
    assert list(out.columns) == ["visitor_id", "event", "item_id", "event_time"]
    assert out.event_time.tolist() == [pd.Timestamp("2015-06-02 05:02:12.117"), pd.Timestamp("2015-05-03 03:00:00")]
    assert out.visitor_id.tolist() == [257597, 1]


def test_ordered_first_times(nb):
    ft = nb.ordered_first_times(small_log())
    assert list(ft.columns) == ["t_view", "t_cart", "t_buy"]
    assert sorted(ft.index) == [1, 2, 3, 5, 6], "Chỉ visitor có ít nhất một lần xem"
    assert ft.loc[1].tolist() == [pd.Timestamp(x) for x in ["2015-05-04 10:00", "2015-05-04 10:30", "2015-05-04 11:00"]]
    assert ft.loc[2, "t_view"] == pd.Timestamp("2015-05-04 10:00")
    assert pd.isna(ft.loc[2, "t_cart"]) and pd.isna(ft.loc[2, "t_buy"]), "Giỏ trước lần xem đầu không tính"
    assert ft.loc[3, "t_view"] == pd.Timestamp("2015-05-05 08:00"), "Lần xem đầu là thời điểm nhỏ nhất"
    assert ft.loc[5, "t_buy"] == pd.Timestamp("2015-05-12 08:00"), "Mua phải vào hoặc sau lần thêm giỏ đầu"
    assert ft.notna().sum().tolist() == [5, 3, 3]


def test_ordered_first_times_does_not_mutate_input(nb):
    log = small_log()
    before = log.copy()
    nb.ordered_first_times(log)
    pd.testing.assert_frame_equal(log, before)


def test_conversion_within(nb):
    ft = nb.ordered_first_times(small_log())
    out = nb.conversion_within(ft, [1, 24, 168])
    assert out.name == "share_of_buyers"
    assert list(out.index) == [1, 24, 168]
    # 3 người mua: 1 giờ (v1), đúng 24 giờ (v5, tính là trong 24 giờ), 15 ngày (v3)
    assert out.tolist() == pytest.approx([1 / 3, 2 / 3, 2 / 3])


def test_weekly_funnel(nb):
    ft = nb.ordered_first_times(small_log())
    out = nb.weekly_funnel(ft, WEEK, pd.Timestamp("2015-05-20"))
    assert list(out.columns) == ["visitors", "cart_rate", "buy_rate", "mature"]
    assert list(out.index) == [pd.Timestamp("2015-05-04"), pd.Timestamp("2015-05-11")], "Tuần bắt đầu thứ Hai"
    assert out.visitors.tolist() == [3, 2]
    assert out.cart_rate.tolist() == pytest.approx([1 / 3, 1 / 2]), "Giỏ sau 15 ngày nằm ngoài cửa sổ"
    assert out.buy_rate.tolist() == pytest.approx([1 / 3, 1 / 2])
    # tuần 04/05 cần quan sát tới 18/05; tuần 11/05 cần tới 25/05 > 20/05
    assert out.mature.tolist() == [True, False]
    later = nb.weekly_funnel(ft, WEEK, pd.Timestamp("2015-05-25"))
    assert later.mature.tolist() == [True, True]


def test_weekly_funnel_longer_window(nb):
    ft = nb.ordered_first_times(small_log())
    out = nb.weekly_funnel(ft, pd.Timedelta(days=30), pd.Timestamp("2015-07-01"))
    assert out.buy_rate.tolist() == pytest.approx([2 / 3, 1 / 2]), "Cửa sổ 30 ngày tính được v3"


@pytest.fixture(scope="module")
def real_events():
    path = ex.dataset("ecommerce-events") / "clean_events.csv"
    return pd.read_csv(path, usecols=["timestamp", "visitorid", "event", "itemid"])


def test_real_funnel(nb, real_events):
    ev = nb.to_events(real_events)
    assert len(ev) == 2_755_641
    ft = nb.ordered_first_times(ev)
    assert ft.notna().sum().tolist() == [1_404_179, 32_934, 9_952]
    within = nb.conversion_within(ft, [1, 24, 168, 720])
    assert within.tolist() == pytest.approx([0.6283, 0.7962, 0.8862, 0.9528], abs=1e-4)
    weekly = nb.weekly_funnel(ft, WEEK, ev.event_time.max())
    assert len(weekly) == 21 and int(weekly.mature.sum()) == 19
    assert weekly.visitors.iloc[0] == 7_845 and weekly.visitors.iloc[-1] == 32_823
    assert weekly.buy_rate.iloc[-1] == pytest.approx(0.0049, abs=1e-4)
    mature = weekly[weekly.mature]
    assert mature.buy_rate.idxmin() == pd.Timestamp("2015-08-10")
