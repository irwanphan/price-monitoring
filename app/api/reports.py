from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/price-comparison/excel")
async def export_price_comparison_excel(
    product_sku: Optional[str] = None,
    brand: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Export price comparison report as Excel file.
    """
    generator = ReportGenerator(db)
    
    try:
        excel_file = await generator.generate_price_comparison(
            product_sku=product_sku,
            brand=brand,
            days=days
        )
        
        return StreamingResponse(
            iter([excel_file.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=price_comparison_report.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/price-comparison/summary")
async def get_price_comparison_summary(
    product_sku: Optional[str] = None,
    brand: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price comparison summary as JSON (for dashboard display).
    """
    from sqlalchemy import select
    from app.db.models import PriceSnapshot, Product
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get products
    if product_sku:
        from app.crud import ProductCRUD
        products = [await ProductCRUD.get_by_sku(db, product_sku)]
    else:
        from app.crud import ProductCRUD
        products = await ProductCRUD.get_all(db, brand=brand, is_active=True)
    
    summary = []
    for product in products:
        if not product:
            continue
        
        result = await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product.id)
            .where(PriceSnapshot.snapshot_date >= cutoff_date)
            .where(PriceSnapshot.is_valid == True)
        )
        snapshots = result.scalars().all()
        
        if not snapshots:
            continue
        
        prices = [s.price for s in snapshots]
        
        summary.append({
            "product_id": product.id,
            "brand": product.brand,
            "product_name": product.name,
            "sku": product.sku,
            "category": product.category,
            "count": len(snapshots),
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
        })

    # Return list directly so dashboard can iterate
    return summary
