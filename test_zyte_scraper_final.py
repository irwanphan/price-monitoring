"""Test Zyte scraper with confirmed working Tokopedia product URL"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.scrapers.zyte_scraper import ZyteScraper


async def test_zyte_scraper():
    """Test the updated ZyteScraper with real Tokopedia product URL."""
    
    print("=" * 60)
    print("ZYTE SCRAPER TEST - TOKOPEDIA PRODUCT PAGE")
    print("=" * 60)
    
    scraper = ZyteScraper()
    
    # Confirmed working URL from playground test
    test_urls = [
        "https://www.tokopedia.com/adata-xpg-id/adata-xpg-gammix-s70-blade-ssd-nvme-gen4-512gb-1731346947923019212",
    ]
    
    print(f"\nTesting {len(test_urls)} product(s)...\n")
    
    results = await scraper.scrape_product_urls(test_urls)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for item in results:
        print(f"\nProduct: {item.product_name}")
        print(f"  Price: Rp {item.price:,.0f}")
        if item.original_price:
            print(f"  Original Price: Rp {item.original_price:,.0f}")
        if item.discount_percentage:
            print(f"  Discount: {item.discount_percentage}%")
        print(f"  Stock: {item.stock_status}")
        print(f"  Store: {item.store_id}")
        print(f"  Marketplace: {item.marketplace}")
        print(f"  URL: {item.product_url}")
    
    print(f"\n{'='*60}")
    print(f"Test Complete: {len(results)}/{len(test_urls)} products scraped")
    print("=" * 60)
    
    await scraper.close()


if __name__ == "__main__":
    asyncio.run(test_zyte_scraper())
