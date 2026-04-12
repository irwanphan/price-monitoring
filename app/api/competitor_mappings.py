from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import CompetitorMapping
from app.schemas import CompetitorMappingCreate, CompetitorMappingResponse
from app.crud import CompetitorMappingCRUD, ProductCRUD

router = APIRouter(prefix="/competitor-mappings", tags=["competitor-mappings"])


@router.post("/", response_model=CompetitorMappingResponse, status_code=201)
async def create_competitor_mapping(
    mapping_data: CompetitorMappingCreate,
    db: AsyncSession = Depends(get_db)
):
    # Get products by SKU
    ref_product = await ProductCRUD.get_by_sku(db, mapping_data.reference_product_sku)
    if not ref_product:
        raise HTTPException(
            status_code=404,
            detail=f"Reference product with SKU '{mapping_data.reference_product_sku}' not found"
        )
    
    comp_product = await ProductCRUD.get_by_sku(db, mapping_data.competitor_product_sku)
    if not comp_product:
        raise HTTPException(
            status_code=404,
            detail=f"Competitor product with SKU '{mapping_data.competitor_product_sku}' not found"
        )
    
    mapping = CompetitorMapping(
        reference_product_id=ref_product.id,
        competitor_product_id=comp_product.id,
        notes=mapping_data.notes
    )
    
    created = await CompetitorMappingCRUD.create(db, mapping)
    return created


@router.get("/", response_model=list[CompetitorMappingResponse])
async def get_competitor_mappings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    return await CompetitorMappingCRUD.get_all(db, skip=skip, limit=limit)


@router.delete("/{mapping_id}", status_code=204)
async def delete_competitor_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await CompetitorMappingCRUD.delete(db, mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return None
