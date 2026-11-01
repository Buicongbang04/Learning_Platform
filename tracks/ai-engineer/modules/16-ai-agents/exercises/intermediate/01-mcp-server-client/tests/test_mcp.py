import asyncio
import json
import sys

import pytest

from testkit import Exercise

ex = Exercise(__file__)

pytest.importorskip("mcp")
from mcp import Client, StdioServerParameters  # noqa: E402
from mcp.types import CallToolResult, TextContent, Tool  # noqa: E402


@pytest.fixture(scope="module")
def srv():
    return ex.module("server.py")


@pytest.fixture(scope="module")
def br():
    return ex.module("bridge.py")


def run(fn):
    return asyncio.run(fn())


def with_client(server, body):
    async def go():
        async with Client(server) as client:
            return await body(client)
    return run(go)


# ---------- server ----------


def test_tools_and_schemas(srv):
    async def body(client):
        return (await client.list_tools()).tools

    tools = {t.name: t for t in with_client(srv.build_server(), body)}
    assert set(tools) == {"search_books", "get_book", "place_order"}
    assert all(t.description for t in tools.values()), "docstring thành description cho model đọc"
    search = tools["search_books"].input_schema
    assert search["required"] == ["query"]
    assert search["properties"]["limit"]["default"] == 5
    assert (search["properties"]["limit"]["minimum"], search["properties"]["limit"]["maximum"]) == (1, 10)
    order = tools["place_order"].input_schema
    assert sorted(order["required"]) == ["book_id", "quantity"]
    assert (order["properties"]["quantity"]["minimum"], order["properties"]["quantity"]["maximum"]) == (1, 10)


def call(server, *calls):
    async def body(client):
        return [await client.call_tool(name, args) for name, args in calls]
    return with_client(server, body)


def payload(result):
    if result.structured_content is not None:
        data = result.structured_content
        return data["result"] if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


def test_search_books(srv):
    a, b, c = call(srv.build_server(), ("search_books", {"query": "NGUYỄN nhật ánh"}),
                   ("search_books", {"query": "a", "limit": 2}), ("search_books", {"query": "   "}))
    assert not a.is_error
    assert [x["id"] for x in payload(a)] == ["B04", "B05", "B06"]
    assert payload(a)[1] == {"id": "B05", "title": "Mắt biếc", "author": "Nguyễn Nhật Ánh", "price": 110000}
    assert len(payload(b)) == 2
    assert c.is_error, "query rỗng là lỗi tool"


def test_get_book(srv):
    ok, missing = call(srv.build_server(), ("get_book", {"book_id": "b05"}), ("get_book", {"book_id": "X9"}))
    assert payload(ok) == {"id": "B05", "title": "Mắt biếc", "author": "Nguyễn Nhật Ánh", "price": 110000,
                           "stock": 33, "category": "văn học"}
    assert missing.is_error
    text = missing.content[0].text
    assert "X9" in text and "search_books" in text, "thông điệp lỗi giúp model tự sửa"


def test_place_order_side_effect_and_limits(srv):
    server = srv.build_server()
    first, second, short, big, after = call(
        server, ("place_order", {"book_id": "b05", "quantity": 3}), ("place_order", {"book_id": "B24", "quantity": 2}),
        ("place_order", {"book_id": "B24", "quantity": 1}), ("place_order", {"book_id": "B05", "quantity": 11}),
        ("get_book", {"book_id": "B05"}))
    assert payload(first) == {"order_id": "DH001", "book_id": "B05", "quantity": 3, "total": 330000}
    assert payload(second)["order_id"] == "DH002"
    assert short.is_error and "0" in short.content[0].text, "hết hàng: nêu tồn kho hiện tại"
    assert big.is_error, "quantity > 10 bị schema chặn"
    assert payload(after)["stock"] == 30
    fresh = call(srv.build_server(), ("get_book", {"book_id": "B05"}))[0]
    assert payload(fresh)["stock"] == 33, "mỗi build_server có tồn kho riêng"
    assert srv.BOOKS["B05"]["stock"] == 33, "không sửa BOOKS gốc"


def test_resources(srv):
    async def body(client):
        listed = await client.list_resources()
        templates = await client.list_resource_templates()
        cats = await client.read_resource("catalog://categories")
        book = await client.read_resource("book://b20")
        return listed, templates, cats, book

    listed, templates, cats, book = with_client(srv.build_server(), body)
    assert [str(r.uri) for r in listed.resources] == ["catalog://categories"]
    assert [t.uri_template for t in templates.resource_templates] == ["book://{book_id}"]
    assert cats.contents[0].text == json.dumps({"khoa học": 1, "thiếu nhi": 2, "thơ": 1, "văn học": 6},
                                               ensure_ascii=False)
    assert json.loads(book.contents[0].text)["title"] == "Hoàng tử bé"


# ---------- bridge: chuyển đổi ----------


def test_to_openai_tool(br):
    tool = Tool(name="get_book", description=None, input_schema={
        "type": "object", "title": "get_bookArguments",
        "properties": {"book_id": {"type": "string", "title": "Book Id"}}, "required": ["book_id"]})
    spec = br.to_openai_tool(tool)
    assert spec == {"type": "function", "function": {"name": "get_book", "description": "", "parameters": {
        "type": "object", "properties": {"book_id": {"type": "string", "title": "Book Id"}}, "required": ["book_id"]}}}
    bare = br.to_openai_tool(Tool(name="ping", description="Kiểm tra.", input_schema={"type": "object"}))
    assert bare["function"]["parameters"] == {"type": "object", "properties": {}}


@pytest.mark.parametrize("result, ok, content", [
    (CallToolResult(content=[TextContent(type="text", text="Unknown tool: x")], is_error=True), False,
     "ERROR: Unknown tool: x"),
    (CallToolResult(content=[TextContent(type="text", text="5")], structured_content={"result": 5}), True, "5"),
    (CallToolResult(content=[TextContent(type="text", text="?")], structured_content={"result": [{"tên": "Mắt biếc"}]}),
     True, '[{"tên": "Mắt biếc"}]'),
    (CallToolResult(content=[TextContent(type="text", text="?")], structured_content={"id": "B05", "giá": 1}), True,
     '{"id": "B05", "giá": 1}'),
    (CallToolResult(content=[TextContent(type="text", text='{\n  "order_id": "DH001",\n  "tổng": 2\n}')]), True,
     '{"order_id": "DH001", "tổng": 2}'),
    (CallToolResult(content=[TextContent(type="text", text="dòng 1"), TextContent(type="text", text="dòng 2")]), True,
     "dòng 1\ndòng 2"),
])
def test_to_observation(br, result, ok, content):
    assert br.to_observation(result) == br.Observation(ok, content)


# ---------- bridge: MCPToolbox ----------


def test_toolbox_in_process(br, srv):
    with br.MCPToolbox(srv.build_server()) as tb:
        names = [s["function"]["name"] for s in tb.specs()]
        assert sorted(names) == ["get_book", "place_order", "search_books"]
        assert all(s["type"] == "function" and "title" not in s["function"]["parameters"] for s in tb.specs())
        ok = tb.call("get_book", {"book_id": "B05"})
        assert ok.ok and json.loads(ok.content)["price"] == 110000
        assert tb.call("get_book", '{"book_id": "B01"}').ok, "arguments dạng chuỗi JSON"
        assert tb.call("place_order", {"book_id": "B24", "quantity": 1}).ok
        assert json.loads(tb.call("get_book", {"book_id": "B24"}).content)["stock"] == 1, "cùng một phiên server"
        bad = tb.call("get_book", {"book_id": "Z1"})
        assert bad.ok is False and bad.content.startswith("ERROR: ") and "Z1" in bad.content
        assert tb.call("no_such_tool", {}).ok is False
        assert tb.call("get_book", "[1, 2]").ok is False
        assert json.loads(tb.read_resource("book://B11"))["author"] == "Stephen Hawking"
        assert "văn học" in tb.read_resource("catalog://categories")


def test_toolbox_works_with_agent_loop_protocol(br, srv):
    """MCPToolbox dùng thay ToolRegistry: specs() là list spec OpenAI, call() trả object có .ok, .content."""
    with br.MCPToolbox(srv.build_server()) as tb:
        specs = tb.specs()
        assert specs == tb.specs() and specs is not tb.specs(), "trả bản sao, gọi list_tools một lần lúc mở"
        obs = tb.call("search_books", {"query": "kiều"})
        assert hasattr(obs, "ok") and hasattr(obs, "content")
        assert json.loads(obs.content) == [{"id": "B08", "title": "Truyện Kiều", "author": "Nguyễn Du", "price": 64000}]


def test_toolbox_stdio_subprocess(br):
    params = StdioServerParameters(command=sys.executable, args=[str(ex.path("server.py"))])
    with br.MCPToolbox(params) as tb:
        assert sorted(s["function"]["name"] for s in tb.specs()) == ["get_book", "place_order", "search_books"]
        assert json.loads(tb.call("get_book", {"book_id": "B02"}).content)["title"] == "Tắt đèn"


def test_toolbox_protocol_error_becomes_observation(br):
    from mcp.server.mcpserver import MCPServer
    from mcp.shared.exceptions import MCPError

    server = MCPServer("loi-giao-thuc")

    @server.tool()
    def quota() -> str:
        """Luôn báo lỗi mức giao thức (JSON-RPC error), không phải lỗi tool."""
        raise MCPError(-32001, "hết hạn mức gọi")

    with br.MCPToolbox(server) as tb:
        obs = tb.call("quota", {})
    assert obs.ok is False and obs.content.startswith("ERROR: ") and "hết hạn mức" in obs.content
