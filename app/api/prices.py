from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from app.db.database import get_db
from app.db.models import PriceSnapshot, Product, Store
from app.schemas import PriceSnapshotCreate, PriceSnapshotResponse, MarketInsight
from app.crud import PriceSnapshotCRUD, ProductCRUD, StoreCRUD
from app.services.price_validation import validate_price

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/", response_model=PriceSnapshotResponse, status_code=201)
async def create_price_snapshot(
    snapshot_data: PriceSnapshotCreate,
    db: AsyncSession = Depends(get_db)
):
    # Get product
    product = await ProductCRUD.get_by_sku(db, snapshot_data.product_sku)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with SKU '{snapshot_data.product_sku}' not found"
        )
    
    # Get store
    store = await StoreCRUD.get_by_id(db, snapshot_data.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Validate price (anomaly detection)
    is_valid, anomaly_reason = await validate_price(
        db, product.id, snapshot_data.price, snapshot_data.marketplace
    )
    
    snapshot = PriceSnapshot(
        product_id=product.id,
        store_id=store.id,
        marketplace=snapshot_data.marketplace.value,
        price=snapshot_data.price,
        original_price=snapshot_data.original_price,
        discount_percentage=snapshot_data.discount_percentage,
        stock_status=snapshot_data.stock_status.value if snapshot_data.stock_status else None,
        product_url=snapshot_data.product_url,
        is_valid=is_valid,
        anomaly_reason=anomaly_reason,
        snapshot_date=snapshot_data.snapshot_date or datetime.utcnow()
    )
    
    created = await PriceSnapshotCRUD.create(db, snapshot)
    return created


@router.get("/product/{product_id}", response_model=list[PriceSnapshotResponse])
async def get_product_prices(
    product_id: int,
    store_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    if store_id:
        return await PriceSnapshotCRUD.get_by_product_and_store(
            db, product_id, store_id, skip, limit
        )
    return await PriceSnapshotCRUD.get_by_product(db, product_id, skip, limit)


@router.get("/product/{product_id}/latest", response_model=list[PriceSnapshotResponse])
async def get_latest_product_prices(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await PriceSnapshotCRUD.get_latest_by_product(db, product_id)


@router.get("/insights/{product_id}", response_model=MarketInsight)
async def get_market_insights(
    product_id: int,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    # Get product
    product = await ProductCRUD.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get recent valid prices
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    from sqlalchemy import select
    result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .where(PriceSnapshot.snapshot_date >= cutoff_date)
        .where(PriceSnapshot.is_valid == True)
    )
    snapshots = result.scalars().all()
    
    if not snapshots:
        raise HTTPException(status_code=404, detail="No price data found for this product")
    
    prices = [s.price for s in snapshots]
    prices_sorted = sorted(prices)
    
    # Find cheapest/most expensive stores
    cheapest = min(snapshots, key=lambda s: s.price)
    most_expensive = max(snapshots, key=lambda s: s.price)
    
    # Get store names
    cheapest_store = await StoreCRUD.get_by_id(db, cheapest.store_id)
    most_expensive_store = await StoreCRUD.get_by_id(db, most_expensive.store_id)
    
    # Calculate median
    n = len(prices_sorted)
    if n % 2 == 0:
        median = (prices_sorted[n//2 - 1] + prices_sorted[n//2]) / 2
    else:
        median = prices_sorted[n//2]
    
    # Count anomalies
    result_anomalies = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .where(PriceSnapshot.snapshot_date >= cutoff_date)
        .where(PriceSnapshot.is_valid == False)
    )
    anomaly_count = len(result_anomalies.scalars().all())
    
    return MarketInsight(
        product_name=product.name,
        total_listings=len(snapshots),
        price_range={
            "min": min(prices),
            "max": max(prices)
        },
        average_price=sum(prices) / len(prices),
        median_price=median,
        cheapest_store=cheapest_store.store_name if cheapest_store else "Unknown",
        most_expensive_store=most_expensive_store.store_name if most_expensive_store else "Unknown",
        anomaly_count=anomaly_count
    )
