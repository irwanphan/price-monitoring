"""Test Zyte API with ecommerce extraction and longer timeout"""
import asyncio
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


async def test_zyte_ecommerce():
    """Test Zyte API with ecommerce extraction."""
    
    api_key = settings.ZYTE_API_KEY
    
    # Test URLs
    urls = [
        "https://www.tokopedia.com/adata-xpg-id",
    ]
    
    async with httpx.AsyncClient(auth=(api_key, ""), timeout=120) as client:
        for url in urls:
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"{'='*60}")
            
            # Use Zyte's automatic extraction (no browserHtml - uses their ML models)
            response = await client.post(
                "https://api.zyte.com/v1/extract",
                json={
                    "url": url,
                    "httpResponseBody": True,
                    "browserHtml": True,
                    "javascript": True,  # Enable JS rendering
                    "actions": [
                        {"action": "waitForSelector", "selector": "body", "timeout": 30000}
                    ]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {response.status_code}")
                print(f"Keys: {list(data.keys())}")
                
                if "browserHtml" in data:
                    html = data["browserHtml"]
                    print(f"browserHtml length: {len(html)}")
                    
                    with open("/tmp/zyte_js_rendered.html", "w") as f:
                        f.write(html)
                    print("Saved to /tmp/zyte_js_rendered.html")
                
                if "products" in data:
                    products = data["products"]
                    print(f"Extracted {len(products)} products:")
                    for p in products[:5]:
                        print(f"  - {p.get('name')}: {p.get('price')}")
                
            else:
                print(f"Error: {response.status_code}")
                print(response.text[:500])
    
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(test_zyte_ecommerce())
