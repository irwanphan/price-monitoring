from app.scrapers.zyte_scraper import ZyteScraper
from app.scrapers.base import ScrapedPriceData
from typing import Optional


class ScraperOrchestrator:
    """
    Orchestrates scraping of Tokopedia product URLs using Zyte API.
    
    Workflow:
    1. User provides list of product URLs to monitor
    2. Orchestrator scrapes all URLs via Zyte
    3. Returns structured price data for storage
    
    Note: Tokopedia store pages don't expose product lists via HTML.
    Users need to manually collect product URLs from store pages
    (visit tokopedia.com/store-name, copy product URLs).
    """
    
    def __init__(self, use_zyte: bool = True):
        self.use_zyte = use_zyte
    
    async def scrape_product_urls(
        self,
        product_urls: list[str],
    ) -> list[ScrapedPriceData]:
        """
        Scrape multiple Tokopedia product URLs.
        
        Args:
            product_urls: List of full Tokopedia product URLs
        
        Returns:
            All scraped data
        """
        if self.use_zyte:
            scraper = ZyteScraper()
            try:
                results = await scraper.scrape_product_urls(product_urls)
                return results
            finally:
                await scraper.close()
        
        return []
    
    async def scrape_by_store(
        self,
        store_urls: dict[str, list[str]],
    ) -> list[ScrapedPriceData]:
        """
        Scrape products grouped by store.
        
        Args:
            store_urls: {store_name: [url1, url2, ...]}
        
        Returns:
            All scraped data combined
        """
        all_results = []
        
        for store_name, urls in store_urls.items():
            print(f"[Orchestrator] Scraping {len(urls)} products from {store_name}...")
            results = await self.scrape_product_urls(urls)
            all_results.extend(results)
            print(f"[Orchestrator] Got {len(results)} results from {store_name}")
        
        return all_results
