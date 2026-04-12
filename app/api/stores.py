from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.db.models import Store
from app.schemas import StoreCreate, StoreResponse
from app.crud import StoreCRUD

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("/", response_model=StoreResponse, status_code=201)
async def create_store(
    store_data: StoreCreate,
    db: AsyncSession = Depends(get_db)
):
    store = Store(
        marketplace=store_data.marketplace.value,
        store_id=store_data.store_id,
        store_name=store_data.store_name
    )
    
    created = await StoreCRUD.create(db, store)
    return created


@router.get("/", response_model=list[StoreResponse])
async def get_stores(
    marketplace: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await StoreCRUD.get_all(db, marketplace=marketplace, is_active=is_active, skip=skip, limit=limit)


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: int,
    db: AsyncSession = Depends(get_db)
):
    store = await StoreCRUD.get_by_id(db, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    update_data: dict,
    db: AsyncSession = Depends(get_db)
):
    store = await StoreCRUD.get_by_id(db, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    updated = await StoreCRUD.update(db, store, update_data)
    return updated


@router.delete("/{store_id}", status_code=204)
async def delete_store(
    store_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await StoreCRUD.delete(db, store_id)
    if not success:
        raise HTTPException(status_code=404, detail="Store not found")
    return None
