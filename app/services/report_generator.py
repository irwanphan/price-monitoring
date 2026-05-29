import io
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import PriceSnapshot, Product, Store, CompetitorMapping
from app.crud import ProductCRUD
import xlsxwriter


class ReportGenerator:
    """Generate Excel reports for price comparisons."""

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

        Returns:
            Excel file as BytesIO
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Shared formats
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#2F5496", "font_color": "white",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        currency_fmt = workbook.add_format({"num_format": "#,##0", "align": "right"})
        pct_fmt = workbook.add_format({"num_format": "0.0%", "align": "right"})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm", "align": "center"})
        anomaly_fmt = workbook.add_format({"bg_color": "#FFD7D7"})
        title_fmt = workbook.add_format({"bold": True, "font_size": 12})
        subtitle_fmt = workbook.add_format({"italic": True, "font_color": "#666666"})

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get products
        if product_sku:
            products = [await ProductCRUD.get_by_sku(self.db, product_sku)]
        else:
            products = await ProductCRUD.get_all(self.db, brand=brand, is_active=True)

        products = [p for p in products if p]  # filter None

        # 1. Summary sheet
        await self._write_summary_sheet(
            workbook.add_worksheet("Summary"),
            products,
            cutoff_date,
            header_fmt, currency_fmt, title_fmt, subtitle_fmt, days
        )

        # 2. Detailed sheet per product
        for product in products:
            safe_name = f"{product.brand[:10]}-{product.sku[:18]}"  # max 31 chars
            sheet = workbook.add_worksheet(safe_name)
            await self._write_product_sheet(
                sheet, product, cutoff_date,
                header_fmt, currency_fmt, pct_fmt, date_fmt, anomaly_fmt
            )

        workbook.close()
        output.seek(0)
        return output

    async def _write_summary_sheet(
        self, worksheet, products: list, cutoff_date: datetime,
        header_fmt, currency_fmt, title_fmt, subtitle_fmt, days: int
    ):
        """Write summary overview sheet with actual price data."""
        # Title
        worksheet.write(0, 0, "Adata Price Monitor — Summary Report", title_fmt)
        worksheet.write(1, 0, f"Period: last {days} days  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", subtitle_fmt)
        worksheet.merge_range(0, 0, 0, 9, "Adata Price Monitor — Summary Report", title_fmt)
        worksheet.merge_range(1, 0, 1, 9,
            f"Period: last {days} days  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            subtitle_fmt
        )

        headers = [
            "Brand", "Product Name", "SKU", "Category",
            "# Listings", "Min Price (Rp)", "Max Price (Rp)",
            "Avg Price (Rp)", "Cheapest Store", "Report Date"
        ]
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_fmt)

        for row, product in enumerate(products, start=4):
            # Query aggregated price data for this product
            result = await self.db.execute(
                select(
                    func.count(PriceSnapshot.id).label("count"),
                    func.min(PriceSnapshot.price).label("min_price"),
                    func.max(PriceSnapshot.price).label("max_price"),
                    func.avg(PriceSnapshot.price).label("avg_price"),
                )
                .where(PriceSnapshot.product_id == product.id)
                .where(PriceSnapshot.snapshot_date >= cutoff_date)
                .where(PriceSnapshot.is_valid == True)
            )
            agg = result.one()

            # Cheapest store
            cheapest_store_name = ""
            if agg.min_price:
                snap_result = await self.db.execute(
                    select(PriceSnapshot, Store)
                    .join(Store, PriceSnapshot.store_id == Store.id)
                    .where(PriceSnapshot.product_id == product.id)
                    .where(PriceSnapshot.snapshot_date >= cutoff_date)
                    .where(PriceSnapshot.price == agg.min_price)
                    .where(PriceSnapshot.is_valid == True)
                    .limit(1)
                )
                snap_row = snap_result.first()
                if snap_row:
                    _, cheapest_store = snap_row
                    cheapest_store_name = f"{cheapest_store.store_name} ({cheapest_store.marketplace})"

            worksheet.write(row, 0, product.brand)
            worksheet.write(row, 1, product.name)
            worksheet.write(row, 2, product.sku)
            worksheet.write(row, 3, product.category or "")
            worksheet.write(row, 4, agg.count or 0)
            worksheet.write(row, 5, round(agg.min_price or 0), currency_fmt)
            worksheet.write(row, 6, round(agg.max_price or 0), currency_fmt)
            worksheet.write(row, 7, round(agg.avg_price or 0), currency_fmt)
            worksheet.write(row, 8, cheapest_store_name)
            worksheet.write(row, 9, datetime.utcnow().strftime("%Y-%m-%d"))

        col_widths = [10, 40, 18, 12, 10, 18, 18, 18, 35, 14]
        for col, width in enumerate(col_widths):
            worksheet.set_column(col, col, width)

    async def _write_product_sheet(
        self, worksheet, product: Product, cutoff_date: datetime,
        header_fmt, currency_fmt, pct_fmt, date_fmt, anomaly_fmt
    ):
        """Write detailed product price history sheet."""
        # Product info block
        info_fmt = worksheet.workbook.add_format({"bold": True})
        worksheet.write(0, 0, f"Product: {product.brand} — {product.name}", info_fmt)
        worksheet.write(1, 0, f"SKU: {product.sku}   Category: {product.category or '-'}")
        worksheet.write(2, 0, f"Report from: {cutoff_date.strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')}")

        # Headers (row 4)
        headers = [
            "Date", "Marketplace", "Store Name",
            "Price (Rp)", "Original Price (Rp)", "Discount %",
            "Stock", "Valid?", "Anomaly Reason", "URL"
        ]
        for col, h in enumerate(headers):
            worksheet.write(4, col, h, header_fmt)

        # Data
        result = await self.db.execute(
            select(PriceSnapshot, Store)
            .join(Store, PriceSnapshot.store_id == Store.id)
            .where(PriceSnapshot.product_id == product.id)
            .where(PriceSnapshot.snapshot_date >= cutoff_date)
            .order_by(PriceSnapshot.snapshot_date.desc())
        )
        rows = result.all()

        for data_row, (snapshot, store) in enumerate(rows, start=5):
            row_fmt = anomaly_fmt if not snapshot.is_valid else None

            def w(col, val, fmt=None):
                worksheet.write(data_row, col, val, fmt or row_fmt)

            w(0, snapshot.snapshot_date.strftime("%Y-%m-%d %H:%M"))
            w(1, snapshot.marketplace)
            w(2, store.store_name)
            w(3, round(snapshot.price), currency_fmt)
            w(4, round(snapshot.original_price) if snapshot.original_price else "", currency_fmt)
            disc = (snapshot.discount_percentage / 100) if snapshot.discount_percentage else ""
            w(5, disc, pct_fmt if disc != "" else None)
            w(6, snapshot.stock_status or "")
            w(7, "✓" if snapshot.is_valid else "✗")
            w(8, snapshot.anomaly_reason or "")
            w(9, snapshot.product_url or "")

        col_widths = [20, 12, 30, 18, 20, 12, 12, 8, 40, 60]
        for col, width in enumerate(col_widths):
            worksheet.set_column(col, col, width)

        # Freeze header rows
        worksheet.freeze_panes(5, 0)
