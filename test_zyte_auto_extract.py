"""Test Zyte Automatic Extraction for product pages"""
import asyncio
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


async def test_zyte_automatic_extraction():
    """
    Test Zyte's Automatic Extraction feature.
    This automatically extracts product data from e-commerce pages.
    """
    
    api_key = settings.ZYTE_API_KEY
    
    # Direct product URLs from Tokopedia
    # These are example URLs - we'll need to find real ones
    urls = [
        # Example Tokopedia product URL structure
        "https://www.tokopedia.com/adata-xpg-id/adata-xpg-sx8200-pro-1tb-nvme-m-2-ssd-gen3-read-3500mb-s-write-3000mb-s",
    ]
    
    async with httpx.AsyncClient(auth=(api_key, ""), timeout=60) as client:
        for url in urls:
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"{'='*60}")
            
            # Use automatic extraction (products, articles, etc.)
            response = await client.post(
                "https://api.zyte.com/v1/extract",
                json={
                    "url": url,
                    "httpResponseBody": True,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {response.status_code}")
                print(f"Keys in response: {list(data.keys())}")
                
                if "products" in data:
                    products = data["products"]
                    print(f"\nExtracted {len(products)} products:")
                    for p in products:
                        print(json.dumps(p, indent=2))
                else:
                    print("No products extracted automatically")
                    print("Available keys:", list(data.keys()))
                    
            else:
                print(f"Error: {response.status_code}")
                print(response.text[:500])
    
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(test_zyte_automatic_extraction())
