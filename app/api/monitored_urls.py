from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.db.models import MonitoredURL
from app.schemas import MonitoredURLCreate, MonitoredURLUpdate, MonitoredURLResponse, BulkMonitoredURLCreate
from app.crud import MonitoredURLCRUD, ProductCRUD, StoreCRUD

router = APIRouter(prefix="/monitored-urls", tags=["monitored-urls"])


@router.post("/", response_model=MonitoredURLResponse, status_code=201)
async def add_monitored_url(
    data: MonitoredURLCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a product URL to monitor for automatic weekly scraping.

    Steps:
    1. First add a Product via POST /api/v1/products/
    2. Then add a Store via POST /api/v1/stores/
    3. Then register the product URL here (can add many URLs per product/store)

    The scheduled scraper will automatically scrape all active URLs every Monday 6 AM.
    """
    # Validate product exists
    product = await ProductCRUD.get_by_id(db, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product ID {data.product_id} not found")

    # Validate store exists
    store = await StoreCRUD.get_by_id(db, data.store_id)
    if not store:
        raise HTTPException(status_code=404, detail=f"Store ID {data.store_id} not found")

    monitored = MonitoredURL(
        product_id=data.product_id,
        store_id=data.store_id,
        url=data.url,
        label=data.label or f"{product.brand} {product.name} - {store.marketplace}",
        is_active=True
    )

    try:
        created = await MonitoredURLCRUD.create(db, monitored)
    except Exception as e:
        if "uq_product_store_url" in str(e):
            raise HTTPException(status_code=400, detail="This URL is already registered for this product/store combination")
        raise

    return MonitoredURLResponse(
        id=created.id,
        product_id=created.product_id,
        store_id=created.store_id,
        url=created.url,
        label=created.label,
        is_active=created.is_active,
        last_scraped_at=created.last_scraped_at,
        created_at=created.created_at,
        product_name=product.name,
        product_sku=product.sku,
        store_name=store.store_name,
        marketplace=store.marketplace,
    )


@router.post("/bulk", response_model=list[MonitoredURLResponse], status_code=201)
async def add_monitored_urls_bulk(
    data: BulkMonitoredURLCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register multiple product URLs at once."""
    results = []
    for item in data.urls:
        product = await ProductCRUD.get_by_id(db, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found")

        store = await StoreCRUD.get_by_id(db, item.store_id)
        if not store:
            raise HTTPException(status_code=404, detail=f"Store ID {item.store_id} not found")

        monitored = MonitoredURL(
            product_id=item.product_id,
            store_id=item.store_id,
            url=item.url,
            label=item.label or f"{product.brand} {product.name} - {store.marketplace}",
            is_active=True
        )
        created = await MonitoredURLCRUD.create(db, monitored)
        results.append(MonitoredURLResponse(
            id=created.id,
            product_id=created.product_id,
            store_id=created.store_id,
            url=created.url,
            label=created.label,
            is_active=created.is_active,
            last_scraped_at=created.last_scraped_at,
            created_at=created.created_at,
            product_name=product.name,
            product_sku=product.sku,
            store_name=store.store_name,
            marketplace=store.marketplace,
        ))
    return results


@router.get("/", response_model=list[MonitoredURLResponse])
async def get_monitored_urls(
    product_id: Optional[int] = None,
    store_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db)
):
    """List all monitored URLs (optionally filtered by product or store)."""
    items = await MonitoredURLCRUD.get_all(
        db,
        product_id=product_id,
        store_id=store_id,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return [
        MonitoredURLResponse(
            id=m.id,
            product_id=m.product_id,
            store_id=m.store_id,
            url=m.url,
            label=m.label,
            is_active=m.is_active,
            last_scraped_at=m.last_scraped_at,
            created_at=m.created_at,
            product_name=m.product.name if m.product else None,
            product_sku=m.product.sku if m.product else None,
            store_name=m.store.store_name if m.store else None,
            marketplace=m.store.marketplace if m.store else None,
        )
        for m in items
    ]


@router.get("/{url_id}", response_model=MonitoredURLResponse)
async def get_monitored_url(url_id: int, db: AsyncSession = Depends(get_db)):
    item = await MonitoredURLCRUD.get_by_id(db, url_id)
    if not item:
        raise HTTPException(status_code=404, detail="Monitored URL not found")

    product = await ProductCRUD.get_by_id(db, item.product_id)
    store = await StoreCRUD.get_by_id(db, item.store_id)

    return MonitoredURLResponse(
        id=item.id,
        product_id=item.product_id,
        store_id=item.store_id,
        url=item.url,
        label=item.label,
        is_active=item.is_active,
        last_scraped_at=item.last_scraped_at,
        created_at=item.created_at,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        store_name=store.store_name if store else None,
        marketplace=store.marketplace if store else None,
    )


@router.put("/{url_id}", response_model=MonitoredURLResponse)
async def update_monitored_url(
    url_id: int,
    update_data: MonitoredURLUpdate,
    db: AsyncSession = Depends(get_db)
):
    item = await MonitoredURLCRUD.get_by_id(db, url_id)
    if not item:
        raise HTTPException(status_code=404, detail="Monitored URL not found")

    updated = await MonitoredURLCRUD.update(db, item, update_data.model_dump(exclude_unset=True))
    product = await ProductCRUD.get_by_id(db, updated.product_id)
    store = await StoreCRUD.get_by_id(db, updated.store_id)

    return MonitoredURLResponse(
        id=updated.id,
        product_id=updated.product_id,
        store_id=updated.store_id,
        url=updated.url,
        label=updated.label,
        is_active=updated.is_active,
        last_scraped_at=updated.last_scraped_at,
        created_at=updated.created_at,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        store_name=store.store_name if store else None,
        marketplace=store.marketplace if store else None,
    )


@router.delete("/{url_id}", status_code=204)
async def delete_monitored_url(url_id: int, db: AsyncSession = Depends(get_db)):
    success = await MonitoredURLCRUD.delete(db, url_id)
    if not success:
        raise HTTPException(status_code=404, detail="Monitored URL not found")
    return None
