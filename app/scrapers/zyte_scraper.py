import httpx
import base64
from typing import Optional
from app.scrapers.base import BaseScraper, ScrapedPriceData
from app.core.config import settings


class ZyteScraper(BaseScraper):
    """
    Scraper using Zyte API automatic extraction for Tokopedia products.
    Works with individual product URLs (product detail pages).
    
    Zyte successfully extracts:
    - name, price, regularPrice (original price before discount)
    - description, additionalProperties (specs, stock, etc.)
    - aggregateRating, brand, breadcrumbs
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ZYTE_API_KEY
        if not self.api_key:
            raise ValueError("ZYTE_API_KEY is required")
        self.client = httpx.AsyncClient(
            auth=(self.api_key, ""),
            timeout=settings.SCRAPE_TIMEOUT
        )
    
    async def scrape_product_url(
        self,
        product_url: str,
        **kwargs
    ) -> Optional[ScrapedPriceData]:
        """
        Scrape a single Tokopedia product page using Zyte automatic extraction.
        
        Args:
            product_url: Full Tokopedia product URL (e.g., https://www.tokopedia.com/store/product-name-id)
        
        Returns:
            ScrapedPriceData or None if extraction failed
        """
        print(f"[ZyteScraper] Extracting: {product_url}")
        
        try:
            response = await self.client.post(
                "https://api.zyte.com/v1/extract",
                json={
                    "url": product_url,
                    "product": True,
                    "productOptions": {
                        "extractFrom": "browserHtml",
                    }
                }
            )
            
            if response.status_code != 200:
                print(f"[ZyteScraper] API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            product_data = data.get("product")
            
            if not product_data:
                print("[ZyteScraper] No product data in response")
                return None
            
            # Check confidence
            metadata = product_data.get("metadata", {})
            probability = metadata.get("probability", 0)
            if probability < 0.5:
                print(f"[ZyteScraper] Low confidence ({probability:.2%}), skipping")
                return None
            
            # Extract price (price is current, regularPrice is original)
            price = float(product_data.get("price", 0))
            regular_price = float(product_data.get("regularPrice", 0)) if product_data.get("regularPrice") else None
            
            # Calculate discount
            discount = None
            if regular_price and regular_price > price:
                discount = round(((regular_price - price) / regular_price) * 100, 2)
            
            # Extract stock from additionalProperties
            stock_status = "in_stock"
            for prop in product_data.get("additionalProperties", []):
                if prop.get("name") == "stok total":
                    stock_qty = int(prop.get("value", "0"))
                    stock_status = "in_stock" if stock_qty > 0 else "out_of_stock"
                    break
            
            # Extract store from URL
            url_parts = product_url.split("/")
            store_id = url_parts[3] if len(url_parts) > 3 else "unknown"
            
            return ScrapedPriceData(
                product_name=product_data.get("name", ""),
                product_sku=None,  # Can extract from URL or additionalProperties
                price=price,
                original_price=regular_price,
                discount_percentage=discount,
                stock_status=stock_status,
                product_url=product_url,
                store_id=store_id,
                store_name=store_id,
                marketplace="tokopedia",
            )
            
        except Exception as e:
            import traceback
            print(f"[ZyteScraper] Error: {e}")
            traceback.print_exc()
            return None
    
    async def scrape_product(
        self,
        product_query: str,
        store_id: str,
        marketplace: str = "tokopedia",
        **kwargs
    ) -> list[ScrapedPriceData]:
        """
        Scrape by searching for products on a Tokopedia store.
        Note: This requires the product URLs to be provided via search.
        For now, this builds a search URL that user needs to manually collect from.
        """
        search_url = f"https://www.tokopedia.com/search?st=shop&q={product_query}&shop_domain={store_id}"
        print(f"[ZyteScraper] Search URL (manual): {search_url}")
        print("[ZyteScraper] Note: Use scrape_product_urls() with collected product URLs instead")
        return []
    
    async def scrape_product_urls(
        self,
        product_urls: list[str],
    ) -> list[ScrapedPriceData]:
        """
        Scrape multiple product URLs concurrently.
        
        Args:
            product_urls: List of full Tokopedia product URLs
        
        Returns:
            List of successfully scraped products
        """
        print(f"[ZyteScraper] Scraping {len(product_urls)} products...")
        
        results = []
        for url in product_urls:
            item = await self.scrape_product_url(url)
            if item:
                results.append(item)
                price_str = f"Rp {item.price:,.0f}"
                discount_str = f" ({item.discount_percentage}% off)" if item.discount_percentage else ""
                print(f"  ✓ {item.product_name[:50]}...: {price_str}{discount_str}")
        
        print(f"[ZyteScraper] Successfully scraped {len(results)}/{len(product_urls)} products")
        return results
    
    async def scrape_multiple_products(
        self,
        product_queries: list[str],
        store_id: str,
        marketplace: str = "tokopedia",
        **kwargs
    ) -> list[ScrapedPriceData]:
        """
        Backwards compatibility - delegates to scrape_product_urls.
        Accepts product URLs as product_queries.
        """
        return await self.scrape_product_urls(product_queries)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
