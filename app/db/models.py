from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(50), nullable=False, index=True)  # Adata, Team, Kingston, etc.
    name = Column(String(255), nullable=False)  # Full product name
    sku = Column(String(100), unique=True, index=True)  # Unique SKU identifier
    category = Column(String(50), index=True)  # SSD, RAM, PSU, etc.
    specifications = Column(Text, nullable=True)  # JSON string of specs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    price_snapshots = relationship("PriceSnapshot", back_populates="product")
    monitored_urls = relationship("MonitoredURL", back_populates="product")
    competitor_mappings_as_target = relationship(
        "CompetitorMapping",
        foreign_keys="CompetitorMapping.competitor_product_id",
        back_populates="competitor_product"
    )
    competitor_mappings_as_reference = relationship(
        "CompetitorMapping",
        foreign_keys="CompetitorMapping.reference_product_id",
        back_populates="reference_product"
    )


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False, index=True)  # shopee, tokopedia, blibli, lazada, tiktok
    store_id = Column(String(100), nullable=False)  # Store identifier on marketplace
    store_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    price_snapshots = relationship("PriceSnapshot", back_populates="store")
    monitored_urls = relationship("MonitoredURL", back_populates="store")


class CompetitorMapping(Base):
    __tablename__ = "competitor_mappings"

    id = Column(Integer, primary_key=True, index=True)
    reference_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    competitor_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reference_product = relationship(
        "Product",
        foreign_keys=[reference_product_id],
        back_populates="competitor_mappings_as_reference"
    )
    competitor_product = relationship(
        "Product",
        foreign_keys=[competitor_product_id],
        back_populates="competitor_mappings_as_target"
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("idx_product_store_date", "product_id", "store_id", "snapshot_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    marketplace = Column(String(50), nullable=False, index=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)  # Before discount
    discount_percentage = Column(Float, nullable=True)
    stock_status = Column(String(20), nullable=True)  # in_stock, out_of_stock, preorder
    product_url = Column(Text, nullable=True)
    is_valid = Column(Boolean, default=True)  # Passed validation checks
    anomaly_reason = Column(Text, nullable=True)  # Why it was flagged if invalid
    snapshot_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="price_snapshots")
    store = relationship("Store", back_populates="price_snapshots")


class MonitoredURL(Base):
    """
    Stores product URLs to be scraped automatically.
    This is the core config table: user registers which URLs to monitor
    for which product on which store, so weekly scraping knows what to fetch.
    """
    __tablename__ = "monitored_urls"
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", "url", name="uq_product_store_url"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)  # Full marketplace product URL
    label = Column(String(255), nullable=True)  # Optional human label e.g. "Tokopedia Adata S70 1TB"
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)  # Last time this URL was scraped
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="monitored_urls")
    store = relationship("Store", back_populates="monitored_urls")
