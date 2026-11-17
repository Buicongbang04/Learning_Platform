TOKEN = "test-admin-token-0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
DEFAULT_ACL = "legal:legal/,finance:finance/"


def make_settings(database_url: str, llm_url: str, embed_url: str | None = None, **overrides):
    from quillo.config import Settings

    return Settings(database_url=database_url, llm_url=llm_url, embed_url=embed_url or llm_url, admin_token=TOKEN,
                    **overrides)


def sso_settings(database_url: str, llm_url: str, idp, acl: str = DEFAULT_ACL, **overrides):
    from fake_idp import CLIENT_ID, CLIENT_SECRET

    return make_settings(database_url, llm_url, oidc_issuer=idp.issuer, oidc_client_id=CLIENT_ID,
                         oidc_client_secret=CLIENT_SECRET, acl=acl, **overrides)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def upload(client, name: str, text: str, headers=None, **fields):
    return client.post("/api/documents", headers=headers or AUTH,
                       files={"file": (name, text.encode(), "text/plain")}, data=fields)


def it_change_request(site) -> None:
    """Đóng vai IT khách áp yêu cầu thay đổi cho client `quillo` của Keycloak lab qua admin REST API."""
    import requests

    response = requests.post(f"{site.keycloak_host}/realms/master/protocol/openid-connect/token", timeout=30,
                             data={"grant_type": "password", "client_id": "admin-cli",
                                   "username": site.keycloak_admin[0], "password": site.keycloak_admin[1]})
    response.raise_for_status()
    admin = f"{site.keycloak_host}/admin/realms/lawfirm"
    auth = bearer(response.json()["access_token"])
    [client] = requests.get(f"{admin}/clients", params={"clientId": "quillo"}, headers=auth, timeout=30).json()
    change = {"name": "groups", "protocol": "openid-connect", "protocolMapper": "oidc-group-membership-mapper",
              "config": {"claim.name": "groups", "full.path": "true", "id.token.claim": "true",
                         "access.token.claim": "true", "userinfo.token.claim": "true"}}
    added = requests.post(f"{admin}/clients/{client['id']}/protocol-mappers/models", headers=auth, json=change,
                          timeout=30)
    assert added.status_code == 201, added.text
