import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .db import get_engine
from .routers import auth, bins, export, items, labels, locations, photos, settings, sso, tags, users
from .services import webhooks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(webhooks.worker(stop)) if get_settings().webhook_worker else None
    yield
    stop.set()
    if task:
        await task


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Kapaat",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=s.secret_key,
        session_cookie="kapaat_session",
        max_age=s.session_days * 86400,
        same_site="lax",
        https_only=s.cookie_secure,
    )
    for module in (auth, users, locations, bins, items, tags, photos, export, labels, settings, sso):
        app.include_router(module.router)

    @app.get("/api/health")
    def health() -> dict:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "version": app.version}

    return app


app = create_app()
