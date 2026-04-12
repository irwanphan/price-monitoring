from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import engine
from app.db.models import Base
from app.api import products, stores, prices, competitor_mappings, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup (optional)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated marketplace price monitoring for Adata distributor",
    lifespan=lifespan
)

# Include routers
app.include_router(products.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(competitor_mappings.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
