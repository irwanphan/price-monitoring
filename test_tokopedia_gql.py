"""Test Tokopedia GraphQL API directly"""
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


async def test_tokopedia_graphql():
    """
    Test Tokopedia's internal GraphQL API.
    This is much faster and more reliable than HTML scraping.
    """
    
    # Tokopedia GraphQL endpoint
    gql_url = "https://gql.tokopedia.com/"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Origin": "https://www.tokopedia.com",
        "Referer": "https://www.tokopedia.com/",
    }
    
    # Query to search products in a specific store
    # This uses Tokopedia's internal search query
    search_query = {
        "operationName": "ProductSearchQueryPaginated",
        "variables": {
            "params": {
                "shop_domain": "adata-xpg-id",
                "q": "ssd",
                "st": "shop",
                "ob": 23,  # Sort by newest
                "page": 1,
                "rows": 20,
            }
        },
        "query": """
        query ProductSearchQueryPaginated($params: SearchQueryParams!) {
          searchV2(params: $params) {
            products {
              title
              price {
                integer
              }
              originalPrice {
                integer
              }
              discountPercentage
              image {
                url
              }
              url
              rating
              countReview
              shop {
                name
                location
                isOfficial
              }
            }
            totalData
          }
        }
        """
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("Testing Tokopedia GraphQL API...")
        print(f"Querying store: adata-xpg-id, search: ssd\n")
        
        response = await client.post(gql_url, json=search_query, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for errors
            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                return
            
            # Navigate the response structure
            print(json.dumps(data, indent=2)[:2000])
        else:
            print(f"Response: {response.text[:500]}")
    
    print("\nDone")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tokopedia_graphql())
