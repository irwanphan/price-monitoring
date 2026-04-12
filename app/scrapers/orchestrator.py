from app.scrapers.zyte_scraper import ZyteScraper
from app.scrapers.playwright_scraper import PlaywrightScraper
from app.scrapers.base import BaseScraper, ScrapedPriceData
from app.core.config import settings
from typing import Optional


class ScraperFactory:
    """Factory to create appropriate scraper based on marketplace/config"""
    
    @staticmethod
    def get_scraper(
        marketplace: str,
        use_zyte: bool = False,
        **kwargs
    ) -> BaseScraper:
        """
        Get appropriate scraper for the marketplace.
        
        Args:
            marketplace: Target marketplace name
            use_zyte: Whether to use Zyte API (fallback to Playwright if False)
            **kwargs: Scraper-specific configuration
        
        Returns:
            Configured scraper instance
        """
        if use_zyte and settings.ZYTE_API_KEY:
            return ZyteScraper(**kwargs)
        
        # Default to Playwright for most marketplaces
        return PlaywrightScraper(**kwargs)


class ScraperOrchestrator:
    """
    Orchestrates scraping across multiple marketplaces and stores.
    This will be called by Celery tasks.
    """
    
    def __init__(self, use_zyte: bool = False):
        self.use_zyte = use_zyte
    
    async def scrape_all_stores(
        self,
        product_queries: list[str],
        stores: list[dict],  # [{marketplace, store_id, store_name}]
    ) -> list[ScrapedPriceData]:
        """
        Scrape products across all configured stores.
        
        Args:
            product_queries: List of product search queries
            stores: List of store configurations
        
        Returns:
            All scraped data combined
        """
        all_results = []
        
        for store in stores:
            marketplace = store["marketplace"]
            store_id = store["store_id"]
            
            scraper = ScraperFactory.get_scraper(
                marketplace,
                use_zyte=self.use_zyte
            )
            
            try:
                results = await scraper.scrape_multiple_products(
                    product_queries,
                    store_id,
                    marketplace=marketplace
                )
                all_results.extend(results)
                print(f"[ScraperOrchestrator] Scraped {len(results)} items from {marketplace}/{store_id}")
            except Exception as e:
                print(f"[ScraperOrchestrator] Failed to scrape {marketplace}/{store_id}: {e}")
                continue
        
        return all_results
