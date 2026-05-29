from app.tasks.celery_app import celery_app
from app.scrapers.orchestrator import ScraperOrchestrator
from app.db.database import async_session_factory
from app.db.models import PriceSnapshot
from app.crud import PriceSnapshotCRUD, MonitoredURLCRUD
from app.scrapers.base import ScrapedPriceData
from app.services.price_validation import validate_price
from datetime import datetime
import asyncio


@celery_app.task(bind=True, max_retries=3)
def run_weekly_scraping(self):
    """
    Weekly task: Scrape all active MonitoredURLs.
    Runs every Monday at 6 AM WIB.

    Flow:
    1. Fetch all active MonitoredURL rows from DB
    2. Group URLs by store for efficient scraping
    3. Scrape via Zyte API
    4. Save price snapshots with anomaly validation
    5. Update last_scraped_at on each MonitoredURL
    """
    async def _run():
        orchestrator = ScraperOrchestrator(use_zyte=True)

        async with async_session_factory() as db:
            # Get all active monitored URLs
            monitored_urls = await MonitoredURLCRUD.get_active_urls(db)

            if not monitored_urls:
                print("[WeeklyScraping] No active monitored URLs configured. Skipping.")
                print("[WeeklyScraping] Tip: Add URLs via POST /api/v1/monitored-urls/")
                return

            print(f"[WeeklyScraping] Starting scrape of {len(monitored_urls)} monitored URLs...")

            # Extract all URLs to scrape
            urls_to_scrape = [m.url for m in monitored_urls]

            # Build url → monitored_url mapping for later DB update
            url_to_monitored = {m.url: m for m in monitored_urls}

            # Scrape all URLs
            scraped_data = await orchestrator.scrape_product_urls(urls_to_scrape)

            # Build url → scraped data mapping
            url_to_scraped = {item.product_url: item for item in scraped_data}

            saved_count = 0
            for monitored in monitored_urls:
                scraped = url_to_scraped.get(monitored.url)

                if not scraped:
                    print(f"[WeeklyScraping] No data returned for: {monitored.url}")
                    continue

                # Validate price
                is_valid, anomaly_reason = await validate_price(
                    db, monitored.product_id, scraped.price, scraped.marketplace
                )

                # Save price snapshot
                snapshot = PriceSnapshot(
                    product_id=monitored.product_id,
                    store_id=monitored.store_id,
                    marketplace=scraped.marketplace,
                    price=scraped.price,
                    original_price=scraped.original_price,
                    discount_percentage=scraped.discount_percentage,
                    stock_status=scraped.stock_status,
                    product_url=scraped.product_url,
                    is_valid=is_valid,
                    anomaly_reason=anomaly_reason,
                    snapshot_date=scraped.scraped_at or datetime.utcnow()
                )
                await PriceSnapshotCRUD.create(db, snapshot)

                # Update last_scraped_at
                await MonitoredURLCRUD.mark_scraped(db, monitored.id)
                saved_count += 1

            await db.commit()
            print(f"[WeeklyScraping] Done. Saved {saved_count}/{len(monitored_urls)} snapshots.")

    asyncio.run(_run())


@celery_app.task(bind=True, max_retries=1)
def run_anomaly_check(self):
    """
    Daily task: Re-validate recent snapshots for price anomalies.
    Runs every day at 8 AM WIB.
    """
    async def _run():
        from sqlalchemy import select
        from app.db.models import PriceSnapshot

        async with async_session_factory() as db:
            # Get recent snapshots (last 24h)
            from datetime import timedelta
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
