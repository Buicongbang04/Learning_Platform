"""IdP OIDC giả chạy trong tiến trình test: discovery, JWKS, authorize/token (authorization code + PKCE S256).

Khoá RSA sinh mới mỗi lần; `token()` ký JWT bằng khoá thật của IdP, `forged()` ký bằng khoá khác nhưng cùng `kid`.
"""

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

CLIENT_ID = "quillo"
CLIENT_SECRET = "fake-idp-client-secret-0123456789"


def _new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeIdP:
    def __init__(self) -> None:
        self.key = _new_key()
        self.kid = "kid-1"
        self.other = _new_key()
        self.codes: dict[str, dict] = {}
        self.jwks_fetches = 0
        self._server: ThreadingHTTPServer | None = None

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def issuer(self) -> str:
        return f"{self.url}/realms/lawfirm"

    def jwks(self) -> dict:
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        return {"keys": [{**public, "kid": self.kid, "use": "sig", "alg": "RS256"}]}

    def claims(self, sub: str = "u-an", groups=("/legal",), **overrides) -> dict:
        now = int(time.time())
        base = {"iss": self.issuer, "sub": sub, "aud": [CLIENT_ID, "account"], "azp": CLIENT_ID, "iat": now,
                "exp": now + 300, "preferred_username": sub.removeprefix("u-"), "groups": list(groups)}
        base.update(overrides)
        return {k: v for k, v in base.items() if v is not None}

    def token(self, sub: str = "u-an", groups=("/legal",), *, key=None, kid=None, alg="RS256", **overrides) -> str:
        return jwt.encode(self.claims(sub, groups, **overrides), key or self.key, algorithm=alg,
                          headers={"kid": kid or self.kid})

    def forged(self, sub: str = "u-an", groups=("/legal",), **overrides) -> str:
        return self.token(sub, groups, key=self.other, **overrides)

    def rotate(self) -> None:
        self.key = _new_key()
        self.kid = f"kid-{secrets.token_hex(4)}"

    def authorize(self, location: str, sub: str = "u-an", groups=("/legal",)) -> dict:
        """Giả người dùng đăng nhập ở IdP: nhận URL authorize quillo chuyển tới, trả query của redirect về callback."""
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))
        assert query["response_type"] == "code" and query["client_id"] == CLIENT_ID
        assert query["code_challenge_method"] == "S256"
        code = secrets.token_urlsafe(16)
        self.codes[code] = {**query, "sub": sub, "groups": list(groups)}
        return {"code": code, "state": query["state"], "redirect_uri": query["redirect_uri"]}

    def _exchange(self, form: dict) -> tuple[int, dict]:
        grant = self.codes.pop(form.get("code", ""), None)
        if grant is None or form.get("grant_type") != "authorization_code":
            return 400, {"error": "invalid_grant"}
        if (form.get("client_id"), form.get("client_secret")) != (CLIENT_ID, CLIENT_SECRET):
            return 401, {"error": "invalid_client"}
        if form.get("redirect_uri") != grant["redirect_uri"]:
            return 400, {"error": "invalid_grant", "error_description": "redirect_uri"}
        digest = hashlib.sha256(form.get("code_verifier", "").encode()).digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != grant["code_challenge"]:
            return 400, {"error": "invalid_grant", "error_description": "PKCE"}
        id_token = self.token(grant["sub"], grant["groups"], aud=CLIENT_ID, nonce=grant["nonce"])
        return 200, {"access_token": self.token(grant["sub"], grant["groups"]), "id_token": id_token,
                     "token_type": "Bearer", "expires_in": 300}

    def __enter__(self) -> "FakeIdP":
        idp = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _reply(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                base = "/realms/lawfirm"
                if self.path == f"{base}/.well-known/openid-configuration":
                    self._reply(200, {"issuer": idp.issuer, "jwks_uri": f"{idp.issuer}/certs",
                                      "authorization_endpoint": f"{idp.issuer}/auth",
                                      "token_endpoint": f"{idp.issuer}/token"})
                elif self.path == f"{base}/certs":
                    idp.jwks_fetches += 1
                    self._reply(200, idp.jwks())
                else:
                    self._reply(404, {"error": "not found"})

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
                if self.path == "/realms/lawfirm/token":
                    self._reply(*idp._exchange(dict(urllib.parse.parse_qsl(body))))
                else:
                    self._reply(404, {"error": "not found"})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
