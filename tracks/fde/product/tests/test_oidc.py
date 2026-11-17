import time
import urllib.parse

import jwt
import pytest
from fastapi.testclient import TestClient

from fake_idp import CLIENT_SECRET
from quillo.app import create_app
from quillo.config import ConfigError, Settings
from quillo_support import AUTH, TOKEN, bearer, it_change_request, sso_settings, upload

NY = "This agreement is governed by the law of the State of New York. " * 3


def me(client, token: str) -> int | dict:
    response = client.get("/api/me", headers=bearer(token))
    return response.json() if response.status_code == 200 else response.status_code


def test_oidc_rejects_bad_signature_and_expired(sso_client, idp):
    now = int(time.time())
    assert me(sso_client, idp.forged()) == 401
    assert me(sso_client, idp.token(exp=now - 61, iat=now - 400)) == 401
    assert me(sso_client, idp.token(iss="http://evil.example/realms/lawfirm")) == 401
    assert me(sso_client, idp.token(aud="other-app", azp="other-app")) == 401
    assert me(sso_client, idp.token(exp=None)) == 401
    assert me(sso_client, idp.token(kid="unknown-kid")) == 401
    unsigned = jwt.encode(idp.claims(), None, algorithm="none", headers={"kid": idp.kid})
    assert me(sso_client, unsigned) == 401
    hmac_signed = jwt.encode(idp.claims(), CLIENT_SECRET, algorithm="HS256", headers={"kid": idp.kid})
    assert me(sso_client, hmac_signed) == 401
    assert me(sso_client, "not.a.jwt") == 401
    assert sso_client.post("/api/ask", headers=bearer(idp.forged()), json={"question": "law?"}).status_code == 401
    within_leeway = me(sso_client, idp.token(exp=now - 30, iat=now - 330))
    assert isinstance(within_leeway, dict) and within_leeway["user"] == "an"


def test_oidc_accepts_valid_token_groups(sso_client, idp):
    assert me(sso_client, idp.token("u-chi", ["/legal", "/finance"])) == {
        "user": "chi", "groups": ["finance", "legal"], "admin": False}
    assert me(sso_client, idp.token(aud="account", azp="quillo"))["user"] == "an"
    upload(sso_client, "nda.txt", NY, folder="legal")
    upload(sso_client, "memo.txt", NY.replace("New York", "Texas"))
    asked = sso_client.post("/api/ask", headers=bearer(idp.token()), json={"question": "Which law governs?"})
    assert asked.status_code == 200, asked.text
    assert asked.json()["citations"] and all("New York" in c["text"] for c in asked.json()["citations"])
    listing = sso_client.get("/api/documents", headers=bearer(idp.token())).json()
    assert [d["filename"] for d in listing] == ["legal/nda.txt"]


def test_oidc_groups_claim_is_configurable(database_url, fake_llm, idp):
    settings = sso_settings(database_url, fake_llm.url, idp, oidc_groups_claim="roles")
    with TestClient(create_app(settings)) as client:
        assert me(client, idp.token(roles=["finance"]))["groups"] == ["finance"]


def test_static_token_still_admin(sso_client, idp, fake_llm):
    fake_llm.answer = "New York law, without passage markers."
    assert me(sso_client, TOKEN) == {"user": "admin", "groups": [], "admin": True}
    upload(sso_client, "memo.txt", NY)
    upload(sso_client, "nda.txt", NY + " Legal.", folder="legal")
    assert len(sso_client.get("/api/documents", headers=AUTH).json()) == 2
    asked = sso_client.post("/api/ask", headers=AUTH, json={"question": "Which law governs?", "top_k": 4})
    assert len({c["doc_id"] for c in asked.json()["citations"]}) == 2


def test_jwks_refetched_when_idp_rotates_key(sso_client, idp):
    assert me(sso_client, idp.token())["user"] == "an"
    fetches = idp.jwks_fetches
    idp.rotate()
    assert me(sso_client, idp.token())["user"] == "an"
    assert idp.jwks_fetches == fetches + 1
    for _ in range(3):
        assert me(sso_client, idp.token(kid="kid-nope")) == 401
    assert idp.jwks_fetches <= fetches + 2


def test_oidc_ui_login_with_pkce(sso_client, idp):
    upload(sso_client, "nda.txt", NY, folder="legal")
    upload(sso_client, "pay.txt", "Payment is due within thirty days.", folder="finance")
    assert "/oidc/login" in sso_client.get("/login").text
    start = sso_client.get("/oidc/login", follow_redirects=False)
    assert start.status_code == 303
    location = start.headers["location"]
    assert location.startswith(f"{idp.issuer}/auth?")
    assert "samesite=lax" in start.headers["set-cookie"].lower()
    callback = idp.authorize(location, "u-binh", ["/finance"])
    assert callback["redirect_uri"] == "http://testserver/oidc/callback"
    bad = sso_client.get("/oidc/callback", params={"code": callback["code"], "state": "x" * 20})
    assert bad.status_code == 400
    callback = idp.authorize(sso_client.get("/oidc/login", follow_redirects=False).headers["location"], "u-binh",
                             ["/finance"])
    done = sso_client.get("/oidc/callback", params={"code": callback["code"], "state": callback["state"]})
    assert done.status_code == 200, done.text
    page = sso_client.get("/")
    assert page.status_code == 200
    assert "finance/pay.txt" in page.text and "legal/nda.txt" not in page.text
    answer = sso_client.post("/ui/ask", data={"question": "Which law governs this agreement?"})
    assert "finance/pay.txt" in answer.text and "legal/nda.txt" not in answer.text


def test_oidc_secret_read_from_file(tmp_path, idp):
    secret = tmp_path / "client-secret"
    secret.write_text(CLIENT_SECRET + "\n")
    env = {"QUILLO_DATABASE_URL": "postgresql://x/y", "QUILLO_ADMIN_TOKEN": TOKEN, "QUILLO_OIDC_ISSUER": idp.issuer,
           "QUILLO_OIDC_CLIENT_ID": "quillo", "QUILLO_OIDC_CLIENT_SECRET_FILE": str(secret),
           "QUILLO_ACL": "legal:legal"}
    settings = Settings.from_env(env)
    assert settings.oidc_client_secret == CLIENT_SECRET and settings.oidc_groups_claim == "groups"
    assert CLIENT_SECRET not in repr(settings) and TOKEN not in repr(settings)
    with pytest.raises(ConfigError, match="QUILLO_OIDC_CLIENT_SECRET_FILE"):
        Settings.from_env({**env, "QUILLO_OIDC_CLIENT_SECRET_FILE": "", "QUILLO_OIDC_CLIENT_SECRET": CLIENT_SECRET})
    with pytest.raises(ConfigError, match="không đọc được"):
        Settings.from_env({**env, "QUILLO_OIDC_CLIENT_SECRET_FILE": str(tmp_path / "missing")})
    plain = Settings.from_env({k: v for k, v in env.items() if not k.startswith("QUILLO_OIDC")})
    assert plain.oidc_issuer == ""


def test_oidc_login_unavailable_without_oidc(client):
    assert client.get("/oidc/login", follow_redirects=False).status_code == 404
    assert "/oidc/login" not in client.get("/login").text


def test_authorize_url_has_pkce_and_nonce(sso_client, idp):
    location = sso_client.get("/oidc/login", follow_redirects=False).headers["location"]
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))
    assert query["scope"] == "openid"
    assert len(query["code_challenge"]) == 43 and len(query["state"]) >= 20 and len(query["nonce"]) >= 20


VM_SETUP = """set -eu
cd /home/fde && tar xf quillo.tar && rm quillo.tar && cd quillo-1.0.0
for i in images/pgvector.tar images/llama-cpp-server.tar images/quillo-api.tar; do docker load -q -i "$i" >/dev/null; done
sudo -n install -d -o 10001 -g 10001 -m 0750 inbox oidc
printf '%s' "$CLIENT_SECRET" | sudo -n install -o 10001 -g 10001 -m 0400 /dev/stdin oidc/client-secret
umask 077
cat > .env <<ENV
QUILLO_VERSION=1.0.0
QUILLO_ADMIN_TOKEN=$ADMIN_TOKEN
QUILLO_DB_PASSWORD=$(openssl rand -hex 16)
QUILLO_BIND=0.0.0.0
QUILLO_OIDC_ISSUER=http://10.0.2.102:8080/realms/lawfirm
QUILLO_OIDC_CLIENT_ID=quillo
QUILLO_ACL=legal:legal/,finance:finance/
ENV
docker compose -f compose.yaml -f compose.sso.yaml up -d --wait api >/dev/null
docker compose -f compose.yaml -f compose.sso.yaml up -d worker >/dev/null
"""


def test_keycloak_end_to_end(bundle):
    import shlex

    import fdekit
    import requests

    with fdekit.customer_site("lab-open", forwards=(18080,), extra_services=("keycloak",)) as site:
        site.vm.put(bundle, "/home/fde/quillo.tar")
        env = f"CLIENT_SECRET={shlex.quote(site.keycloak_client[1])} ADMIN_TOKEN={shlex.quote(TOKEN)}"
        setup = site.vm.ssh(f"{env} sh -c {shlex.quote(VM_SETUP)}", timeout=200)
        assert setup.returncode == 0, setup.stdout[-2000:] + setup.stderr[-2000:]
        api = f"http://127.0.0.1:{site.vm.port(18080)}"
        for name, folder, text in (("nda.txt", "legal", NY), ("invoice.txt", "finance", "Invoices are paid in 30 days.")):
            stored = requests.post(f"{api}/api/documents", headers=AUTH, data={"folder": folder}, timeout=120,
                                   files={"file": (name, text.encode(), "text/plain")})
            assert stored.status_code == 201, stored.text
        listing = requests.get(f"{api}/api/documents", headers=AUTH, timeout=30).json()
        legal_id = next(d["doc_id"] for d in listing if d["filename"] == "legal/nda.txt")

        def ask(user: str) -> dict:
            token = fdekit.keycloak_token(site, user, fdekit.KEYCLOAK_PASSWORDS[user])
            response = requests.post(f"{api}/api/ask", headers=bearer(token), timeout=120,
                                     json={"question": "Which law governs this agreement?"})
            assert response.status_code == 200, response.text
            return response.json()

        assert ask("an")["citations"] == []
        it_change_request(site)
        an = ask("an")
        assert an["citations"] and {c["doc_id"] for c in an["citations"]} == {legal_id}
        assert legal_id not in {c["doc_id"] for c in ask("binh")["citations"]}
