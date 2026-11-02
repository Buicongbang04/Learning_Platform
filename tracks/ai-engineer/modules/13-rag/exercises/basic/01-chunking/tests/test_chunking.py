import json
import math
import re
import unicodedata

import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Điều luật tự viết theo đúng định dạng Điều/Khoản/Điểm (không trích văn bản thật).
HEADER = "Điều 5. Xử phạt người điều khiển xe đạp điện vi phạm quy tắc giao thông"
K1 = (
    "1. Phạt tiền từ 100.000 đồng đến 200.000 đồng đối với người điều khiển xe không bật đèn chiếu sáng "
    "khi đi trên đường từ 19 giờ ngày hôm trước đến 05 giờ ngày hôm sau."
)
K2_LEAD = (
    "2. Phạt tiền từ 300.000 đồng đến 500.000 đồng đối với người điều khiển xe thực hiện một trong các "
    "hành vi vi phạm sau đây:"
)
K2_DIEM = [
    "a) Chở theo từ hai người trở lên trên xe, trừ trường hợp chở trẻ em dưới 12 tuổi;",
    "b) Buông cả hai tay hoặc dùng chân điều khiển xe;",
    "c) Vừa điều khiển xe vừa dùng điện thoại di động;",
    "d) Đi vào đường cao tốc hoặc khu vực có biển báo cấm xe thô sơ;",
    "đ) Không đội mũ bảo hiểm hoặc đội mũ bảo hiểm nhưng không cài quai đúng quy cách.",
]
K2 = "\n".join([K2_LEAD, *K2_DIEM])
K3 = (
    "3. Ngoài việc bị phạt tiền, người thực hiện hành vi quy định tại điểm d khoản 2 Điều này còn bị "
    "tạm giữ phương tiện đến 07 ngày."
)
ARTICLE = "\n".join([HEADER, K1, K2, K3])


@pytest.fixture(scope="module")
def ck():
    return ex.module("chunking.py")


# ---------- normalize ----------


def test_normalize_nfc_and_whitespace(ck):
    messy = "  Điều 5.\t Phạm   vi \r\n\r\n1.\u00a0 Khoản  một  \n   \n2. Khoản hai"
    assert ck.normalize(messy) == "Điều 5. Phạm vi\n1. Khoản một\n2. Khoản hai"
    nfd = unicodedata.normalize("NFD", "Luật Đất đai")
    out = ck.normalize(nfd)
    assert out == "Luật Đất đai"
    assert unicodedata.is_normalized("NFC", out)


# ---------- chunk_fixed ----------


def _rebuild(chunks: list[str], overlap: int) -> str:
    return chunks[0] + "".join(c[overlap:] for c in chunks[1:])


@pytest.mark.parametrize("size,overlap", [(50, 10), (40, 0), (37, 36), (100, 25)])
def test_chunk_fixed_rebuilds_original(ck, size, overlap):
    chunks = ck.chunk_fixed(ARTICLE, size, overlap)
    assert _rebuild(chunks, overlap) == ARTICLE
    assert all(len(c) == size for c in chunks[:-1])
    assert 0 < len(chunks[-1]) <= size
    # chunk sau bắt đầu bằng đúng `overlap` ký tự cuối của chunk trước
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt[:overlap] == prev[size - overlap :]


def test_chunk_fixed_does_not_normalize(ck):
    # chunk_fixed cắt đúng chuỗi được đưa vào, theo code point: NFD và khoảng trắng lộn xộn giữ nguyên từng ký tự
    raw = "  " + unicodedata.normalize("NFD", ARTICLE).replace("\n", " \r\n\t ") + "  "
    chunks = ck.chunk_fixed(raw, 60, 15)
    assert _rebuild(chunks, 15) == raw
    assert all(len(c) == 60 for c in chunks[:-1])
    assert len(chunks) == math.ceil((len(raw) - 15) / (60 - 15))


@pytest.mark.parametrize("length,size,overlap", [(1000, 100, 20), (1000, 500, 50), (100, 10, 0), (101, 10, 0), (95, 50, 10), (90, 50, 10)])
def test_chunk_fixed_count(ck, length, size, overlap):
    # không sinh chunk thừa nằm trọn trong chunk trước: số chunk đúng bằng ceil((L - O) / (S - O))
    text = "x" * length
    assert len(ck.chunk_fixed(text, size, overlap)) == math.ceil((length - overlap) / (size - overlap))


def test_chunk_fixed_short_and_empty_text(ck):
    assert ck.chunk_fixed("ngắn", 100, 10) == ["ngắn"]
    assert ck.chunk_fixed("x" * 100, 100, 10) == ["x" * 100]
    assert ck.chunk_fixed("", 100, 10) == []


@pytest.mark.parametrize("size,overlap", [(10, 10), (10, 15), (0, 0), (10, -1)])
def test_chunk_fixed_rejects_bad_params(ck, size, overlap):
    # kiểm tham số trước mọi việc khác; văn bản rỗng để cài đặt thiếu kiểm tra không bị lặp vô hạn (bước 0)
    with pytest.raises(ValueError):
        ck.chunk_fixed("", size, overlap)


# ---------- chunk_legal ----------


def test_chunk_legal_one_chunk_per_khoan(ck):
    chunks = ck.chunk_legal(ARTICLE, max_chars=2000)
    assert chunks == [f"{HEADER}\n{K1}", f"{HEADER}\n{K2}", f"{HEADER}\n{K3}"]
    assert all(c.startswith("Điều 5.") for c in chunks)


def test_chunk_legal_long_khoan_split_by_diem(ck):
    assert len(K1) <= 300 and len(K3) <= 300 < len(K2)
    chunks = ck.chunk_legal(ARTICLE, max_chars=300)
    # khoản 1, năm điểm a) b) c) d) đ) của khoản 2 (chữ "đ" cũng là một điểm), khoản 3
    assert len(chunks) == 7
    assert chunks[0] == f"{HEADER}\n{K1}"
    assert chunks[-1] == f"{HEADER}\n{K3}"
    for chunk, diem in zip(chunks[1:6], K2_DIEM):
        # mỗi điểm giữ tiêu đề Điều và phần dẫn của khoản (mức phạt nằm ở đó)
        assert chunk == f"{HEADER}\n{K2_LEAD}\n{diem}"


def test_chunk_legal_threshold_is_on_khoan_length(ck):
    # khoản dài đúng max_chars chưa phải tách; dài hơn 1 ký tự thì tách
    assert len(ck.chunk_legal(ARTICLE, max_chars=len(K2))) == 3
    assert len(ck.chunk_legal(ARTICLE, max_chars=len(K2) - 1)) == 7


def test_chunk_legal_long_khoan_without_diem_kept_whole(ck):
    chunks = ck.chunk_legal(ARTICLE, max_chars=50)
    assert chunks[0] == f"{HEADER}\n{K1}"
    assert chunks[-1] == f"{HEADER}\n{K3}"
    assert len(chunks) == 7


def test_chunk_legal_khoan_marker_must_start_line_and_be_followed_by_space(ck):
    article = "\n".join(
        [
            "Điều 9. Mức thu lệ phí cấp giấy phép",
            "1. Cấp mới giấy phép, mức thu là",
            "150.000 đồng một lần cấp.",
            "2. Cấp lại do mất hoặc hư hỏng, mức thu bằng 50% mức quy định tại khoản 1. Điều này áp dụng cả khi đổi.",
            "Trường hợp đổi giấy phép thì nộp như khoản 1. Lệ phí nộp một lần khi nhận hồ sơ.",
        ]
    )
    chunks = ck.chunk_legal(article, max_chars=1000)
    # "khoản 1. " giữa dòng không mở khoản mới: mẫu phải khớp ở đầu dòng
    assert len(chunks) == 2
    assert chunks[0] == "Điều 9. Mức thu lệ phí cấp giấy phép\n1. Cấp mới giấy phép, mức thu là\n150.000 đồng một lần cấp."
    assert chunks[1].endswith("\nTrường hợp đổi giấy phép thì nộp như khoản 1. Lệ phí nộp một lần khi nhận hồ sơ.")


def test_chunk_legal_article_without_khoan(ck):
    article = "Điều 1. Phạm vi điều chỉnh\nNghị định này quy định về xử phạt vi phạm hành chính đối với xe đạp điện."
    assert ck.chunk_legal(article, max_chars=1000) == [article]


def test_chunk_legal_text_before_first_khoan_is_its_own_chunk(ck):
    intro = "Người điều khiển xe đạp điện bị xử phạt như sau:"
    article = "\n".join([HEADER, intro, K1, K3])
    assert ck.chunk_legal(article, max_chars=1000) == [f"{HEADER}\n{intro}", f"{HEADER}\n{K1}", f"{HEADER}\n{K3}"]


def test_chunk_legal_normalizes_input(ck):
    expected = ck.chunk_legal(ARTICLE, max_chars=300)
    nfd = unicodedata.normalize("NFD", ARTICLE)
    assert ck.chunk_legal(nfd, max_chars=300) == expected
    messy = "\r\n".join("  " + line.replace(" ", "  ") + " \t" for line in ARTICLE.split("\n")) + "\n\n"
    assert ck.chunk_legal(messy, max_chars=300) == expected


def test_chunk_legal_on_real_zalo_articles(ck):
    """Dữ liệu thật: 3 000 điều luật đầu tiên của Zalo Legal. Tự skip nếu chưa tải."""
    root = ex.dataset("zalo-legal")
    articles = []
    with (root / "corpus.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            articles.append(f"{d['title']}\n{d['text']}")
            if len(articles) == 3000:
                break
    diem = re.compile(r"(?m)^[a-zđ]\)\s")
    total = 0
    for article in articles:
        title, *body = ck.normalize(article).split("\n")
        chunks = ck.chunk_legal(article, max_chars=1500)
        total += len(chunks)
        assert chunks and all(c.startswith(title + "\n") or c == title for c in chunks)
        # không mất dòng nào của điều luật
        kept = {line for c in chunks for line in c.split("\n")}
        assert set(body) <= kept
        # chunk còn dài quá max_chars chỉ khi phần thân (bỏ tiêu đề) không còn điểm nào để tách
        for c in chunks:
            if len(c) - len(title) - 1 > 1500:
                assert len(diem.findall(c.split("\n", 1)[1])) <= 1
    assert total > len(articles)
