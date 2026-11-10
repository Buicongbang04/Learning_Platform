import logging
import textwrap

import pytest
from fastapi.testclient import TestClient

from quillo import extensions
from quillo.app import create_app
from quillo_support import AUTH, make_settings, upload

REPORT = '''
from fastapi import Depends
from fastapi.responses import HTMLResponse


def register(app, ctx):
    @app.get("/ext/acme/report", response_class=HTMLResponse)
    def report(user=Depends(ctx.require_user)):
        rows = ctx.db_query("SELECT count(*) AS n FROM documents WHERE filename LIKE %s", ("legal/%",))
        return ctx.templates.get_template("acme_report.html").render(n=rows[0]["n"], user=user.name)

    @app.get("/ext/acme/ask")
    def ask(q: str, user=Depends(ctx.require_user)):
        return ctx.ask(q, 2, user)

    @app.get("/ext/acme/write")
    def write():
        return ctx.db_query("DELETE FROM documents", ())

    @app.get("/ext/acme/sneaky")
    def sneaky():
        return ctx.db_query("SET TRANSACTION READ WRITE; DELETE FROM documents", None)
'''


def write_extension(root, name: str, body: str, template: str | None = None):
    package = root / "acme"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("")
    (package / f"{name}.py").write_text(textwrap.dedent(body))
    if template is not None:
        (package / "templates").mkdir(exist_ok=True)
        (package / "templates" / "acme_report.html").write_text(template)
    return root


def test_extension_registers_route(database_url, fake_llm, tmp_path):
    root = write_extension(tmp_path / "ext", "report", REPORT, "<p>{{ n }} legal docs for {{ user }}</p>")
    settings = make_settings(database_url, fake_llm.url, extensions=("acme.report",), extensions_path=str(root))
    with TestClient(create_app(settings)) as client:
        upload(client, "nda.txt", "Governed by the law of New York. " * 3, folder="legal")
        assert client.get("/ext/acme/report").status_code == 401
        page = client.get("/ext/acme/report", headers=AUTH)
        assert page.status_code == 200 and page.text == "<p>1 legal docs for admin</p>"
        answer = client.get("/ext/acme/ask", params={"q": "Which law?"}, headers=AUTH).json()
        assert answer["citations"] and answer["citations"][0]["filename"] == "legal/nda.txt"
        with pytest.raises(Exception, match="read-only"):
            client.get("/ext/acme/write")
        with pytest.raises(Exception, match="read-write mode must be set before any query"):
            client.get("/ext/acme/sneaky")
        assert len(client.get("/api/documents", headers=AUTH).json()) == 1


@pytest.mark.parametrize("body, needle", [
    ("import not_installed_anywhere\n", "not_installed_anywhere"),
    ("raise RuntimeError('boom at import')\n", "boom at import"),
    ("x = 1\n", "register"),
])
def test_extension_import_error_fails_startup(database_url, fake_llm, tmp_path, caplog, body, needle):
    root = write_extension(tmp_path / "ext", "broken", body)
    settings = make_settings(database_url, fake_llm.url, extensions=("acme.broken",), extensions_path=str(root))
    with caplog.at_level(logging.ERROR, logger="quillo.extensions"):
        with pytest.raises(extensions.ExtensionError, match="acme.broken"):
            create_app(settings)
    assert any("acme.broken" in r.getMessage() and needle in str(getattr(r, "fields", {})) for r in caplog.records)


def test_missing_extension_module_fails_startup(database_url, fake_llm, tmp_path):
    settings = make_settings(database_url, fake_llm.url, extensions=("acme.nope",), extensions_path=str(tmp_path))
    with pytest.raises(extensions.ExtensionError, match="acme.nope"):
        create_app(settings)


def test_extensions_from_env(tmp_path):
    from quillo.config import Settings

    env = {"QUILLO_DATABASE_URL": "postgresql://x/y", "QUILLO_ADMIN_TOKEN": "t" * 20,
           "QUILLO_EXTENSIONS": "acme.report, acme.audit", "QUILLO_EXTENSIONS_PATH": str(tmp_path)}
    settings = Settings.from_env(env)
    assert settings.extensions == ("acme.report", "acme.audit")
    from quillo.config import ConfigError

    with pytest.raises(ConfigError, match="QUILLO_EXTENSIONS"):
        Settings.from_env({**env, "QUILLO_EXTENSIONS": "acme/../x"})
