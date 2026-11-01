"""MCP server của hiệu sách: tool tra cứu, tool đặt hàng (có tác dụng phụ), resource danh mục và từng cuốn sách."""

import copy
import json
import unicodedata
from typing import Annotated

from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

BOOKS = {
    "B01": {"title": "Dế Mèn phiêu lưu ký", "author": "Tô Hoài", "price": 68000, "stock": 42, "category": "thiếu nhi"},
    "B02": {"title": "Tắt đèn", "author": "Ngô Tất Tố", "price": 55000, "stock": 18, "category": "văn học"},
    "B03": {"title": "Số đỏ", "author": "Vũ Trọng Phụng", "price": 72000, "stock": 25, "category": "văn học"},
    "B04": {"title": "Cho tôi xin một vé đi tuổi thơ", "author": "Nguyễn Nhật Ánh", "price": 85000, "stock": 60,
            "category": "văn học"},
    "B05": {"title": "Mắt biếc", "author": "Nguyễn Nhật Ánh", "price": 110000, "stock": 33, "category": "văn học"},
    "B06": {"title": "Tôi thấy hoa vàng trên cỏ xanh", "author": "Nguyễn Nhật Ánh", "price": 125000, "stock": 27,
            "category": "văn học"},
    "B08": {"title": "Truyện Kiều", "author": "Nguyễn Du", "price": 64000, "stock": 50, "category": "thơ"},
    "B11": {"title": "Lược sử thời gian", "author": "Stephen Hawking", "price": 115000, "stock": 30,
            "category": "khoa học"},
    "B20": {"title": "Hoàng tử bé", "author": "Antoine de Saint-Exupéry", "price": 59000, "stock": 70,
            "category": "thiếu nhi"},
    "B24": {"title": "Thép đã tôi thế đấy", "author": "Nikolai Ostrovsky", "price": 120000, "stock": 2,
            "category": "văn học"},
}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def build_server() -> MCPServer:
    books = copy.deepcopy(BOOKS)
    orders: list[dict] = []
    server = MCPServer("hieu-sach", instructions="Tra cứu và đặt sách của hiệu sách. Giá tính bằng đồng.")

    @server.tool()
    def search_books(query: str, limit: Annotated[int, Field(ge=1, le=10)] = 5) -> list[dict]:
        """Tìm sách theo một phần tên sách hoặc tên tác giả, không phân biệt hoa thường. Trả mã, tên, tác giả, giá."""
        q = _norm(query).strip()
        if not q:
            raise ToolError("query rỗng: nhập một phần tên sách hoặc tác giả")
        hits = [{"id": bid, "title": b["title"], "author": b["author"], "price": b["price"]}
                for bid, b in books.items() if q in _norm(b["title"]) or q in _norm(b["author"])]
        return hits[:limit]

    @server.tool()
    def get_book(book_id: str) -> dict:
        """Thông tin đầy đủ của một cuốn sách theo mã (vd. "B05"): tên, tác giả, giá, tồn kho, thể loại."""
        key = book_id.strip().upper()
        if key not in books:
            raise ToolError(f"không có sách mã {book_id!r}; dùng search_books để tìm mã")
        return {"id": key, **books[key]}

    @server.tool()
    def place_order(book_id: str, quantity: Annotated[int, Field(ge=1, le=10)]) -> dict:
        """Đặt mua sách: trừ tồn kho, trả mã đơn và tổng tiền. Thao tác có tác dụng phụ, chỉ gọi khi người dùng yêu cầu."""
        key = book_id.strip().upper()
        if key not in books:
            raise ToolError(f"không có sách mã {book_id!r}")
        if books[key]["stock"] < quantity:
            raise ToolError(f"không đủ hàng: {key} còn {books[key]['stock']} cuốn, yêu cầu {quantity}")
        books[key]["stock"] -= quantity
        order = {"order_id": f"DH{len(orders) + 1:03d}", "book_id": key, "quantity": quantity,
                 "total": quantity * books[key]["price"]}
        orders.append(order)
        return order

    @server.resource("catalog://categories", mime_type="application/json")
    def categories() -> str:
        """Số đầu sách theo thể loại."""
        counts: dict[str, int] = {}
        for b in books.values():
            counts[b["category"]] = counts.get(b["category"], 0) + 1
        return json.dumps(dict(sorted(counts.items())), ensure_ascii=False)

    @server.resource("book://{book_id}", mime_type="application/json")
    def book(book_id: str) -> str:
        """Bản ghi JSON của một cuốn sách."""
        key = book_id.upper()
        if key not in books:
            raise ValueError(f"không có sách mã {book_id!r}")
        return json.dumps({"id": key, **books[key]}, ensure_ascii=False)

    return server


if __name__ == "__main__":
    build_server().run("stdio")
