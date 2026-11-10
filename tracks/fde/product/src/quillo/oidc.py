"""OIDC: kiểm access token (`Authorization: Bearer <JWT>`) bằng khoá công khai từ JWKS của IdP, và đăng nhập UI bằng
authorization code + PKCE (S256). Discovery và JWKS được cache; gặp `kid` lạ (IdP xoay khoá) thì tải lại JWKS, tối đa mỗi 10 s một lần."""

import base64
import hashlib
import secrets
import threading
import time
import urllib.parse
from dataclasses import dataclass

import httpx
import jwt

ALGORITHMS = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512")
LEEWAY_S = 60
DISCOVERY_TTL_S = 3600
JWKS_MIN_REFRESH_S = 10


class InvalidToken(Exception):
    pass


class ProviderError(Exception):
    """Không lấy được discovery/JWKS hay đổi code lấy token: IdP không với tới hoặc cấu hình sai."""


@dataclass(frozen=True)
class Identity:
    subject: str
    name: str
    groups: frozenset[str]


@dataclass(frozen=True)
class LoginRequest:
    url: str
    state: str
    nonce: str
    verifier: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Provider:
    def __init__(self, issuer: str, client_id: str, client_secret: str, groups_claim: str = "groups",
                 ca_file: str = "", timeout: float = 10.0) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self._secret = client_secret
        self.groups_claim = groups_claim
        self._http = httpx.Client(timeout=timeout, verify=ca_file or True)
        self._lock = threading.Lock()
        self._config: dict | None = None
        self._config_at = 0.0
        self._keys: dict[str, jwt.PyJWK] = {}
        self._keys_at = 0.0
        self._miss_refresh_at = float("-inf")

    def close(self) -> None:
        self._http.close()

    def _get(self, url: str) -> dict:
        try:
            response = self._http.get(url)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError(f"IdP: không lấy được {url}: {error!r}") from error

    def config(self) -> dict:
        with self._lock:
            if self._config is None or time.monotonic() - self._config_at > DISCOVERY_TTL_S:
                found = self._get(f"{self.issuer}/.well-known/openid-configuration")
                if str(found.get("issuer", "")).rstrip("/") != self.issuer:
                    raise ProviderError(f"IdP: discovery ghi issuer {found.get('issuer')!r}, cấu hình là {self.issuer!r}")
                self._config, self._config_at = found, time.monotonic()
            return self._config

    def _key(self, kid: str | None) -> jwt.PyJWK | None:
        jwks_uri = self.config()["jwks_uri"]
        with self._lock:
            now = time.monotonic()
            if kid not in self._keys and (not self._keys_at or now - self._miss_refresh_at >= JWKS_MIN_REFRESH_S):
                if self._keys_at:
                    self._miss_refresh_at = now
                keys = {}
                for item in self._get(jwks_uri).get("keys", []):
                    if item.get("use", "sig") != "sig" or not item.get("kid"):
                        continue
                    try:
                        keys[item["kid"]] = jwt.PyJWK(item)
                    except jwt.PyJWTError:
                        continue
                self._keys, self._keys_at = keys, time.monotonic()
            return self._keys.get(kid)

    def verify(self, token: str, *, nonce: str | None = None) -> dict:
        """Claims của JWT nếu chữ ký đúng khoá trong JWKS, `iss` khớp, còn hạn (lệch đồng hồ tối đa LEEWAY_S) và dành cho
        client này (`aud` chứa client id hoặc `azp` là client id). `nonce` đặt thì là ID token: `aud` phải chứa client id."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise InvalidToken(f"không phải JWT: {error}") from error
        algorithm = header.get("alg")
        if algorithm not in ALGORITHMS:
            raise InvalidToken(f"thuật toán ký {algorithm!r} không được nhận")
        key = self._key(header.get("kid"))
        if key is None:
            raise InvalidToken(f"không có khoá kid={header.get('kid')!r} trong JWKS của IdP")
        try:
            claims = jwt.decode(token, key.key, algorithms=[algorithm], issuer=self.issuer, leeway=LEEWAY_S,
                                options={"require": ["exp", "iss", "sub"], "verify_aud": False})
        except jwt.PyJWTError as error:
            raise InvalidToken(str(error)) from error
        audience = claims.get("aud")
        audience = [audience] if isinstance(audience, str) else list(audience or [])
        if nonce is not None:
            if self.client_id not in audience or not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
                raise InvalidToken("ID token không dành cho client này hoặc sai nonce")
        elif self.client_id not in audience and claims.get("azp") != self.client_id:
            raise InvalidToken(f"token dành cho {audience or claims.get('azp')}, không phải {self.client_id}")
        return claims

    def identity(self, claims: dict) -> Identity:
        groups = claims.get(self.groups_claim) or []
        if isinstance(groups, str):
            groups = [groups]
        names = frozenset(g.strip("/") for g in groups if isinstance(g, str) and g.strip("/"))
        return Identity(claims["sub"], claims.get("preferred_username") or claims["sub"], names)

    def login_request(self, redirect_uri: str) -> LoginRequest:
        state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        query = urllib.parse.urlencode({"response_type": "code", "client_id": self.client_id, "scope": "openid",
                                        "redirect_uri": redirect_uri, "state": state, "nonce": nonce,
                                        "code_challenge": challenge, "code_challenge_method": "S256"})
        return LoginRequest(f"{self.config()['authorization_endpoint']}?{query}", state, nonce, verifier)

    def exchange(self, code: str, redirect_uri: str, verifier: str, nonce: str) -> Identity:
        """Đổi authorization code lấy token (kèm code_verifier của PKCE), kiểm ID token, trả danh tính người dùng."""
        try:
            response = self._http.post(self.config()["token_endpoint"], data={
                "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
                "client_id": self.client_id, "client_secret": self._secret, "code_verifier": verifier})
        except httpx.HTTPError as error:
            raise ProviderError(f"IdP: không đổi được code lấy token: {error!r}") from error
        if response.status_code != 200:
            raise InvalidToken(f"IdP từ chối đổi code (HTTP {response.status_code}): {response.text[:200]}")
        return self.identity(self.verify(response.json().get("id_token", ""), nonce=nonce))
