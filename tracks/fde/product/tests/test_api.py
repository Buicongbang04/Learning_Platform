import psycopg
from fastapi.testclient import TestClient

from fake_llm import FakeOpenAI
from quillo.app import create_app
from quillo_support import AUTH, TOKEN, make_settings

GOVERNING = "This agreement is governed by the law of the State of New York. " * 3
PAYMENT = "Payment is due within thirty days of the invoice date. Late payments accrue interest. " * 3


def upload(client, name: str, text: str, **fields):
    return client.post("/api/documents", headers=AUTH, files={"file": (name, text.encode(), "text/plain")},
                       data=fields)


def test_ask_returns_citations(client, fake_llm):
    governing = upload(client, "nda.txt", GOVERNING).json()
    upload(client, "invoice-terms.txt", PAYMENT)

    response = client.post("/api/ask", headers=AUTH, json={"question": "Which law governs this agreement?"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == fake_llm.answer
    assert body["model"] == "fake-llm"
    assert body["citations"], body
    first = body["citations"][0]
    assert set(first) == {"doc_id", "chunk", "text"}
    assert first["doc_id"] == governing["doc_id"]
    assert "New York" in first["text"]
    prompt = fake_llm.chats[-1]["messages"][-1]["content"]
    assert "New York" in prompt and "Which law governs this agreement?" in prompt


def test_ask_top_k_limits_context(client, fake_llm):
    for i in range(3):
        upload(client, f"doc{i}.txt", f"Clause {i}. " + GOVERNING)
    response = client.post("/api/ask", headers=AUTH, json={"question": "governing law", "top_k": 2})
    assert response.status_code == 200
    assert len(response.json()["citations"]) <= 2
    assert client.post("/api/ask", headers=AUTH, json={"question": "x", "top_k": 0}).status_code == 422


def test_ask_without_documents_does_not_call_llm(client, fake_llm):
    response = client.post("/api/ask", headers=AUTH, json={"question": "Which law governs this agreement?"})
    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert fake_llm.chats == []


def test_healthz_ok_reports_version(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.1.0", "checks": {"db": True, "llm": True, "embed": True}}


def test_healthz_503_when_llm_down(database_url, fake_llm):
    import testkit

    dead = f"http://127.0.0.1:{testkit.free_port()}"
    app = create_app(make_settings(database_url, dead, embed_url=fake_llm.url))
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"db": True, "llm": False, "embed": True}


def test_requires_token(client):
    files = {"file": ("a.txt", b"hello", "text/plain")}
    assert client.post("/api/documents", files=files).status_code == 401
    wrong = {"Authorization": "Bearer " + "x" * len(TOKEN)}
    assert client.post("/api/documents", headers=wrong, files=files).status_code == 401
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 401
    assert client.get("/api/documents").status_code == 401
    page = client.get("/", follow_redirects=False)
    assert page.status_code == 303 and page.headers["location"] == "/login"
    assert client.get("/healthz").status_code == 200


def test_login_then_ui(client):
    assert client.post("/login", data={"token": "wrong-token-wrong-token"}, follow_redirects=False).status_code == 401
    login = client.post("/login", data={"token": TOKEN}, follow_redirects=False)
    assert login.status_code == 303
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert TOKEN.lower() not in cookie
    page = client.get("/")
    assert page.status_code == 200
    assert '<script src="/static/htmx.min.js"' in page.text
    assert "https://" not in page.text
    assert client.get("/static/htmx.min.js").status_code == 200
    upload_part = client.post("/ui/documents", files={"file": ("nda.txt", GOVERNING.encode(), "text/plain")})
    assert upload_part.status_code == 200 and "nda.txt" in upload_part.text
    answer = client.post("/ui/ask", data={"question": "Which law governs this agreement?"})
    assert answer.status_code == 200 and "New York" in answer.text
    client.post("/logout")
    assert client.get("/", follow_redirects=False).status_code == 303


def test_ui_escapes_html(client, fake_llm):
    fake_llm.answer = "<script>alert(1)</script>"
    client.post("/login", data={"token": TOKEN})
    client.post("/ui/documents", files={"file": ("nda.txt", GOVERNING.encode(), "text/plain")})
    answer = client.post("/ui/ask", data={"question": "Which law governs this agreement?"})
    assert "<script>alert(1)</script>" not in answer.text
    assert "&lt;script&gt;" in answer.text


def test_upload_size_limit(database_url, fake_llm):
    app = create_app(make_settings(database_url, fake_llm.url, max_upload_mb=1))
    with TestClient(app) as client:
        big = upload(client, "big.txt", "a" * (1024 * 1024 + 10))
        assert big.status_code == 413
        assert upload(client, "small.txt", "fine " * 100).status_code == 201


def test_upload_sanitizes_filename_and_type(client, database_url):
    response = upload(client, "../../etc/pass wd;rm -rf.txt", GOVERNING)
    assert response.status_code == 201, response.text
    name = response.json()["filename"]
    assert "/" not in name and ".." not in name and ";" not in name
    assert name.endswith(".txt")
    assert upload(client, "tool.exe", "MZ").status_code == 415
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT filename FROM documents").fetchone()[0] == name


def test_reupload_same_content_replaces_document(client, database_url):
    first = upload(client, "a.txt", GOVERNING).json()
    second = upload(client, "renamed.txt", GOVERNING).json()
    assert first["doc_id"] == second["doc_id"]
    listing = client.get("/api/documents", headers=AUTH).json()
    assert [d["filename"] for d in listing] == ["renamed.txt"]


def test_tags_in_v1_1(client):
    response = upload(client, "nda.txt", GOVERNING, tags="nda, New York ,")
    assert response.status_code == 201
    assert response.json()["tags"] == ["nda", "New York"]
    assert client.get("/api/documents", headers=AUTH).json()[0]["tags"] == ["nda", "New York"]


def test_v1_0_has_no_tags(database_url, fake_llm):
    app = create_app(make_settings(database_url, fake_llm.url, version="1.0.0"))
    with TestClient(app) as client:
        assert client.get("/healthz").json()["version"] == "1.0.0"
        response = upload(client, "nda.txt", GOVERNING, tags="nda")
        assert response.status_code == 201
        assert "tags" not in response.json()
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT max(version) FROM schema_migrations").fetchone()[0] == 1
        columns = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'")}
        assert "tags" not in columns
