TOKEN = "test-admin-token-0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def make_settings(database_url: str, llm_url: str, embed_url: str | None = None, **overrides):
    from quillo.config import Settings

    return Settings(database_url=database_url, llm_url=llm_url, embed_url=embed_url or llm_url, admin_token=TOKEN,
                    **overrides)
