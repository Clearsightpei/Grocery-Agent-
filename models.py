"""
SQLAlchemy ORM Models for AI Grocery Agent Database

Tables:
- stores: Physical grocery store locations
- ingredients: Available ingredients with categories
- prices: Current prices (latest price for each ingredient at each store)
- price_history: Historical prices for analytics
- cache_metadata: Track cache freshness and data sources
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, 
    Numeric, Index, UniqueConstraint, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

Base = declarative_base()


class Store(Base):
    """Physical grocery store with location"""
    __tablename__ = 'stores'
    __table_args__ = {'schema': 'grocery'}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    chain = Column(String(100), nullable=False)  # e.g., "Trader Joe's", "Safeway"
    address = Column(String(500), nullable=False)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(10))
    phone = Column(String(20))
    latitude = Column(Numeric(10, 8))  # Geographical coordinates
    longitude = Column(Numeric(11, 8))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = relationship("Price", back_populates="store", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="store", cascade="all, delete-orphan")
    cache_metadata = relationship("CacheMetadata", back_populates="store", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Store {self.name}>"


class Ingredient(Base):
    """Available ingredients with categories and units"""
    __tablename__ = 'ingredients'
    __table_args__ = {'schema': 'grocery'}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)  # Normalized to lowercase
    category = Column(String(100), nullable=False)  # e.g., "produce", "meat", "dairy", "pantry"
    unit = Column(String(50), nullable=False)  # e.g., "lb", "oz", "each", "liter"
    avg_price = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = relationship("Price", back_populates="ingredient", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="ingredient", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Ingredient {self.name}>"


class Price(Base):
    """Current prices (latest price for each ingredient at each store)"""
    __tablename__ = 'prices'
    __table_args__ = (
        UniqueConstraint('ingredient_id', 'store_id', name='unique_ingredient_store'),
        Index('idx_ingredient_id', 'ingredient_id'),
        Index('idx_store_id', 'store_id'),
        Index('idx_in_stock', 'in_stock'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_store_in_stock', 'store_id', 'in_stock'),
        {'schema': 'grocery'}
    )
    
    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('grocery.ingredients.id'), nullable=False)
    store_id = Column(Integer, ForeignKey('grocery.stores.id'), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    in_stock = Column(Boolean, default=True)
    last_verified = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Cache expiration time
    
    # Relationships
    ingredient = relationship("Ingredient", back_populates="prices")
    store = relationship("Store", back_populates="prices")
    
    def __repr__(self):
        return f"<Price {self.ingredient.name} @ {self.store.name}: ${self.price}>"


class PriceHistory(Base):
    """Historical prices for analytics and price trends"""
    __tablename__ = 'price_history'
    __table_args__ = (
        Index('idx_ingredient_store', 'ingredient_id', 'store_id'),
        Index('idx_recorded_at', 'recorded_at'),
        Index('idx_source', 'source'),
        {'schema': 'grocery'}
    )
    
    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('grocery.ingredients.id'), nullable=False)
    store_id = Column(Integer, ForeignKey('grocery.stores.id'), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    in_stock = Column(Boolean, default=True)
    source = Column(String(50))  # 'api', 'mock', 'cache'
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ingredient = relationship("Ingredient", back_populates="price_history")
    store = relationship("Store", back_populates="price_history")
    
    def __repr__(self):
        return f"<PriceHistory {self.ingredient.name} @ {self.store.name}: ${self.price}>"


class CacheMetadata(Base):
    """Track when data was fetched and cache validity"""
    __tablename__ = 'cache_metadata'
    __table_args__ = (
        Index('idx_store_id', 'store_id'),
        Index('idx_next_refresh', 'next_refresh_at'),
        {'schema': 'grocery'}
    )
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('grocery.stores.id'), nullable=True)
    last_fetch_time = Column(DateTime)
    coverage_percentage = Column(Integer)  # % of all ingredients in stock
    data_source = Column(String(50))  # 'api', 'mock'
    next_refresh_at = Column(DateTime)
    
    # Relationships
    store = relationship("Store", back_populates="cache_metadata")
    
    def __repr__(self):
        return f"<CacheMetadata store_id={self.store_id}, coverage={self.coverage_percentage}%>"


if __name__ == "__main__":
    # Test model creation
    from sqlalchemy import inspect
    
    print("SQLAlchemy ORM Models:")
    print(f"- Store: {Store.__tablename__}")
    print(f"- Ingredient: {Ingredient.__tablename__}")
    print(f"- Price: {Price.__tablename__}")
    print(f"- PriceHistory: {PriceHistory.__tablename__}")
    print(f"- CacheMetadata: {CacheMetadata.__tablename__}")
