from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import PriceSnapshot, Product, Store
from app.schemas import BulkScrapeRequest, BulkScrapeResponse, ScrapedProductResponse, PriceSnapshotCreate
from app.crud import PriceSnapshotCRUD, ProductCRUD, StoreCRUD
from app.scrapers.orchestrator import ScraperOrchestrator
from datetime import datetime

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/", response_model=BulkScrapeResponse)
async def bulk_scrape_products(
    request: BulkScrapeRequest,
    save_to_db: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape multiple Tokopedia product URLs using Zyte API.
    
    Optionally saves results to database.
    
    Example request:
    ```json
    {
        "urls": [
            {"url": "https://www.tokopedia.com/adata-xpg-id/product-1"},
            {"url": "https://www.tokopedia.com/agresid/product-2"}
        ],
        "marketplace": "tokopedia"
    }
    ```
    """
    orchestrator = ScraperOrchestrator(use_zyte=True)
    
    # Extract URLs
    product_urls = [u.url for u in request.urls]
    
    # Scrape
    scraped_data = await orchestrator.scrape_product_urls(product_urls)
    
    # Build response
    results = []
    success_count = 0
    failed_count = 0
    
    for item in scraped_data:
        results.append(ScrapedProductResponse(
            product_name=item.product_name,
            product_sku=item.product_sku,
            price=item.price,
            original_price=item.original_price,
            discount_percentage=item.discount_percentage,
            stock_status=item.stock_status,
            product_url=item.product_url,
            store_id=item.store_id,
            store_name=item.store_name,
            marketplace=item.marketplace,
        ))
        success_count += 1
        
        # Optionally save to database
        if save_to_db:
            await _save_scraped_data(db, item, request.marketplace)
    
    failed_count = len(request.urls) - success_count
    
    return BulkScrapeResponse(
        total_requested=len(request.urls),
        total_success=success_count,
        total_failed=failed_count,
        results=results
    )


@router.post("/test")
async def test_scrape_single(url: str):
    """
    Test scraping a single product URL.
    Quick test without saving to database.
    """
    orchestrator = ScraperOrchestrator(use_zyte=True)
    results = await orchestrator.scrape_product_urls([url])
    
    if not results:
        return {"error": "Failed to scrape product", "url": url}
    
    item = results[0]
    return {
        "product_name": item.product_name,
        "price": item.price,
        "original_price": item.original_price,
        "discount_percentage": item.discount_percentage,
        "stock_status": item.stock_status,
        "store_id": item.store_id,
        "product_url": item.product_url,
    }


async def _save_scraped_data(db: AsyncSession, item, marketplace: str):
    """Save scraped data to price_snapshots table."""
    from app.services.price_validation import validate_price
    
    # Find or create store
    store = await StoreCRUD.get_all(db, marketplace=marketplace, store_marketplace_id=item.store_id)
    if not store:
        store_obj = Store(
            marketplace=marketplace,
            store_id=item.store_id,
            store_name=item.store_name
        )
        store_obj = await StoreCRUD.create(db, store_obj)
    else:
        store_obj = store[0]
    
    # Find matching product by URL pattern or name
    product = None
    if item.product_sku:
        product = await ProductCRUD.get_by_sku(db, item.product_sku)
    
    if not product:
        # Try to find by name match
        from sqlalchemy import select
        result = await db.execute(
            select(Product).where(Product.name.ilike(f"%{item.product_name[:50]}%"))
        )
        product = result.scalar_one_or_none()
    
    if not product:
        # Auto-create product if not found
        product = Product(
            brand=item.store_id,  # Use store as brand for now
            name=item.product_name,
            sku=f"AUTO_{item.store_id}_{hash(item.product_name) % 10000}",
            category="SSD",  # Default
            is_active=True
        )
        product = await ProductCRUD.create(db, product)
    
    # Validate price
    is_valid, anomaly_reason = await validate_price(
        db, product.id, item.price, marketplace
    )
    
    # Create price snapshot
    snapshot = PriceSnapshot(
        product_id=product.id,
        store_id=store_obj.id,
        marketplace=marketplace,
        price=item.price,
        original_price=item.original_price,
        discount_percentage=item.discount_percentage,
        stock_status=item.stock_status,
        product_url=item.product_url,
        is_valid=is_valid,
        anomaly_reason=anomaly_reason,
        snapshot_date=datetime.utcnow()
    )
    
    await PriceSnapshotCRUD.create(db, snapshot)
