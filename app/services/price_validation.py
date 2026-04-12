from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import PriceSnapshot
from app.core.config import settings


async def validate_price(
    db: AsyncSession,
    product_id: int,
    price: float,
    marketplace: str
) -> tuple[bool, str | None]:
    """
    Validate if a price is within acceptable range.
    Returns (is_valid, anomaly_reason)
    """
    # Get recent valid prices for this product
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    result = await db.execute(
        select(PriceSnapshot.price)
        .where(PriceSnapshot.product_id == product_id)
        .where(PriceSnapshot.snapshot_date >= cutoff_date)
        .where(PriceSnapshot.is_valid == True)
    )
    historical_prices = result.scalars().all()
    
    if not historical_prices:
        # No historical data, accept the price
        return True, None
    
    # Calculate median
    sorted_prices = sorted(historical_prices)
    n = len(sorted_prices)
    if n % 2 == 0:
        median = (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
    else:
        median = sorted_prices[n//2]
    
    # Calculate acceptable range
    tolerance = settings.DEFAULT_PRICE_TOLERANCE
    min_acceptable = median * (1 - tolerance)
    max_acceptable = median * (1 + tolerance)
    
    # Check if price is within range
    if price < min_acceptable:
        deviation = ((median - price) / median) * 100
        return False, f"Price is {deviation:.1f}% below median (median: {median}, threshold: {min_acceptable})"
    
    if price > max_acceptable:
        deviation = ((price - median) / median) * 100
        return False, f"Price is {deviation:.1f}% above median (median: {median}, threshold: {max_acceptable})"
    
    return True, None
