"""Test bài PII. Mọi giá trị trong tệp là dữ liệu sinh, không phải PII thật."""

import random
import re

import pytest

from testkit import Exercise

ex = Exercise(__file__)



@pytest.fixture(scope="module")
def pii():
    return ex.module("pii.py")


def luhn_complete(prefix: str) -> str:
    for d in "0123456789":
        cand = prefix + d
        total = 0
        for i, ch in enumerate(reversed(cand)):
            v = int(ch) * (2 if i % 2 else 1)
            total += v - 9 if v > 9 else v
        if total % 10 == 0:
            return cand
    raise AssertionError


class Doc:
    def __init__(self):
        self.text = ""
        self.gold = []

    def add(self, s, kind=None):
        if kind:
            self.gold.append((len(self.text), len(self.text) + len(s), kind))
        self.text += s
        return self


def fake_cccd(rng, valid=True):
    codes = ["001", "079", "048", "031", "092"]
    head = rng.choice(codes) if valid else rng.choice(["003", "099", "150", "777"])
    return head + rng.choice("0123") + f"{rng.randint(0, 99):02d}" + f"{rng.randint(0, 999999):06d}"


def fake_phone(rng):
    num = rng.choice("35789") + "".join(rng.choice("0123456789") for _ in range(8))
    style = rng.randrange(4)
    if style == 0:
        return "0" + num
    if style == 1:
        return f"0{num[:3]} {num[3:6]} {num[6:]}"
    if style == 2:
        return f"0{num[:3]}.{num[3:6]}.{num[6:]}"
    return f"+84 {num[:3]} {num[3:6]} {num[6:]}"


def fake_card(rng, valid=True):
    body = "4" + "".join(rng.choice("0123456789") for _ in range(14))
    full = luhn_complete(body)
    if not valid:
        full = full[:-1] + str((int(full[-1]) + 1) % 10)
    return " ".join(full[i:i + 4] for i in range(0, 16, 4)) if rng.random() < 0.5 else full


def build_corpus(seed=0, n=120):
    rng = random.Random(seed)
    docs = []
    for _ in range(n):
        d = Doc()
        d.add(rng.choice(["Khách hàng ", "Anh Nam ", "Chị Thu ", "Người gửi "]))
        k = rng.randrange(6)
        if k == 0:
            d.add("có số CCCD ").add(fake_cccd(rng), "CCCD").add(", cần cập nhật hồ sơ.")
        elif k == 1:
            d.add("gọi lại số ").add(fake_phone(rng), "PHONE").add(" sau 17 giờ.")
        elif k == 2:
            u = rng.choice(["minh.anh", "thu_ha92", "nguyen.van.b"]) + str(rng.randint(1, 99))
            d.add("gửi email tới ").add(f"{u}@vidu.com.vn", "EMAIL").add(" để nhận hoá đơn.")
        elif k == 3:
            d.add("thanh toán bằng thẻ ").add(fake_card(rng), "CARD").add(" hôm qua.")
        elif k == 4:
            num = "".join(rng.choice("0123456789") for _ in range(rng.choice([10, 12, 13])))
            d.add(rng.choice(["chuyển khoản vào STK ", "số tài khoản: ", "tài khoản số "])).add(num, "BANK").add(" tại ngân hàng.")
        else:
            d.add("ở ").add(f"số {rng.randint(1, 300)} đường Lê Lợi, phường Bến Nghé, quận 1", "ADDRESS").add(".")
        neg = rng.randrange(5)
        if neg == 0:
            d.add(f" Mã hoá đơn {fake_cccd(rng, valid=False)} đã xuất.")
        elif neg == 1:
            d.add(f" Mã vận đơn {fake_card(rng, valid=False).replace(' ', '')}.")
        elif neg == 2:
            d.add(f" Số tiền {rng.randint(1, 999)}.{rng.randint(100, 999)}.000 đồng.")
        elif neg == 3:
            d.add(f" Mã đơn {rng.randint(10**12, 10**13 - 1)}0{rng.choice('35789')}{rng.randint(10**7, 10**8 - 1)}.")
        else:
            d.add(f" Ngày {rng.randint(1, 28)}/{rng.randint(1, 12)}/2026, phòng {rng.randint(100, 999)}.")
        docs.append(d)
    return docs


# ---------- từng loại ----------


def test_luhn(pii):
    assert pii.luhn_ok("4539578763621486")
    assert not pii.luhn_ok("4539578763621487")
    assert pii.luhn_ok("79927398713")
    assert not pii.luhn_ok("")


def test_cccd_structure(pii):
    assert pii.cccd_ok("079203001234")
    assert pii.cccd_ok("001099123456")
    assert not pii.cccd_ok("003203001234"), "003 không phải mã tỉnh"
    assert not pii.cccd_ok("079503001234"), "chữ số thứ 4 là mã thế kỷ và giới tính, 5 là năm sinh thế kỷ 22"
    assert not pii.cccd_ok("07920300123")
    assert not pii.cccd_ok("07920300123a")


def kinds(spans):
    return [(s.kind, s.text) for s in spans]


def test_phone_formats(pii):
    for phone in ["0912345678", "0912 345 678", "0912.345.678", "+84 912 345 678", "+84912345678", "038-123-4567"]:
        assert kinds(pii.find_pii(f"Gọi {phone} nhé.")) == [("PHONE", phone)], phone


def test_phone_not_inside_longer_numbers(pii):
    for text in ["Mã đơn 1234567890912345678.", "Mã 20912345678 lỗi", "Số tiền 1.091.234.567 đồng", "0212345678"]:
        assert [s for s in pii.find_pii(text) if s.kind == "PHONE"] == [], text


def test_email(pii):
    text = "Liên hệ nguyen.van-b+hr@cong-ty.com.vn hoặc admin@vidu.vn."
    assert kinds(pii.find_pii(text)) == [("EMAIL", "nguyen.van-b+hr@cong-ty.com.vn"), ("EMAIL", "admin@vidu.vn")]


def test_card_needs_luhn(pii):
    good = luhn_complete("453957876362148")
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert kinds(pii.find_pii(f"Thẻ {good} hết hạn")) == [("CARD", good)]
    spaced = " ".join(good[i:i + 4] for i in range(0, 16, 4))
    assert kinds(pii.find_pii(f"Thẻ {spaced}.")) == [("CARD", spaced)]
    assert pii.find_pii(f"Mã vận đơn {bad}") == []


def test_cccd_needs_valid_province(pii):
    assert kinds(pii.find_pii("CCCD 079203001234 của tôi")) == [("CCCD", "079203001234")]
    assert pii.find_pii("Hoá đơn 999203001234") == []


def test_bank_and_cmnd_need_keyword(pii):
    assert kinds(pii.find_pii("STK: 0071001234568 Vietcombank")) == [("BANK", "0071001234568")]
    assert kinds(pii.find_pii("Số tài khoản là 1903 4567 8901 23.")) == [("BANK", "1903 4567 8901 23")]
    assert kinds(pii.find_pii("CMND số 025123456 cấp năm 2010")) == [("CMND", "025123456")]
    assert pii.find_pii("Mã sản phẩm 0071001234568 còn hàng") == []
    assert pii.find_pii("Đơn 025123456 đã giao") == []


def test_address(pii):
    addr = "số 12/3 đường Nguyễn Trãi, phường Bến Thành, quận 1, TP. Hồ Chí Minh"
    spans = pii.find_pii(f"Giao tới {addr}. Cảm ơn")
    assert kinds(spans) == [("ADDRESS", addr)]


def test_spans_have_offsets(pii):
    text = "A: 0912345678, B: x@vidu.vn"
    for s in pii.find_pii(text):
        assert text[s.start:s.end] == s.text


# ---------- chồng lấn và che ----------


def test_resolve_overlaps(pii):
    S = pii.Span
    spans = [S(0, 10, "PHONE", "x" * 10), S(0, 13, "BANK", "x" * 13), S(20, 25, "EMAIL", "x" * 5),
             S(22, 30, "ADDRESS", "x" * 8), S(40, 52, "CCCD", "x" * 12), S(40, 52, "BANK", "x" * 12)]
    out = pii.resolve_overlaps(spans)
    assert [(s.start, s.end, s.kind) for s in out] == [(0, 13, "BANK"), (22, 30, "ADDRESS"), (40, 52, "BANK")]
    assert pii.resolve_overlaps([S(0, 5, "EMAIL", "aaaaa"), S(5, 9, "PHONE", "bbbb")]) == \
        [S(0, 5, "EMAIL", "aaaaa"), S(5, 9, "PHONE", "bbbb")], "chạm nhau ở biên không phải chồng lấn"


def test_keyword_beats_phone_shape(pii):
    spans = pii.find_pii("STK 0912345678 tại MB")
    assert kinds(spans) == [("BANK", "0912345678")]


def test_redact_multiple_spans(pii):
    text = "Gọi 0912345678 hoặc mail a.b@vidu.vn, CCCD 079203001234."
    assert pii.redact(text) == "Gọi [PHONE] hoặc mail [EMAIL], CCCD [CCCD]."


def test_redact_with_given_overlapping_spans(pii):
    S = pii.Span
    text = "0123456789abcdef"
    out = pii.redact(text, [S(2, 6, "PHONE", text[2:6]), S(4, 12, "BANK", text[4:12])])
    assert out == "0123[BANK]cdef"


# ---------- giả danh hoá ----------


def test_pseudonymize_roundtrip(pii):
    p = pii.Pseudonymizer(b"khoa-bi-mat-1")
    text = "Chị Thu (0912 345 678, thu@vidu.vn) gọi lại từ +84912345678, CCCD 079203001234."
    out = p.pseudonymize(text)
    for raw in ["0912 345 678", "thu@vidu.vn", "+84912345678", "079203001234"]:
        assert raw not in out
    tokens = re.findall(r"<[A-Z]+_[0-9a-f]{10}>", out)
    assert len(tokens) == 4
    assert tokens[0] == tokens[2], "cùng số điện thoại (khác cách viết) phải ra cùng token"
    assert p.restore(out).replace("+84912345678", "0912 345 678") == text.replace("+84912345678", "0912 345 678")
    assert p.restore("Không có token nào") == "Không có token nào"


def test_pseudonymize_is_keyed_and_stable(pii):
    a1, a2, b = pii.Pseudonymizer(b"khoa-A"), pii.Pseudonymizer(b"khoa-A"), pii.Pseudonymizer(b"khoa-B")
    text = "Email x.y@vidu.vn"
    assert a1.pseudonymize(text) == a2.pseudonymize(text), "cùng khoá, cùng giá trị, cùng token (join log được)"
    assert a1.pseudonymize(text) != b.pseudonymize(text), "khác khoá phải khác token: token không đoán được nếu thiếu khoá"
    with pytest.raises(ValueError):
        pii.Pseudonymizer(b"")


def test_restore_inside_llm_reply(pii):
    p = pii.Pseudonymizer(b"k")
    masked = p.pseudonymize("Khách 0987654321 hỏi về đơn hàng.")
    tok = re.search(r"<PHONE_[0-9a-f]{10}>", masked).group()
    reply = f"Tôi sẽ gọi lại cho số {tok} trong hôm nay. <PHONE_0000000000> là token lạ."
    assert p.restore(reply) == "Tôi sẽ gọi lại cho số 0987654321 trong hôm nay. <PHONE_0000000000> là token lạ."


# ---------- đo trên tập sinh ----------


def test_score_function(pii):
    S = pii.Span
    gold = [S(0, 5, "PHONE", ""), S(10, 15, "EMAIL", "")]
    pred = [S(0, 5, "PHONE", ""), S(10, 14, "EMAIL", ""), S(20, 25, "CARD", "")]
    sc = pii.score(pred, gold)
    assert sc["PHONE"]["precision"] == 1.0 and sc["PHONE"]["recall"] == 1.0
    assert sc["EMAIL"]["tp"] == 0 and sc["EMAIL"]["fp"] == 1 and sc["EMAIL"]["fn"] == 1
    assert sc["CARD"]["precision"] == 0.0 and sc["CARD"]["fp"] == 1


def test_precision_recall_on_synthetic_corpus(pii):
    pred, gold = [], []
    offset = 0
    for d in build_corpus(seed=0, n=150):
        gold += [pii.Span(a + offset, b + offset, k, "") for a, b, k in d.gold]
        pred += [pii.Span(s.start + offset, s.end + offset, s.kind, "") for s in pii.find_pii(d.text)]
        offset += len(d.text) + 1
    sc = pii.score(pred, gold)
    for kind in ["CCCD", "PHONE", "EMAIL", "CARD", "BANK", "ADDRESS"]:
        assert sc[kind]["recall"] == 1.0, (kind, sc[kind])
        assert sc[kind]["precision"] == 1.0, (kind, sc[kind])
