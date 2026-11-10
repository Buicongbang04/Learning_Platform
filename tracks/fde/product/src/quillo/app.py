import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psycopg
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from quillo import acl, auth, db, extensions, ingest, metrics, oidc, rag
from quillo.auth import User
from quillo.config import ConfigError, Settings, setup_logging
from quillo.llm import ModelServer

log = logging.getLogger("quillo.api")
HERE = Path(__file__).resolve().parent
UPLOAD_PATHS = {"/api/documents", "/ui/documents"}
MULTIPART_OVERHEAD = 64 * 1024
MAX_FORM_BYTES = 64 * 1024
MAX_TAGS = 20
MAX_TAG_LENGTH = 64
HEALTH_TIMEOUT_S = 1.5
STARTUP_DB_WAIT_S = 60
OIDC_COOKIE = "quillo_oidc"
OIDC_COOKIE_MAX_AGE = 600
ASK_ROUTES = {"/api/ask", "/ui/ask"}
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
templates = Jinja2Templates(directory=HERE / "templates")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)


class BodyLimit:
    """Từ chối POST quá giới hạn (413) hoặc không rõ độ dài (411) trước khi parse body, kể cả trước khi kiểm token:
    upload tối đa QUILLO_MAX_UPLOAD_MB và bắt buộc Content-Length; POST khác tối đa 64 KB, không có Content-Length lẫn
    Transfer-Encoding thì coi như body rỗng."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            upload = scope["path"] in UPLOAD_PATHS
            limit = self.max_bytes + MULTIPART_OVERHEAD if upload else MAX_FORM_BYTES
            headers = dict(scope["headers"])
            length = headers.get(b"content-length", b"")
            if not length and not upload and b"transfer-encoding" not in headers:
                length = b"0"
            if not (length.isascii() and length.isdigit()):
                await JSONResponse({"detail": "Cần Content-Length"}, status_code=411)(scope, receive, send)
                return
            if int(length) > limit:
                await JSONResponse({"detail": "Body quá lớn"}, status_code=413)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _wait_and_migrate(settings: Settings) -> int:
    deadline = time.monotonic() + STARTUP_DB_WAIT_S
    while True:
        try:
            with db.connect(settings.database_url) as conn:
                db.migrate(conn, settings.migrations_dir, db.schema_for(settings.version))
                return db.current_schema(conn)
        except psycopg.OperationalError as error:
            if time.monotonic() > deadline:
                raise
            log.warning("chờ database", extra={"fields": {"error": str(error).strip()}})
            time.sleep(2)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        setup_logging()
        settings = Settings.from_env()
    tags_enabled = db.schema_for(settings.version) >= 2
    max_bytes = settings.max_upload_mb * 1024 * 1024
    try:
        rules = acl.parse(settings.acl)
    except ValueError as error:
        raise ConfigError(str(error)) from error

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        schema = _wait_and_migrate(settings)
        log.info("quillo sẵn sàng", extra={"fields": {"version": settings.version, "schema": schema}})
        yield
        app.state.llm.close()
        app.state.embed.close()
        if app.state.oidc is not None:
            app.state.oidc.close()

    app = FastAPI(title="Quillo", version=settings.version, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.llm = ModelServer(settings.llm_url, settings.http_timeout_s)
    app.state.embed = ModelServer(settings.embed_url, settings.http_timeout_s)
    app.state.oidc = None
    if settings.oidc_enabled:
        app.state.oidc = oidc.Provider(settings.oidc_issuer, settings.oidc_client_id, settings.oidc_client_secret,
                                       settings.oidc_groups_claim, settings.oidc_ca_file)
    app.add_middleware(BodyLimit, max_bytes=max_bytes)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    def counts() -> tuple[int, int] | None:
        try:
            with db.connect(settings.database_url, timeout=2) as conn:
                conn.execute("SET statement_timeout = 1500")
                return db.counts(conn)
        except psycopg.Error:
            return None

    app.state.metrics = stats = metrics.Metrics(counts, {
        "llm": lambda: app.state.llm.healthy(HEALTH_TIMEOUT_S),
        "embed": lambda: app.state.embed.healthy(HEALTH_TIMEOUT_S)})

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        elapsed = time.perf_counter() - started
        route = getattr(request.scope.get("route"), "path", None)
        stats.observe_request(route, response.status_code)
        if route in ASK_ROUTES and response.status_code == 200:
            stats.ask_seconds.observe(elapsed)
        log.info("request", extra={"fields": {"method": request.method, "path": request.url.path,
                                               "status": response.status_code, "ms": round(elapsed * 1000)}})
        return response

    @app.exception_handler(httpx.HTTPError)
    async def model_server_down(request: Request, error: httpx.HTTPError):
        log.error("model server lỗi", extra={"fields": {"path": request.url.path, "error": repr(error)}})
        return JSONResponse({"detail": "Model server (llm/embed) không phản hồi"}, status_code=503)

    @app.exception_handler(psycopg.OperationalError)
    async def database_down(request: Request, error: psycopg.OperationalError):
        log.error("database lỗi", extra={"fields": {"path": request.url.path, "error": str(error).strip()}})
        return JSONResponse({"detail": "Database không phản hồi"}, status_code=503)

    @app.exception_handler(oidc.ProviderError)
    async def idp_down(request: Request, error: oidc.ProviderError):
        log.error("IdP lỗi", extra={"fields": {"path": request.url.path, "error": str(error)}})
        return JSONResponse({"detail": "IdP (OIDC) không phản hồi hoặc cấu hình sai"}, status_code=503)

    def allowed(user: User) -> list[str] | None:
        return None if user.admin else acl.prefixes(rules, set(user.groups))

    def store(upload: UploadFile, tags: str | None, folder: str | None, user: User) -> dict:
        filename = ingest.document_path(folder or "", upload.filename or "")
        prefixes = allowed(user)
        if prefixes is not None and not acl.visible(filename, prefixes):
            raise HTTPException(status_code=403, detail="Không được thêm tài liệu vào thư mục này (ACL)")
        data = upload.file.read(max_bytes + 1)
        tag_list = parse_tags(tags) if tags_enabled and tags else None
        try:
            with db.connect(settings.database_url) as conn:
                existing = db.document_filename(conn, ingest.document_id(data))
                if prefixes is not None and existing is not None and not acl.visible(existing, prefixes):
                    raise HTTPException(status_code=403, detail="Không được thêm tài liệu vào thư mục này (ACL)")
                result = ingest.ingest_bytes(conn, app.state.embed, filename, data, max_bytes=max_bytes,
                                             tags=tag_list)
        except ingest.TooLarge as error:
            raise HTTPException(status_code=413, detail=str(error))
        except ingest.UnsupportedType as error:
            raise HTTPException(status_code=415, detail=str(error))
        except ingest.EmptyDocument as error:
            raise HTTPException(status_code=422, detail=str(error))
        if tags_enabled:
            result["tags"] = tag_list or []
        return result

    def parse_tags(raw: str) -> list[str]:
        tag_list = [t.strip() for t in raw.split(",") if t.strip()]
        if len(tag_list) > MAX_TAGS or any(len(t) > MAX_TAG_LENGTH for t in tag_list):
            raise HTTPException(status_code=422,
                                detail=f"Tối đa {MAX_TAGS} tag, mỗi tag tối đa {MAX_TAG_LENGTH} ký tự")
        return tag_list

    def ask(question: str, top_k: int, user: User) -> dict:
        with db.connect(settings.database_url) as conn:
            return rag.answer(conn, app.state.embed, app.state.llm, question, top_k, allowed(user))

    def documents(user: User) -> list[dict]:
        with db.connect(settings.database_url) as conn:
            return db.list_documents(conn, with_tags=tags_enabled, allowed=allowed(user))

    def db_healthy() -> bool:
        try:
            with db.connect(settings.database_url, timeout=2) as conn:
                conn.execute("SET statement_timeout = 1500")
                return conn.execute("SELECT 1").fetchone()[0] == 1
        except psycopg.Error:
            return False

    @app.get("/healthz")
    def healthz():
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {"db": pool.submit(db_healthy),
                       "llm": pool.submit(app.state.llm.healthy, HEALTH_TIMEOUT_S),
                       "embed": pool.submit(app.state.embed.healthy, HEALTH_TIMEOUT_S)}
            checks = {name: future.result() for name, future in futures.items()}
        healthy = all(checks.values())
        return JSONResponse({"status": "ok" if healthy else "degraded", "version": settings.version,
                             "checks": checks}, status_code=200 if healthy else 503)

    @app.get("/metrics")
    def prometheus_metrics():
        return Response(stats.render(), media_type=metrics.CONTENT_TYPE)

    @app.get("/api/me")
    def me(user: User = Depends(auth.require_token)):
        return {"user": user.name, "groups": sorted(user.groups), "admin": user.admin}

    @app.get("/api/documents")
    def list_documents(user: User = Depends(auth.require_token)):
        return documents(user)

    @app.post("/api/documents", status_code=201)
    def upload_document(file: UploadFile, tags: str | None = Form(default=None),
                        folder: str | None = Form(default=None, max_length=512),
                        user: User = Depends(auth.require_token)):
        return store(file, tags, folder, user)

    @app.post("/api/ask")
    def api_ask(body: AskRequest, user: User = Depends(auth.require_token)):
        result = ask(body.question, body.top_k, user)
        citations = [{"doc_id": c["doc_id"], "chunk": c["chunk"], "text": c["text"]} for c in result["citations"]]
        return {"answer": result["answer"], "citations": citations, "model": result["model"]}

    page = {"version": settings.version, "sso": settings.oidc_enabled}

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return templates.TemplateResponse(request, "login.html", page)

    def start_session(request: Request, response: Response, value: str) -> Response:
        response.set_cookie(auth.SESSION_COOKIE, value, max_age=auth.SESSION_MAX_AGE, httponly=True,
                            samesite="strict", secure=request.url.scheme == "https")
        return response

    @app.post("/login")
    def login(request: Request, token: str = Form(max_length=512)):
        if not auth.token_matches(token, settings.admin_token):
            log.warning("đăng nhập sai token", extra={"fields": {"client": request.client.host if request.client else ""}})
            return templates.TemplateResponse(request, "login.html", {**page, "error": True}, status_code=401)
        return start_session(request, RedirectResponse("/", status_code=303), auth.session_value(settings.admin_token))

    def provider() -> oidc.Provider:
        if app.state.oidc is None:
            raise HTTPException(status_code=404, detail="SSO (OIDC) chưa bật")
        return app.state.oidc

    @app.get("/oidc/login")
    def oidc_login(request: Request):
        """Bắt đầu authorization code + PKCE: state, nonce, code_verifier nằm trong cookie ký HMAC, sống 10 phút."""
        started = provider().login_request(str(request.url_for("oidc_callback")))
        response = RedirectResponse(started.url, status_code=303)
        value = auth.sign_payload(settings.admin_token, "o1", {"s": started.state, "n": started.nonce,
                                                               "v": started.verifier, "i": int(auth.clock())})
        response.set_cookie(OIDC_COOKIE, value, max_age=OIDC_COOKIE_MAX_AGE, path="/oidc", httponly=True,
                            samesite="lax", secure=request.url.scheme == "https")
        return response

    @app.get("/oidc/callback", name="oidc_callback")
    def oidc_callback(request: Request, code: str = "", state: str = ""):
        idp = provider()
        pending = auth.read_payload(settings.admin_token, "o1", request.cookies.get(OIDC_COOKIE), OIDC_COOKIE_MAX_AGE)
        if not code or pending is None or not auth.token_matches(state, str(pending.get("s", ""))):
            raise HTTPException(status_code=400, detail="Phiên đăng nhập SSO không hợp lệ hoặc đã hết hạn")
        try:
            identity = idp.exchange(code, str(request.url_for("oidc_callback")), pending["v"], pending["n"])
        except oidc.InvalidToken as error:
            log.warning("đăng nhập SSO bị từ chối", extra={"fields": {"reason": str(error)}})
            raise HTTPException(status_code=401, detail="IdP không xác nhận đăng nhập") from error
        log.info("đăng nhập SSO", extra={"fields": {"user": identity.name, "groups": sorted(identity.groups)}})
        response = templates.TemplateResponse(request, "signed_in.html", page)
        response.delete_cookie(OIDC_COOKIE, path="/oidc")
        value = auth.user_session_value(settings.admin_token, User(identity.name, identity.groups))
        return start_session(request, response, value)

    @app.post("/logout")
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(auth.SESSION_COOKIE)
        return response

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        user = auth.session_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(request, "index.html", {**page, "documents": documents(user), "user": user,
                                                                   "tags_enabled": tags_enabled})

    def require_session(request: Request) -> User:
        user = auth.session_user(request)
        if user is None:
            headers = {"HX-Redirect": "/login"} if request.headers.get("hx-request") else None
            raise HTTPException(status_code=401, detail="Phiên đăng nhập hết hạn", headers=headers)
        return user

    @app.post("/ui/ask", response_class=HTMLResponse)
    def ui_ask(request: Request, question: str = Form(min_length=1, max_length=2000),
               user: User = Depends(require_session)):
        result = ask(question, 4, user)
        return templates.TemplateResponse(request, "_answer.html", {"question": question, **result})

    @app.post("/ui/documents", response_class=HTMLResponse)
    def ui_upload(request: Request, file: UploadFile, tags: str | None = Form(default=None),
                  folder: str | None = Form(default=None, max_length=512), user: User = Depends(require_session)):
        return templates.TemplateResponse(request, "_uploaded.html", {"document": store(file, tags, folder, user)})

    def db_query(sql: str, params=()) -> list[dict]:
        with db.connect(settings.database_url) as conn:
            return db.read_only_query(conn, sql, params)

    extensions.load(app, settings, lambda env: extensions.ExtensionContext(
        settings=settings, ask=ask, db_query=db_query, templates=env, require_user=auth.require_user))
    return app
