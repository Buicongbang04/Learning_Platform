import base64
import hashlib
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import fdekit
from testkit import Exercise

ex = Exercise(__file__)
ISSUER = "http://10.0.2.102:8080/realms/lawfirm"
AUDIENCE = "quillo"
LEEWAY = 60


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def parts(token: str) -> tuple[dict, dict, str]:
    head, body, sig = token.split(".")
    return json.loads(unb64(head)), json.loads(unb64(body)), sig


def forge(header: dict, claims: dict, sig: str) -> str:
    return ".".join([b64(json.dumps(header).encode()), b64(json.dumps(claims).encode()), sig])


class Lab:
    def __init__(self, site: fdekit.Site) -> None:
        self.site = site
        self.upstream = f"{site.keycloak_host}/realms/{fdekit.KEYCLOAK_REALM}/protocol/openid-connect/certs"
        self.fetches = 0
        lab = self

        class Counting(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_GET(self) -> None:
                lab.fetches += 1
                upstream = requests.get(lab.upstream, timeout=30)
                self.send_response(upstream.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(upstream.content)))
                self.end_headers()
                self.wfile.write(upstream.content)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Counting)
        self.jwks_url = f"http://127.0.0.1:{self.server.server_address[1]}/realms/lawfirm/protocol/openid-connect/certs"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def token(self, user: str) -> str:
        return fdekit.keycloak_token(self.site, user, fdekit.KEYCLOAK_PASSWORDS[user])

    def other_client_token(self, user: str) -> str:
        response = requests.post(
            f"{self.site.keycloak_host}/realms/{fdekit.KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli", "username": user,
                  "password": fdekit.KEYCLOAK_PASSWORDS[user], "scope": "openid"}, timeout=30)
        response.raise_for_status()
        return response.json()["access_token"]

    def rotate_key(self) -> None:
        admin = requests.post(
            f"{self.site.keycloak_host}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli", "username": self.site.keycloak_admin[0],
                  "password": self.site.keycloak_admin[1]}, timeout=30)
        admin.raise_for_status()
        created = requests.post(
            f"{self.site.keycloak_host}/admin/realms/{fdekit.KEYCLOAK_REALM}/components",
            headers={"Authorization": f"Bearer {admin.json()['access_token']}"}, timeout=30,
            json={"name": f"rotated-{secrets.token_hex(3)}", "providerId": "rsa-generated",
                  "providerType": "org.keycloak.keys.KeyProvider",
                  "config": {"priority": ["500"], "keySize": ["2048"], "algorithm": ["RS256"], "active": ["true"],
                             "enabled": ["true"]}})
        assert created.status_code == 201, f"Test không xoay được khoá của realm: {created.text}"


@pytest.fixture(scope="module")
def lab():
    with fdekit.customer_site("lab-open", memory_mb=1024, extra_services=("keycloak",)) as site:
        lab = Lab(site)
        try:
            yield lab
        finally:
            lab.close()


@pytest.fixture(scope="module")
def mod():
    return ex.module("jwt_check.py")


def check(mod, lab, token, **kwargs):
    options = {"issuer": ISSUER, "audience": AUDIENCE, "jwks_url": lab.jwks_url} | kwargs
    return mod.check(token, **options)


def rejected(mod, lab, token, accepted: set[str], **kwargs) -> None:
    with pytest.raises(mod.TokenError) as caught:
        check(mod, lab, token, **kwargs)
    reason = getattr(caught.value, "reason", None)
    assert reason in accepted, f"Lý do từ chối phải thuộc {sorted(accepted)}, nhận {reason!r}"


def test_valid_tokens_return_claims(mod, lab):
    for user in ("an", "binh"):
        token = lab.token(user)
        claims = check(mod, lab, token)
        assert isinstance(claims, dict), "check() phải trả dict claim"
        assert claims.get("preferred_username") == user
        assert claims.get("sub") == parts(token)[1]["sub"]


def test_jwks_not_fetched_per_call(mod, lab):
    tokens = [lab.token(user) for user in ("an", "binh", "chi", "an", "binh")]
    check(mod, lab, tokens[0])
    before = lab.fetches
    for token in tokens:
        check(mod, lab, token)
    assert lab.fetches == before, f"5 lần kiểm token cùng kid mà tải JWKS {lab.fetches - before} lần; JWKS phải được cache"


def test_tampered_payload_rejected(mod, lab):
    header, claims, sig = parts(lab.token("binh"))
    for change in ({"preferred_username": "an"}, {"groups": ["legal"]}, {"exp": claims["exp"] + 86400}):
        rejected(mod, lab, forge(header, claims | change, sig), {"signature"})


def test_wrong_audience_rejected(mod, lab):
    rejected(mod, lab, lab.other_client_token("an"), {"audience"})
    rejected(mod, lab, lab.token("an"), {"audience"}, audience="contract-portal")


def test_issuer_must_match_exactly(mod, lab):
    token = lab.token("an")
    for issuer in (ISSUER + "/", ISSUER.replace("http://", "https://"), ISSUER.replace("lawfirm", "master"),
                   "http://127.0.0.1:8080/realms/lawfirm"):
        rejected(mod, lab, token, {"issuer"}, issuer=issuer)


def test_expiry_with_leeway(mod, lab):
    token = lab.token("an")
    exp = parts(token)[1]["exp"]
    assert check(mod, lab, token, now=exp + LEEWAY - 5)["preferred_username"] == "an"
    rejected(mod, lab, token, {"expired"}, now=exp + LEEWAY + 5)
    rejected(mod, lab, token, {"expired"}, now=exp + 86400)


def test_not_yet_valid(mod, lab):
    token = lab.token("an")
    iat = parts(token)[1]["iat"]
    assert check(mod, lab, token, now=iat - LEEWAY + 5)["preferred_username"] == "an"
    rejected(mod, lab, token, {"not_yet_valid"}, now=iat - LEEWAY - 5)


def test_algorithm_tricks_rejected(mod, lab):
    token = lab.token("an")
    header, claims, _ = parts(token)
    rejected(mod, lab, forge(header | {"alg": "none"}, claims, ""), {"algorithm"})
    jwks = requests.get(lab.upstream, timeout=30).json()
    key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
    pem = jwt.PyJWK(key).key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    head = b64(json.dumps(header | {"alg": "HS256"}).encode())
    body = b64(json.dumps(claims).encode())
    mac = hmac.new(pem, f"{head}.{body}".encode(), hashlib.sha256).digest()
    rejected(mod, lab, f"{head}.{body}.{b64(mac)}", {"algorithm"})


def test_foreign_keys_rejected(mod, lab):
    header, claims, _ = parts(lab.token("an"))
    real_kid = header["kid"]
    attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    unknown = jwt.encode(claims, attacker, algorithm="RS256", headers={"kid": f"k-{secrets.token_hex(8)}"})
    rejected(mod, lab, unknown, {"unknown_key"})
    reused = jwt.encode(claims, attacker, algorithm="RS256", headers={"kid": real_kid})
    rejected(mod, lab, reused, {"signature"})


def test_malformed_rejected(mod, lab):
    for token in ("", "abc", "a.b", "a.b.c", "!!!.???.***", lab.token("an") + ".x"):
        rejected(mod, lab, token, {"malformed"})


def test_key_rotation(mod, lab):
    old = lab.token("chi")
    assert check(mod, lab, old)["preferred_username"] == "chi"
    lab.rotate_key()
    new = lab.token("chi")
    assert parts(new)[0]["kid"] != parts(old)[0]["kid"], "Keycloak phải ký token mới bằng khoá mới"
    assert check(mod, lab, new)["preferred_username"] == "chi", "Token ký bằng khoá mới (sau khi IdP xoay khoá) bị từ chối"
    assert check(mod, lab, old)["preferred_username"] == "chi", "Token cũ còn hạn, khoá cũ vẫn trong JWKS: phải nhận"
