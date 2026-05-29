"""Test Zyte API scraping for Tokopedia Adata stores"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.scrapers.zyte_scraper import ZyteScraper
from app.core.config import settings


async def test_zyte_scraping():
    """Test scraping Adata products from Tokopedia stores."""
    
    print("=" * 60)
    print("ZYTE API SCRAPING TEST")
    print("=" * 60)
    print(f"API Key: {settings.ZYTE_API_KEY[:10]}... (masked)")
    print()
    
    scraper = ZyteScraper()
    
    # Target stores from user input
    stores = ["agresid", "adata-xpg-id"]
    
    # Product queries to search for
    queries = [
        "adata sx8200",
        "adata xpg",
        "adata ssd",
    ]
    
    for store in stores:
        print(f"\n{'='*40}")
        print(f"STORE: {store}")
        print(f"{'='*40}")
        
        for query in queries:
            print(f"\n  Query: '{query}'")
            results = await scraper.scrape_product(
                product_query=query,
                store_id=store,
                marketplace="tokopedia"
            )
            
            if results:
                print(f"  → Found {len(results)} products:")
                for item in results:
                    price_str = f"Rp {item.price:,.0f}" if item.price > 0 else "No price"
                    print(f"    - {item.product_name}: {price_str}")
                    if item.product_url:
                        print(f"      URL: {item.product_url}")
            else:
                print("  → No products found")
    
    await scraper.close()
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_zyte_scraping())
