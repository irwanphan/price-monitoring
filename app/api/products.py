from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.db.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.crud import ProductCRUD

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if SKU already exists
    existing = await ProductCRUD.get_by_sku(db, product_data.sku)
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{product_data.sku}' already exists")
    
    product = Product(
        brand=product_data.brand,
        name=product_data.name,
        sku=product_data.sku,
        category=product_data.category,
        specifications=product_data.specifications
    )
    
    created = await ProductCRUD.create(db, product)
    return created


@router.get("/", response_model=list[ProductResponse])
async def get_products(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await ProductCRUD.get_all(db, brand=brand, category=category, is_active=is_active, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    product = await ProductCRUD.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    update_data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    product = await ProductCRUD.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    updated = await ProductCRUD.update(db, product, update_dict)
    return updated


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await ProductCRUD.delete(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return None
