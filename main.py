from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings
from app.db.database import engine
from app.db.models import Base
from app.api import products, stores, prices, competitor_mappings, reports, scrape, monitored_urls

_STATIC_DIR = Path(__file__).parent / "app" / "static"

_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[Startup] Database tables ready.")
    except Exception as e:
        print(f"[Startup] WARNING: Could not create tables: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated marketplace price monitoring for Adata distributor",
    lifespan=lifespan
)


# --- Dashboard middleware: serve index.html for GET / before routing ---
class DashboardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "GET" and request.url.path == "/":
            index = _STATIC_DIR / "index.html"
            content = index.read_text(encoding="utf-8") if index.exists() else "<h2>Dashboard not found</h2>"
            return HTMLResponse(content=content, headers=_NO_CACHE_HEADERS)
        return await call_next(request)

app.add_middleware(DashboardMiddleware)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard_root():
    index = _STATIC_DIR / "index.html"
    content = index.read_text(encoding="utf-8") if index.exists() else "<h2>Dashboard not found</h2>"
    return HTMLResponse(content=content, headers=_NO_CACHE_HEADERS)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# --- API routers ---
app.include_router(products.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(competitor_mappings.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(scrape.router, prefix="/api/v1")
app.include_router(monitored_urls.router, prefix="/api/v1")

# --- Static files ---
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
