from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class ScrapedPriceData(BaseModel):
    product_name: str
    product_sku: Optional[str]  # Will be matched later
    price: float
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    stock_status: Optional[str] = None
    product_url: str
    store_id: str
    store_name: str
    marketplace: str
    scraped_at: datetime = datetime.utcnow()


class BaseScraper(ABC):
    """Abstract base class for marketplace scrapers"""
    
    @abstractmethod
    async def scrape_product(
        self,
        product_query: str,
        store_id: str,
        **kwargs
    ) -> list[ScrapedPriceData]:
        """
        Scrape product data from a specific store on a marketplace.
        
        Args:
            product_query: Search query (product name/SKU)
            store_id: Store identifier on the marketplace
            **kwargs: Additional scraper-specific parameters
        
        Returns:
            List of ScrapedPriceData objects
        """
        pass
    
    @abstractmethod
    async def scrape_multiple_products(
        self,
        product_queries: list[str],
        store_id: str,
        **kwargs
    ) -> list[ScrapedPriceData]:
        """
        Scrape multiple products from a specific store.
        
        Args:
            product_queries: List of search queries
            store_id: Store identifier
            **kwargs: Additional scraper-specific parameters
        
        Returns:
            List of ScrapedPriceData objects
        """
        results = []
        for query in product_queries:
            items = await self.scrape_product(query, store_id, **kwargs)
            results.extend(items)
        return results
