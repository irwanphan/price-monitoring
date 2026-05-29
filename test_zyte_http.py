"""Test Zyte API with httpResponseBody (no browser)"""
import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


async def test_zyte_http():
    """Test Zyte API with httpResponseBody (faster, no browser)."""
    
    api_key = settings.ZYTE_API_KEY
    
    # Tokopedia store URLs
    urls = [
        "https://www.tokopedia.com/adata-xpg-id",
    ]
    
    async with httpx.AsyncClient(auth=(api_key, ""), timeout=30) as client:
        for url in urls:
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"{'='*60}")
            
            # Use httpResponseBody (no browser rendering - faster)
            response = await client.post(
                "https://api.zyte.com/v1/extract",
                json={
                    "url": url,
                    "httpResponseBody": True,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                body = data.get("httpResponseBody", "")
                
                # It's base64 encoded
                import base64
                try:
                    decoded = base64.b64decode(body).decode('utf-8')
                except:
                    decoded = body
                
                print(f"Status: {response.status_code}")
                print(f"Response length: {len(decoded)}")
                
                with open("/tmp/zyte_http.html", "w") as f:
                    f.write(decoded)
                
                print("Saved to /tmp/zyte_http.html")
                
                # Look for product links
                import re
                links = re.findall(r'href="(/[^"]+?)"', decoded)
                product_links = [l for l in links if l.count('/') == 2 and '/product/' not in l]
                print(f"Found {len(set(product_links))} potential store/product links")
                for l in set(product_links)[:10]:
                    print(f"  - {l}")
                
            else:
                print(f"Error: {response.status_code} - {response.text[:300]}")
    
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(test_zyte_http())
