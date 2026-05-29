from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# Enums
class MarketplaceEnum(str, Enum):
    SHOPEE = "shopee"
    TOKOPEDIA = "tokopedia"
    BLIBLI = "blibli"
    LAZADA = "lazada"
    TIKTOK = "tiktok"


class StockStatusEnum(str, Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"


# Product Schemas
class ProductCreate(BaseModel):
    brand: str = Field(..., example="Adata")
    name: str = Field(..., example="XPG SX8200 Pro 1TB NVMe SSD")
    sku: str = Field(..., example="ASX8200PNP-1TT-C")
    category: Optional[str] = Field(None, example="SSD")
    specifications: Optional[str] = Field(None, description="JSON string of specifications")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    specifications: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    brand: str
    name: str
    sku: str
    category: Optional[str]
    specifications: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Store Schemas
class StoreCreate(BaseModel):
    marketplace: MarketplaceEnum
    store_id: str = Field(..., example="12345678")
    store_name: str = Field(..., example="Adata Official Store")


class StoreResponse(BaseModel):
    id: int
    marketplace: str
    store_id: str
    store_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Competitor Mapping Schemas
class CompetitorMappingCreate(BaseModel):
    reference_product_sku: str = Field(..., description="SKU of the reference product (e.g., Adata)")
    competitor_product_sku: str = Field(..., description="SKU of the competitor product (e.g., Team)")
    notes: Optional[str] = None


class CompetitorMappingResponse(BaseModel):
    id: int
    reference_product_id: int
    competitor_product_id: int
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Price Snapshot Schemas
class PriceSnapshotResponse(BaseModel):
    id: int
    product_id: int
    store_id: int
    marketplace: str
    price: float
    original_price: Optional[float]
    discount_percentage: Optional[float]
    stock_status: Optional[str]
    product_url: Optional[str]
    is_valid: bool
    anomaly_reason: Optional[str]
    snapshot_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PriceSnapshotCreate(BaseModel):
    product_sku: str
    marketplace: MarketplaceEnum
    store_id: int
    price: float
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    stock_status: Optional[StockStatusEnum] = None
    product_url: Optional[str] = None
    snapshot_date: Optional[datetime] = None


# Report Schemas
class PriceComparisonReport(BaseModel):
    reference_product: ProductResponse
    competitor_prices: list
    our_prices: list
    lowest_price: float
    highest_price: float
    average_price: float
    our_position: str  # "lowest", "middle", "highest"


class MarketInsight(BaseModel):
    product_name: str
    total_listings: int
    price_range: dict
    average_price: float
    median_price: float
    cheapest_store: str
    most_expensive_store: str
    anomaly_count: int


# Scrape Schemas
class ProductURL(BaseModel):
    """Single product URL to scrape"""
    url: str = Field(..., example="https://www.tokopedia.com/adata-xpg-id/product-name-xxx")
    product_sku: Optional[str] = Field(None, description="SKU to match with tracked product")


class BulkScrapeRequest(BaseModel):
    """Request to scrape multiple product URLs"""
    urls: list[ProductURL] = Field(..., min_length=1, max_length=100)
    marketplace: str = Field(default="tokopedia", example="tokopedia")


class ScrapedProductResponse(BaseModel):
    """Single scraped product result"""
    product_name: str
    product_sku: Optional[str]
    price: float
    original_price: Optional[float]
    discount_percentage: Optional[float]
    stock_status: Optional[str]
    product_url: str
    store_id: str
    store_name: str
    marketplace: str


class BulkScrapeResponse(BaseModel):
    """Response from bulk scraping"""
    total_requested: int
    total_success: int
    total_failed: int
    results: list[ScrapedProductResponse]


# Monitored URL Schemas
class MonitoredURLCreate(BaseModel):
    """Register a product URL to monitor (for weekly scraping)."""
    product_id: int = Field(..., description="DB ID of the product to track")
    store_id: int = Field(..., description="DB ID of the store")
    url: str = Field(..., example="https://www.tokopedia.com/adata-xpg-id/product-name-xxx")
    label: Optional[str] = Field(None, example="Adata XPG S70 Blade 1TB - Tokopedia")


class MonitoredURLUpdate(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None
    url: Optional[str] = None


class MonitoredURLResponse(BaseModel):
    id: int
    product_id: int
    store_id: int
    url: str
    label: Optional[str]
    is_active: bool
    last_scraped_at: Optional[datetime]
    created_at: datetime
    # Nested info
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    store_name: Optional[str] = None
    marketplace: Optional[str] = None

    class Config:
        from_attributes = True


class BulkMonitoredURLCreate(BaseModel):
    """Register multiple URLs at once."""
    urls: list[MonitoredURLCreate] = Field(..., min_length=1, max_length=200)
