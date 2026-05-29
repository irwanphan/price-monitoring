from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Product, Store, PriceSnapshot, CompetitorMapping, MonitoredURL


class ProductCRUD:
    @staticmethod
    async def create(db: AsyncSession, product: Product) -> Product:
        db.add(product)
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Product | None:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_sku(db: AsyncSession, sku: str) -> Product | None:
        result = await db.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        brand: str | None = None,
        category: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100
    ) -> list[Product]:
        query = select(Product)
        if brand:
            query = query.where(Product.brand == brand)
        if category:
            query = query.where(Product.category == category)
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, product: Product, update_data: dict) -> Product:
        for key, value in update_data.items():
            setattr(product, key, value)
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def delete(db: AsyncSession, product_id: int) -> bool:
        product = await ProductCRUD.get_by_id(db, product_id)
        if product:
            await db.delete(product)
            return True
        return False


class StoreCRUD:
    @staticmethod
    async def create(db: AsyncSession, store: Store) -> Store:
        db.add(store)
        await db.flush()
        await db.refresh(store)
        return store

    @staticmethod
    async def get_by_id(db: AsyncSession, store_id: int) -> Store | None:
        result = await db.execute(select(Store).where(Store.id == store_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        marketplace: str | None = None,
        store_marketplace_id: str | None = None,  # store_id field on marketplace (not DB pk)
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100
    ) -> list[Store]:
        query = select(Store)
        if marketplace:
            query = query.where(Store.marketplace == marketplace)
        if store_marketplace_id:
            query = query.where(Store.store_id == store_marketplace_id)
        if is_active is not None:
            query = query.where(Store.is_active == is_active)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, store: Store, update_data: dict) -> Store:
        for key, value in update_data.items():
            setattr(store, key, value)
        await db.flush()
        await db.refresh(store)
        return store

    @staticmethod
    async def delete(db: AsyncSession, store_id: int) -> bool:
        store = await StoreCRUD.get_by_id(db, store_id)
        if store:
            await db.delete(store)
            return True
        return False


class PriceSnapshotCRUD:
    @staticmethod
    async def create(db: AsyncSession, snapshot: PriceSnapshot) -> PriceSnapshot:
        db.add(snapshot)
        await db.flush()
        await db.refresh(snapshot)
        return snapshot

    @staticmethod
    async def get_by_product(
        db: AsyncSession,
        product_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[PriceSnapshot]:
        result = await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product_id)
            .order_by(PriceSnapshot.snapshot_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_product_and_store(
        db: AsyncSession,
        product_id: int,
        store_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[PriceSnapshot]:
        result = await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product_id)
            .where(PriceSnapshot.store_id == store_id)
            .order_by(PriceSnapshot.snapshot_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_latest_by_product(
        db: AsyncSession,
        product_id: int
    ) -> list[PriceSnapshot]:
        # Subquery to get the latest snapshot per store
        from sqlalchemy import func
        subq = (
            select(
                PriceSnapshot.store_id,
                func.max(PriceSnapshot.snapshot_date).label("max_date")
            )
            .where(PriceSnapshot.product_id == product_id)
            .group_by(PriceSnapshot.store_id)
            .subquery()
        )
        result = await db.execute(
            select(PriceSnapshot)
            .join(subq, 
                  (PriceSnapshot.store_id == subq.c.store_id) &
                  (PriceSnapshot.snapshot_date == subq.c.max_date))
            .where(PriceSnapshot.product_id == product_id)
        )
        return result.scalars().all()


class CompetitorMappingCRUD:
    @staticmethod
    async def create(db: AsyncSession, mapping: CompetitorMapping) -> CompetitorMapping:
        db.add(mapping)
        await db.flush()
        await db.refresh(mapping)
        return mapping

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> list[CompetitorMapping]:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(CompetitorMapping)
            .options(
                selectinload(CompetitorMapping.reference_product),
                selectinload(CompetitorMapping.competitor_product)
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def delete(db: AsyncSession, mapping_id: int) -> bool:
        result = await db.execute(
            select(CompetitorMapping).where(CompetitorMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if mapping:
            await db.delete(mapping)
            return True
        return False


class MonitoredURLCRUD:
    """
    CRUD for monitored URLs — the core config table.
    Users register product URLs here so weekly scraping knows what to fetch.
    """

    @staticmethod
    async def create(db: AsyncSession, monitored_url: MonitoredURL) -> MonitoredURL:
        db.add(monitored_url)
        await db.flush()
        await db.refresh(monitored_url)
        return monitored_url

    @staticmethod
    async def get_by_id(db: AsyncSession, url_id: int) -> MonitoredURL | None:
        result = await db.execute(select(MonitoredURL).where(MonitoredURL.id == url_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        product_id: int | None = None,
        store_id: int | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 200
    ) -> list[MonitoredURL]:
        from sqlalchemy.orm import selectinload
        query = select(MonitoredURL).options(
            selectinload(MonitoredURL.product),
            selectinload(MonitoredURL.store),
        )
        if product_id is not None:
            query = query.where(MonitoredURL.product_id == product_id)
        if store_id is not None:
            query = query.where(MonitoredURL.store_id == store_id)
        if is_active is not None:
            query = query.where(MonitoredURL.is_active == is_active)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_active_urls(db: AsyncSession) -> list[MonitoredURL]:
        """Get all active monitored URLs for scheduled scraping."""
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(MonitoredURL)
            .options(
                selectinload(MonitoredURL.product),
                selectinload(MonitoredURL.store),
            )
            .where(MonitoredURL.is_active == True)
            .order_by(MonitoredURL.store_id)
        )
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, monitored_url: MonitoredURL, update_data: dict) -> MonitoredURL:
        for key, value in update_data.items():
            setattr(monitored_url, key, value)
        await db.flush()
        await db.refresh(monitored_url)
        return monitored_url

    @staticmethod
    async def mark_scraped(db: AsyncSession, url_id: int) -> None:
        """Update last_scraped_at timestamp."""
        from datetime import datetime
        result = await db.execute(select(MonitoredURL).where(MonitoredURL.id == url_id))
        murl = result.scalar_one_or_none()
        if murl:
            murl.last_scraped_at = datetime.utcnow()
            await db.flush()

    @staticmethod
    async def delete(db: AsyncSession, url_id: int) -> bool:
        result = await db.execute(select(MonitoredURL).where(MonitoredURL.id == url_id))
        murl = result.scalar_one_or_none()
        if murl:
            await db.delete(murl)
            return True
        return False
