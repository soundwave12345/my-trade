# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, nullable=False)
    name = Column(String)

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    interval = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("stock_id", "timestamp", "interval", name="uix_price"),)

class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    count = Column(Integer, default=0)
