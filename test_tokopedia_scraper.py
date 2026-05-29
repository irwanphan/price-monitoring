"""Test script to inspect Tokopedia HTML structure"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_tokopedia():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Search for Adata SSD on Tokopedia
        url = "https://www.tokopedia.com/search?q=adata%20sx8200%201tb&st=product"
        print(f"Visiting: {url}")
        
        await page.goto(url)
        await page.wait_for_timeout(3000)  # Wait for JS to load
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check if there are product cards
        print("\n--- Checking for product elements ---")
        
        # Common Tokopedia selectors to try
        selectors = [
            'a[data-testid="imgProduct"]',
            '.css-1b6h19w',  # Product card link
            'a[href*="/product/"]',
            '[data-testid="productItem"]',
            '.prd_link-product-name',
            '.css-1541v2k',  # Product title
            '[class*="CardStyled"]',
            'div[class*="product-card"]',
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✓ Found {len(elements)} elements with selector: {selector}")
                    # Get first element details
                    first = elements[0]
                    href = await first.get_attribute("href")
                    text = await first.inner_text()
                    print(f"  - href: {href[:100] if href else 'N/A'}")
                    print(f"  - text: {text[:100]}...")
            except Exception as e:
                print(f"✗ {selector}: {e}")
        
        # Try to get all links that look like product links
        print("\n--- Product links found ---")
        links = await page.query_selector_all('a[href*="/product/"]')
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute("href")
            text = await link.inner_text()
            print(f"{i+1}. {href}")
            print(f"   Title: {text[:80]}...")
        
        # Get the full HTML body to inspect structure
        print("\n--- Saving HTML for inspection ---")
        html = await page.content()
        with open("/tmp/tokopedia_test.html", "w") as f:
            f.write(html)
        print(f"Saved HTML to /tmp/tokopedia_test.html ({len(html)} bytes)")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_tokopedia())
