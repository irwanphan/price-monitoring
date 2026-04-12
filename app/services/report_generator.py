import io
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import PriceSnapshot, Product, Store, CompetitorMapping
from app.crud import ProductCRUD
import xlsxwriter


class ReportGenerator:
    """Generate Excel/PDF reports for price comparisons"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_price_comparison(
        self,
        product_sku: Optional[str] = None,
        brand: Optional[str] = None,
        days: int = 7
    ) -> io.BytesIO:
        """
        Generate Excel report with price comparison across marketplaces.
        
        Args:
            product_sku: Filter by specific SKU (None for all)
            brand: Filter by brand (None for all)
            days: Number of days of data to include
        
        Returns:
            Excel file as BytesIO
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        
        # Get cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get products
        if product_sku:
            products = [await ProductCRUD.get_by_sku(self.db, product_sku)]
        else:
            products = await ProductCRUD.get_all(self.db, brand=brand, is_active=True)
        
        # Summary sheet
        summary_sheet = workbook.add_worksheet("Summary")
        self._write_summary_sheet(summary_sheet, products, cutoff_date)
        
        # Detailed sheets per product
        for product in products:
            if not product:
                continue
            sheet = workbook.add_worksheet(f"{product.brand} - {product.sku}"[:31])
            await self._write_product_sheet(sheet, product, cutoff_date)
        
        workbook.close()
        output.seek(0)
        return output
    
    def _write_summary_sheet(self, worksheet, products: list, cutoff_date: datetime):
        """Write summary overview sheet."""
        # Headers
        headers = [
            "Brand", "Product Name", "SKU", "Category",
            "Total Listings", "Lowest Price", "Highest Price",
            "Average Price", "Cheapest Store", "Report Date"
        ]
        
        # Format
        header_format = {
            "bold": True,
            "bg_color": "#2F5496",
            "font_color": "white",
            "border": 1
        }
        header_fmt = worksheet.workbook.add_format(header_format)
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_fmt)
        
        # Write data
        for row, product in enumerate([p for p in products if p], start=1):
            # TODO: Query actual price data
            worksheet.write(row, 0, product.brand)
            worksheet.write(row, 1, product.name)
            worksheet.write(row, 2, product.sku)
            worksheet.write(row, 3, product.category or "")
            worksheet.write(row, 4, 0)  # Total listings
            worksheet.write(row, 5, 0)  # Lowest price
            worksheet.write(row, 6, 0)  # Highest price
            worksheet.write(row, 7, 0)  # Average price
            worksheet.write(row, 8, "")  # Cheapest store
            worksheet.write(row, 9, datetime.utcnow().strftime("%Y-%m-%d"))
        
        # Auto-size columns
        worksheet.set_column(0, 9, 20)
    
    async def _write_product_sheet(self, worksheet, product: Product, cutoff_date: datetime):
        """Write detailed product price history sheet."""
        # Get price data
        result = await self.db.execute(
            select(PriceSnapshot, Store)
            .join(Store, PriceSnapshot.store_id == Store.id)
            .where(PriceSnapshot.product_id == product.id)
            .where(PriceSnapshot.snapshot_date >= cutoff_date)
            .where(PriceSnapshot.is_valid == True)
            .order_by(PriceSnapshot.snapshot_date.desc())
        )
        snapshots = result.all()
        
        # Headers
        headers = [
            "Date", "Marketplace", "Store Name",
            "Price", "Original Price", "Discount %",
            "Stock Status", "Product URL"
        ]
        
        header_format = {
            "bold": True,
            "bg_color": "#2F5496",
            "font_color": "white",
            "border": 1
        }
        header_fmt = worksheet.workbook.add_format(header_format)
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_fmt)
        
        # Write data
        for row, (snapshot, store) in enumerate(snapshots, start=1):
            worksheet.write(row, 0, snapshot.snapshot_date.strftime("%Y-%m-%d %H:%M"))
            worksheet.write(row, 1, snapshot.marketplace)
            worksheet.write(row, 2, store.store_name)
            worksheet.write(row, 3, snapshot.price)
            worksheet.write(row, 4, snapshot.original_price or "")
            worksheet.write(row, 5, f"{snapshot.discount_percentage}%" if snapshot.discount_percentage else "")
            worksheet.write(row, 6, snapshot.stock_status or "")
            worksheet.write(row, 7, snapshot.product_url or "")
        
        # Auto-size columns
        worksheet.set_column(0, 7, 25)
        
        # Add product info at top
        worksheet.insert_text_box(
            0, len(headers) + 2,
            f"Product: {product.name}\nSKU: {product.sku}\nBrand: {product.brand}"
        )
