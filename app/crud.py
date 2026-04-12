from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Product, Store, PriceSnapshot, CompetitorMapping


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
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100
    ) -> list[Store]:
        query = select(Store)
        if marketplace:
            query = query.where(Store.marketplace == marketplace)
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
