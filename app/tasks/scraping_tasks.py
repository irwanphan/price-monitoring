from app.tasks.celery_app import celery_app
from app.scrapers.orchestrator import ScraperOrchestrator
from app.db.database import async_session_factory
from app.db.models import Product, Store, PriceSnapshot
from app.crud import PriceSnapshotCRUD
from app.scrapers.base import ScrapedPriceData
from datetime import datetime
import asyncio


@celery_app.task(bind=True, max_retries=3)
def run_weekly_scraping(self):
    """
    Weekly task: Scrape prices from all configured stores.
    Runs every Monday at 6 AM.
    """
    async def _run():
        orchestrator = ScraperOrchestrator(use_zyte=False)  # Set True if using Zyte
        
        async with async_session_factory() as db:
            # Get all active products
            from sqlalchemy import select
            from app.db.models import Product as ProductModel, Store as StoreModel
            
            products_result = await db.execute(
                select(ProductModel).where(ProductModel.is_active == True)
            )
            products = products_result.scalars().all()
            
            stores_result = await db.execute(
                select(StoreModel).where(StoreModel.is_active == True)
            )
            stores = stores_result.scalars().all()
            
            if not products or not stores:
                print("[WeeklyScraping] No products or stores configured. Skipping.")
                return
            
            # Build store configs for orchestrator
            store_configs = [
                {
                    "marketplace": store.marketplace,
                    "store_id": store.store_id,
                    "store_name": store.store_name
                }
                for store in stores
            ]
            
            # Build product queries (use SKU + name)
            product_queries = [
                f"{p.brand} {p.name}" for p in products
            ]
            
            print(f"[WeeklyScraping] Starting scrape: {len(product_queries)} products, {len(store_configs)} stores")
            
            # Run scraping
            scraped_data = await orchestrator.scrape_all_stores(
                product_queries,
                store_configs
            )
            
            # Store results in database
            for item in scraped_data:
                # Match product by name/SKU
                product = await _match_product(db, item)
                if not product:
                    continue
                
                # Match store
                store = await _match_store(db, item)
                if not store:
                    continue
                
                # Create price snapshot
                snapshot = PriceSnapshot(
                    product_id=product.id,
                    store_id=store.id,
                    marketplace=item.marketplace,
                    price=item.price,
                    original_price=item.original_price,
                    discount_percentage=item.discount_percentage,
                    stock_status=item.stock_status,
                    product_url=item.product_url,
                    is_valid=True,  # Will be validated
                    snapshot_date=item.scraped_at
                )
                
                await PriceSnapshotCRUD.create(db, snapshot)
            
            await db.commit()
            print(f"[WeeklyScraping] Completed. Saved {len(scraped_data)} price snapshots.")
    
    asyncio.run(_run())


@celery_app.task(bind=True, max_retries=1)
def run_anomaly_check(self):
    """
    Daily task: Check for price anomalies in recent data.
    Runs every day at 8 AM.
    """
    async def _run():
        from app.services.price_validation import validate_price
        from sqlalchemy import select
        from app.db.models import PriceSnapshot
        
        async with async_session_factory() as db:
            # Get recent unvalidated snapshots
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=1)
            
            result = await db.execute(
                select(PriceSnapshot)
                .where(PriceSnapshot.snapshot_date >= cutoff)
            )
            snapshots = result.scalars().all()
            
            anomaly_count = 0
            for snapshot in snapshots:
                is_valid, reason = await validate_price(
                    db, snapshot.product_id, snapshot.price, snapshot.marketplace
                )
                if not is_valid:
                    snapshot.is_valid = False
                    snapshot.anomaly_reason = reason
                    anomaly_count += 1
            
            await db.commit()
            print(f"[AnomalyCheck] Checked {len(snapshots)} snapshots, found {anomaly_count} anomalies.")
    
    asyncio.run(_run())


async def _match_product(db, scraped_item: ScrapedPriceData):
    """Match scraped item to product in database."""
    from sqlalchemy import select
    from app.db.models import Product as ProductModel
    
    # Try exact SKU match first
    if scraped_item.product_sku:
        result = await db.execute(
            select(ProductModel).where(ProductModel.sku == scraped_item.product_sku)
        )
        product = result.scalar_one_or_none()
        if product:
            return product
    
    # Try fuzzy name match
    result = await db.execute(
        select(ProductModel).where(
            ProductModel.name.ilike(f"%{scraped_item.product_name}%")
        )
    )
    return result.scalar_one_or_none()


async def _match_store(db, scraped_item: ScrapedPriceData):
    """Match scraped item to store in database."""
    from sqlalchemy import select
    from app.db.models import Store as StoreModel
    
    result = await db.execute(
        select(StoreModel).where(
            (StoreModel.marketplace == scraped_item.marketplace) &
            (StoreModel.store_id == scraped_item.store_id)
        )
    )
    return result.scalar_one_or_none()
