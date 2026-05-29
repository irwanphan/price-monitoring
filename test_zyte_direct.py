"""Test Zyte API with proper extraction for Tokopedia"""
import asyncio
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


async def test_zyte_direct():
    """Test Zyte API with direct HTTP request."""
    
    api_key = settings.ZYTE_API_KEY
    print(f"Testing Zyte API with key: {api_key[:10]}...")
    
    # Test URL - Tokopedia search for Adata products in specific store
    # Using the shop_domain parameter for store filtering
    test_urls = [
        "https://www.tokopedia.com/search?st=shop&q=adata%20sx8200&shop_domain=adata-xpg-id",
        "https://www.tokopedia.com/adata-xpg-id?ob=23",  # Store page sorted by newest
    ]
    
    async with httpx.AsyncClient(auth=(api_key, ""), timeout=60) as client:
        for url in test_urls:
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"{'='*60}")
            
            # Try with browserHtml only
            response = await client.post(
                "https://api.zyte.com/v1/extract",
                json={
                    "url": url,
                    "browserHtml": True,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                html = data.get("browserHtml", "")
                
                print(f"Status: {response.status_code}")
                print(f"browserHtml length: {len(html)}")
                
                # Save for inspection
                with open("/tmp/zyte_browser.html", "w") as f:
                    f.write(html)
                
                print("Saved to /tmp/zyte_browser.html")
                
                # Look for product patterns
                import re
                # Search for product links in browserHtml
                product_links = re.findall(
                    r'href="(/[^"]+?/[^"]+?)"',
                    html
                )
                # Filter for product-like URLs
                products = [l for l in product_links if l.count('/') == 2 and '/product/' not in l and '/search' not in l and '/category' not in l]
                print(f"Potential product links: {len(set(products))}")
                for p in set(products)[:5]:
                    print(f"  - {p}")
                
            else:
                print(f"Error: {response.status_code} - {response.text[:200]}")
    
    print("\n" + "="*60)
    print("Done")


if __name__ == "__main__":
    asyncio.run(test_zyte_direct())
