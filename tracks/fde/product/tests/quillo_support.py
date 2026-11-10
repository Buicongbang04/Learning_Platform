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
