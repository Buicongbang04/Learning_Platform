"""Môi trường hiệu sách cho agent: dữ liệu tự tạo, 5 tool, 24 task có đáp án tính từ dữ liệu."""

import ast
import operator
import unicodedata
from typing import Literal

BOOKS = [
    ("B01", "Dế Mèn phiêu lưu ký", "Tô Hoài", 68000, 42, "thiếu nhi", 1941),
    ("B02", "Tắt đèn", "Ngô Tất Tố", 55000, 18, "văn học", 1939),
    ("B03", "Số đỏ", "Vũ Trọng Phụng", 72000, 25, "văn học", 1936),
    ("B04", "Cho tôi xin một vé đi tuổi thơ", "Nguyễn Nhật Ánh", 85000, 60, "văn học", 2008),
    ("B05", "Mắt biếc", "Nguyễn Nhật Ánh", 110000, 33, "văn học", 1990),
    ("B06", "Tôi thấy hoa vàng trên cỏ xanh", "Nguyễn Nhật Ánh", 125000, 27, "văn học", 2010),
    ("B07", "Nỗi buồn chiến tranh", "Bảo Ninh", 98000, 12, "văn học", 1990),
    ("B08", "Truyện Kiều", "Nguyễn Du", 64000, 50, "thơ", 1820),
    ("B09", "Đất rừng phương Nam", "Đoàn Giỏi", 79000, 21, "thiếu nhi", 1957),
    ("B10", "Vang bóng một thời", "Nguyễn Tuân", 70000, 9, "văn học", 1940),
    ("B11", "Lược sử thời gian", "Stephen Hawking", 115000, 30, "khoa học", 1988),
    ("B12", "Sapiens: Lược sử loài người", "Yuval Noah Harari", 189000, 45, "lịch sử", 2011),
    ("B13", "Nhà giả kim", "Paulo Coelho", 79000, 80, "văn học", 1988),
    ("B14", "Đắc nhân tâm", "Dale Carnegie", 86000, 120, "kỹ năng", 1936),
    ("B15", "Tuổi trẻ đáng giá bao nhiêu", "Rosie Nguyễn", 80000, 64, "kỹ năng", 2016),
    ("B16", "Cà phê cùng Tony", "Tony Buổi Sáng", 90000, 38, "kỹ năng", 2014),
    ("B17", "Python cho người mới bắt đầu", "Lê Minh Hoàng", 150000, 15, "tin học", 2021),
    ("B18", "Học máy cơ bản", "Vũ Hữu Tiệp", 220000, 11, "tin học", 2018),
    ("B19", "Đi tìm lẽ sống", "Viktor Frankl", 82000, 40, "kỹ năng", 1946),
    ("B20", "Hoàng tử bé", "Antoine de Saint-Exupéry", 59000, 70, "thiếu nhi", 1943),
    ("B21", "Chiến binh cầu vồng", "Andrea Hirata", 108000, 22, "văn học", 2005),
    ("B22", "Việt Nam sử lược", "Trần Trọng Kim", 165000, 14, "lịch sử", 1920),
    ("B23", "Bố già", "Mario Puzo", 135000, 26, "văn học", 1969),
    ("B24", "Thép đã tôi thế đấy", "Nikolai Ostrovsky", 120000, 8, "văn học", 1934),
]
BOOK = {b[0]: dict(zip(["id", "title", "author", "price", "stock", "category", "year"], b)) for b in BOOKS}

ORDERS = {
    "DH01": {"customer": "Lan", "items": [("B05", 2), ("B13", 1)], "status": "đã giao"},
    "DH02": {"customer": "Minh", "items": [("B12", 1), ("B11", 1), ("B14", 3)], "status": "đang giao"},
    "DH03": {"customer": "Hà", "items": [("B01", 4)], "status": "chờ xác nhận"},
    "DH04": {"customer": "Tuấn", "items": [("B18", 1), ("B17", 2)], "status": "đã huỷ"},
}
RATES = {"USD": 25400, "EUR": 27500, "JPY": 170}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def search_books(query: str) -> list[dict]:
    """Tìm sách theo một phần tên sách hoặc tên tác giả (không phân biệt hoa thường). Trả tối đa 5 cuốn: mã, tên, tác giả, giá (đồng).

    Args:
        query: một phần tên sách hoặc tên tác giả, ví dụ "Mắt biếc" hay "Nguyễn Nhật Ánh"
    """
    q = _norm(query).strip()
    if not q:
        raise ValueError("query rỗng")
    hits = [b for b in BOOK.values() if q in _norm(b["title"]) or q in _norm(b["author"])]
    return [{k: b[k] for k in ("id", "title", "author", "price")} for b in hits[:5]]


def get_book(book_id: str) -> dict:
    """Thông tin đầy đủ của một cuốn sách theo mã: tên, tác giả, giá (đồng), số lượng tồn kho, thể loại, năm xuất bản.

    Args:
        book_id: mã sách, ví dụ "B05"
    """
    key = book_id.strip().upper()
    if key not in BOOK:
        raise ValueError(f"không có sách mã {book_id!r}; dùng search_books để tìm mã")
    return dict(BOOK[key])


def get_order(order_id: str) -> dict:
    """Thông tin một đơn hàng: khách hàng, trạng thái, danh sách (mã sách, số lượng). Không có giá: tra giá bằng get_book.

    Args:
        order_id: mã đơn, ví dụ "DH01"
    """
    key = order_id.strip().upper()
    if key not in ORDERS:
        raise ValueError(f"không có đơn {order_id!r}")
    o = ORDERS[key]
    return {"id": key, "customer": o["customer"], "status": o["status"],
            "items": [{"book_id": b, "quantity": q} for b, q in o["items"]]}


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Pow: operator.pow, ast.Mod: operator.mod}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and abs(_eval(node.right)) > 10:
            raise ValueError("số mũ quá lớn")
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("chỉ nhận số và + - * / % ** ( )")


def calculator(expression: str) -> float | int:
    """Tính một biểu thức số học (chỉ số và + - * / % ** ngoặc), ví dụ "3 * 85000 + 110000".

    Args:
        expression: biểu thức, không có đơn vị hay dấu phân cách nghìn
    """
    value = _eval(ast.parse(expression.replace(",", ""), mode="eval"))
    return round(value, 4) if isinstance(value, float) else value


def exchange_rate(currency: Literal["USD", "EUR", "JPY"]) -> dict:
    """Tỷ giá bán ra hôm nay: số đồng cho 1 đơn vị ngoại tệ.

    Args:
        currency: mã ngoại tệ
    """
    return {"currency": currency, "vnd_per_unit": RATES[currency]}


TOOLS = [search_books, get_book, get_order, calculator, exchange_rate]

P = {b: BOOK[b]["price"] for b in BOOK}
S = {b: BOOK[b]["stock"] for b in BOOK}


def order_total(oid):
    return sum(P[b] * q for b, q in ORDERS[oid]["items"])


TASKS = [
    ("t01", "tra-1", "Cuốn 'Mắt biếc' giá bao nhiêu tiền?", [P["B05"]]),
    ("t02", "tra-1", "Ai là tác giả của 'Vang bóng một thời'?", ["Nguyễn Tuân"]),
    ("t03", "tra-1", "Kho còn bao nhiêu cuốn 'Thép đã tôi thế đấy'?", [S["B24"]]),
    ("t04", "tra-1", "Cuốn 'Lược sử thời gian' xuất bản năm nào?", [BOOK["B11"]["year"]]),
    ("t05", "tra-1", "Đơn hàng DH02 đang ở trạng thái nào?", ["đang giao"]),
    ("t06", "tra-1", "Sách 'Học máy cơ bản' thuộc thể loại gì?", ["tin học"]),
    ("t07", "tinh", "Mua 3 cuốn 'Tắt đèn' hết bao nhiêu tiền?", [3 * P["B02"]]),
    ("t08", "tinh", "Cuốn 'Sapiens' giảm giá 20% thì còn bao nhiêu tiền?", [P["B12"] * 0.8]),
    ("t09", "tinh", "Mua 2 cuốn 'Nhà giả kim' và 1 cuốn 'Hoàng tử bé' hết bao nhiêu?", [2 * P["B13"] + P["B20"]]),
    ("t10", "tinh", "Tổng tồn kho của ba cuốn sách của Nguyễn Nhật Ánh là bao nhiêu cuốn?", [S["B04"] + S["B05"] + S["B06"]]),
    ("t11", "tinh", "Cuốn 'Bố già' đắt hơn cuốn 'Số đỏ' bao nhiêu tiền?", [P["B23"] - P["B03"]]),
    ("t12", "tinh", "Giá trị tồn kho (giá nhân số lượng tồn) của 'Đắc nhân tâm' là bao nhiêu?", [P["B14"] * S["B14"]]),
    ("t13", "don", "Tổng tiền đơn hàng DH01 là bao nhiêu?", [order_total("DH01")]),
    ("t14", "don", "Tổng tiền đơn hàng DH02 là bao nhiêu?", [order_total("DH02")]),
    ("t15", "don", "Đơn hàng DH03 của ai và tổng tiền bao nhiêu?", ["Hà", order_total("DH03")]),
    ("t16", "don", "Đơn DH04 có bao nhiêu cuốn sách tất cả?", [3]),
    ("t17", "ngoai-te", "Cuốn 'Bố già' giá bao nhiêu đô la Mỹ (làm tròn 2 chữ số)?", [round(P["B23"] / RATES["USD"], 2)]),
    ("t18", "ngoai-te", "Với 20 euro thì đổi được bao nhiêu đồng?", [20 * RATES["EUR"]]),
    ("t19", "so-sanh", "Trong hai cuốn 'Truyện Kiều' và 'Đất rừng phương Nam', cuốn nào rẻ hơn?", ["Truyện Kiều"]),
    ("t20", "so-sanh", "Cuốn nào của Nguyễn Nhật Ánh đắt nhất trong kho?", ["Tôi thấy hoa vàng trên cỏ xanh"]),
    ("t21", "so-sanh", "Mã sách của 'Đi tìm lẽ sống' là gì?", ["B19"]),
    ("t22", "khong-co", "Cửa hàng có cuốn 'Chiến tranh và hoà bình' không?", ["không"]),
    ("t23", "khong-tool", "Thủ đô của Pháp là thành phố nào?", ["Paris"]),
    ("t24", "khong-tool", "1 giờ có bao nhiêu phút?", [60]),
]
