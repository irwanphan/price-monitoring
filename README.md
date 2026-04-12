# Adata Price Monitor - Automated Marketplace Price Tracking

Automated marketplace price monitoring system for Adata distributors. Scrapes prices from multiple Indonesian marketplaces (Shopee, Tokopedia, Blibli, Lazada, TikTok), compares with competitor products, and generates weekly reports.

## Features

- **Multi-Marketplace Scraping**: Support for Shopee, Tokopedia, Blibli, Lazada, and TikTok
- **Store Whitelisting**: Scrape only from specific dealer stores (no need to scrape everything)
- **Price Validation**: Automatic anomaly detection to filter out fake/erroneous prices
- **Competitor Mapping**: Link Adata products with competitor equivalents (e.g., Adata S70 ↔ Team GM7000)
- **Automated Weekly Reports**: Scheduled scraping and report generation via Celery
- **Excel Export**: Generate comparison reports for headquarters
- **Real-time Dashboard API**: Query latest prices and market insights

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL (async via asyncpg)
- **Task Queue**: Celery + Redis
- **Scraping**: Playwright (browser automation) + Zyte API (optional)
- **Reports**: XlsxWriter

## Quick Start

### 1. Clone & Setup

```bash
cd Moonscope
cp .env.example .env
# Edit .env with your configuration (add ZYTE_API_KEY if using Zyte)
```

### 2. Run with Docker

```bash
docker-compose up -d
```

This starts:
- **API Server**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Celery Worker**: For scraping tasks
- **Celery Beat**: For scheduled tasks

### 3. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Usage Examples

### 1. Add Products to Track

```bash
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Adata",
    "name": "XPG SX8200 Pro 1TB NVMe SSD",
    "sku": "ASX8200PNP-1TT-C",
    "category": "SSD"
  }'
```

### 2. Add Competitor Product

```bash
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Team",
    "name": "MP33 1TB NVMe SSD",
    "sku": "T253TP0010M0E101",
    "category": "SSD"
  }'
```

### 3. Map Competitor Products

```bash
curl -X POST http://localhost:8000/api/v1/competitor-mappings/ \
  -H "Content-Type: application/json" \
  -d '{
    "reference_product_sku": "ASX8200PNP-1TT-C",
    "competitor_product_sku": "T253TP0010M0E101",
    "notes": "Direct competitor - 1TB NVMe Gen3"
  }'
```

### 4. Add Stores to Monitor

```bash
curl -X POST http://localhost:8000/api/v1/stores/ \
  -H "Content-Type: application/json" \
  -d '{
    "marketplace": "tokopedia",
    "store_id": "12345678",
    "store_name": "Adata Official Store"
  }'

curl -X POST http://localhost:8000/api/v1/stores/ \
  -H "Content-Type: application/json" \
  -d '{
    "marketplace": "shopee",
    "store_id": "87654321",
    "store_name": "Team Group Official"
  }'
```

### 5. Get Market Insights

```bash
# Get insights for a specific product
curl http://localhost:8000/api/v1/prices/insights/1?days=7

# Export Excel report
curl -o report.xlsx http://localhost:8000/api/v1/reports/price-comparison/excel?brand=Adata&days=7
```

### 6. Trigger Manual Scraping

```bash
# Via Celery task (from Python)
from app.tasks.scraping_tasks import run_weekly_scraping
run_weekly_scraping.delay()
```

## Project Structure

```
Moonscope/
├── app/
│   ├── api/                      # FastAPI routes
│   │   ├── products.py           # Product CRUD endpoints
│   │   ├── stores.py             # Store configuration endpoints
│   │   ├── prices.py             # Price history & insights
│   │   ├── competitor_mappings.py # Product competitor linking
│   │   └── reports.py            # Report generation
│   ├── core/
│   │   └── config.py             # Application settings
│   ├── db/
│   │   ├── database.py           # Database connection
│   │   └── models.py             # SQLAlchemy models
│   ├── scrapers/
│   │   ├── base.py               # Abstract scraper interface
│   │   ├── zyte_scraper.py       # Zyte API scraper
│   │   ├── playwright_scraper.py # Playwright browser scraper
│   │   └── orchestrator.py       # Multi-marketplace coordinator
│   ├── services/
│   │   ├── price_validation.py   # Anomaly detection
│   │   └── report_generator.py   # Excel report generation
│   └── tasks/
│       ├── celery_app.py         # Celery configuration
│       └── scraping_tasks.py     # Scheduled scraping tasks
├── main.py                       # FastAPI application entry
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker setup
├── Dockerfile                    # Container definition
└── .env.example                  # Environment template
```

## Scraper Implementation

The scraper framework is designed to be extensible. Two implementations are provided:

### Playwright Scraper (Default)
- Uses headless Chromium browser
- Good for JS-heavy marketplaces (Tokopedia, Shopee)
- Requires browser selectors to be implemented per marketplace

### Zyte Scraper (Optional)
- Uses Zyte's managed scraping infrastructure
- Handles proxies, CAPTCHAs, JS rendering automatically
- Requires ZYTE_API_KEY in `.env`

**To implement actual scraping logic**, update the scraper files with marketplace-specific selectors:

```python
# app/scrapers/playwright_scraper.py
# Example for Tokopedia:
products = await page.query_selector_all('.css-54b2en')
for product in products:
    name = await product.inner_text('.prd_link-product-name')
    price_text = await product.inner_text('.prd_link-product-price')
    price = float(price_text.replace('Rp', '').replace('.', '').strip())
    # ... create ScrapedPriceData objects
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@db:5432/price_monitor` |
| `REDIS_URL` | Redis connection for Celery | `redis://redis:6379/0` |
| `ZYTE_API_KEY` | Zyte API key (optional) | - |
| `SCRAPE_TIMEOUT` | Timeout per scrape (seconds) | `30` |
| `DEFAULT_PRICE_TOLERANCE` | Anomaly detection threshold | `0.3` (30%) |

### Scheduled Tasks

- **Weekly Scraping**: Monday 6:00 AM WIB
- **Daily Anomaly Check**: Every day 8:00 AM WIB

Customize in `app/tasks/celery_app.py`

## API Endpoints

### Products
- `POST /api/v1/products/` - Add product to track
- `GET /api/v1/products/` - List products (filter by `brand`, `category`)
- `GET /api/v1/products/{id}` - Get product details
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

### Stores
- `POST /api/v1/stores/` - Add store to monitor
- `GET /api/v1/stores/` - List stores (filter by `marketplace`)
- `PUT /api/v1/stores/{id}` - Update store
- `DELETE /api/v1/stores/{id}` - Delete store

### Competitor Mappings
- `POST /api/v1/competitor-mappings/` - Link products for comparison
- `GET /api/v1/competitor-mappings/` - List all mappings
- `DELETE /api/v1/competitor-mappings/{id}` - Remove mapping

### Prices
- `POST /api/v1/prices/` - Add price snapshot (manual or from scraper)
- `GET /api/v1/prices/product/{id}` - Get price history
- `GET /api/v1/prices/insights/{id}` - Get market insights (min/max/avg/median)

### Reports
- `GET /api/v1/reports/price-comparison/excel` - Download Excel report
- `GET /api/v1/reports/price-comparison/summary` - Get JSON summary

## Next Steps

1. **Implement Marketplace Selectors**: Update scraper files with actual CSS selectors for each marketplace
2. **Add Zyte Integration**: If using Zyte, configure extraction rules
3. **Set Up Email Reports**: Add automated email sending of weekly reports
4. **Add Frontend Dashboard**: Build a simple React/Vue dashboard for visualization
5. **Deploy to Production**: Use AWS/GCP/DigitalOcean with proper SSL and monitoring

## Troubleshooting

### Database connection issues
```bash
docker-compose down -v
docker-compose up -d
```

### Celery worker not running
```bash
docker-compose logs celery_worker
```

### Scraper timeouts
Increase `SCRAPE_TIMEOUT` in `.env` file

## License

Proprietary - Adata Distributor Internal Use
# price-monitoring
