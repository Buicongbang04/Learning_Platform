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
    """Tạo MỘT server mới (tồn kho riêng, bản sao của BOOKS) tên "hieu-sach" với:

    Tool (dùng @server.tool(); docstring thành description, type hint thành inputSchema):
    - search_books(query: str, limit: int = 5) -> list[dict]: tìm theo một phần tên sách hoặc tác giả, không phân
      biệt hoa thường (dùng _norm); mỗi kết quả {"id", "title", "author", "price"} theo thứ tự trong BOOKS, tối đa
      `limit` (1..10, ràng buộc trong schema). query rỗng -> ToolError.
    - get_book(book_id: str) -> dict: {"id", "title", "author", "price", "stock", "category"}; mã không phân biệt hoa
      thường; mã không có -> ToolError có nhắc mã sai và gợi ý dùng search_books.
    - place_order(book_id: str, quantity: int) -> dict: quantity 1..10 (ràng buộc trong schema); mã không có hoặc
      không đủ hàng -> ToolError (nêu tồn kho hiện tại và số yêu cầu); thành công thì trừ tồn kho và trả
      {"order_id": "DH001", "book_id", "quantity", "total"} (mã đơn tăng dần DH001, DH002, ... trong một server).

    Resource:
    - "catalog://categories" (mime application/json): JSON {thể loại: số đầu sách}, khoá sắp xếp tăng dần.
    - "book://{book_id}" (template, mime application/json): JSON như get_book; mã không có -> ValueError.
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    build_server().run("stdio")
