import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psycopg
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from quillo import auth, db, ingest, rag
from quillo.config import Settings, setup_logging
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
    """Từ chối POST thiếu Content-Length (411) hoặc quá giới hạn (413) trước khi parse body, kể cả trước khi kiểm token:
    upload tối đa QUILLO_MAX_UPLOAD_MB, mọi POST khác (JSON, form) tối đa 64 KB."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            limit = self.max_bytes + MULTIPART_OVERHEAD if scope["path"] in UPLOAD_PATHS else MAX_FORM_BYTES
            length = dict(scope["headers"]).get(b"content-length", b"")
            if not length.isdigit():
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        schema = _wait_and_migrate(settings)
        log.info("quillo sẵn sàng", extra={"fields": {"version": settings.version, "schema": schema}})
        yield
        app.state.llm.close()
        app.state.embed.close()

    app = FastAPI(title="Quillo", version=settings.version, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.llm = ModelServer(settings.llm_url, settings.http_timeout_s)
    app.state.embed = ModelServer(settings.embed_url, settings.http_timeout_s)
    app.add_middleware(BodyLimit, max_bytes=max_bytes)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        log.info("request", extra={"fields": {"method": request.method, "path": request.url.path,
                                               "status": response.status_code,
                                               "ms": round((time.perf_counter() - started) * 1000)}})
        return response

    @app.exception_handler(httpx.HTTPError)
    async def model_server_down(request: Request, error: httpx.HTTPError):
        log.error("model server lỗi", extra={"fields": {"path": request.url.path, "error": repr(error)}})
        return JSONResponse({"detail": "Model server (llm/embed) không phản hồi"}, status_code=503)

    @app.exception_handler(psycopg.OperationalError)
    async def database_down(request: Request, error: psycopg.OperationalError):
        log.error("database lỗi", extra={"fields": {"path": request.url.path, "error": str(error).strip()}})
        return JSONResponse({"detail": "Database không phản hồi"}, status_code=503)

    def store(upload: UploadFile, tags: str | None) -> dict:
        filename = ingest.safe_filename(upload.filename or "")
        data = upload.file.read(max_bytes + 1)
        tag_list = parse_tags(tags) if tags_enabled and tags else None
        try:
            with db.connect(settings.database_url) as conn:
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

    def ask(question: str, top_k: int) -> dict:
        with db.connect(settings.database_url) as conn:
            return rag.answer(conn, app.state.embed, app.state.llm, question, top_k)

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

    @app.get("/api/documents", dependencies=[Depends(auth.require_token)])
    def list_documents():
        with db.connect(settings.database_url) as conn:
            return db.list_documents(conn, with_tags=tags_enabled)

    @app.post("/api/documents", status_code=201, dependencies=[Depends(auth.require_token)])
    def upload_document(file: UploadFile, tags: str | None = Form(default=None)):
        return store(file, tags)

    @app.post("/api/ask", dependencies=[Depends(auth.require_token)])
    def api_ask(body: AskRequest):
        result = ask(body.question, body.top_k)
        citations = [{"doc_id": c["doc_id"], "chunk": c["chunk"], "text": c["text"]} for c in result["citations"]]
        return {"answer": result["answer"], "citations": citations, "model": result["model"]}

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return templates.TemplateResponse(request, "login.html", {"version": settings.version})

    @app.post("/login")
    def login(request: Request, token: str = Form(max_length=512)):
        if not auth.token_matches(token, settings.admin_token):
            log.warning("đăng nhập sai token", extra={"fields": {"client": request.client.host if request.client else ""}})
            return templates.TemplateResponse(request, "login.html", {"version": settings.version, "error": True},
                                              status_code=401)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(auth.SESSION_COOKIE, auth.session_value(settings.admin_token), max_age=auth.SESSION_MAX_AGE,
                            httponly=True, samesite="strict", secure=request.url.scheme == "https")
        return response

    @app.post("/logout")
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(auth.SESSION_COOKIE)
        return response

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        if not auth.has_session(request):
            return RedirectResponse("/login", status_code=303)
        with db.connect(settings.database_url) as conn:
            documents = db.list_documents(conn, with_tags=tags_enabled)
        return templates.TemplateResponse(request, "index.html", {"version": settings.version, "documents": documents,
                                                                   "tags_enabled": tags_enabled})

    def require_session(request: Request) -> None:
        if not auth.has_session(request):
            headers = {"HX-Redirect": "/login"} if request.headers.get("hx-request") else None
            raise HTTPException(status_code=401, detail="Phiên đăng nhập hết hạn", headers=headers)

    @app.post("/ui/ask", response_class=HTMLResponse, dependencies=[Depends(require_session)])
    def ui_ask(request: Request, question: str = Form(min_length=1, max_length=2000)):
        result = ask(question, 4)
        return templates.TemplateResponse(request, "_answer.html", {"question": question, **result})

    @app.post("/ui/documents", response_class=HTMLResponse, dependencies=[Depends(require_session)])
    def ui_upload(request: Request, file: UploadFile, tags: str | None = Form(default=None)):
        return templates.TemplateResponse(request, "_uploaded.html", {"document": store(file, tags)})

    return app
