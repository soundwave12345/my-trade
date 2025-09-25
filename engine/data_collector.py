# engine/data_collector.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.database import SessionLocal, init_db
from db.models import Stock, Price, ApiUsage
from .validator import validate_volumes, validate_ohlc

print ("collector ok")
# Timeframe supportati: Yahoo -> [1m, 2m, 5m, 15m, 30m, 60m, 90m, 1d, 1wk, 1mo]
INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
    "6h": "360min",
    "1d": "1D",
    "1w": "1W",
    "1mo": "1M"
}

BUFFER_MINUTES = {
    "1h": 60,
    "6h": 120,
    "1d": 1440
}

def increment_api_counter(db: Session):
    today = datetime.utcnow().date()
    usage = db.query(ApiUsage).filter(ApiUsage.date == today).first()
    if not usage:
        usage = ApiUsage(date=today, count=0)
        db.add(usage)
    usage.count += 1
    db.commit()

def get_last_timestamp(db: Session, stock_id: int, interval: str):
    last_price = db.query(Price).filter(
        Price.stock_id == stock_id, Price.interval == interval
    ).order_by(Price.timestamp.desc()).first()
    return last_price.timestamp if last_price else None

def fetch_and_store_prices(ticker: str, interval: str = "1h", period="7d"):
    db = SessionLocal()

    # Recupera stock ID
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        stock = Stock(ticker=ticker)
        db.add(stock)
        db.commit()
        db.refresh(stock)

    # Buffer per validazione
    buffer_minutes = BUFFER_MINUTES.get(interval, 0)

    last_ts = get_last_timestamp(db, stock.id, interval)
    start_time = (last_ts - timedelta(minutes=buffer_minutes)) if last_ts else None

    # Chiamata API
    increment_api_counter(db)
    df = yf.download(ticker, interval=interval, period=period, start=start_time)
    df.reset_index(inplace=True)
    df.rename(columns={
        "Datetime": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    }, inplace=True)

    # Salva su DB
    for _, row in df.iterrows():
        price = Price(
            stock_id=stock.id,
            timestamp=row["timestamp"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            interval=interval
        )
        db.merge(price)
    db.commit()
    db.close()
    print(f"[{datetime.utcnow()}] Saved {len(df)} rows for {ticker} ({interval}).")
    
if __name__ == "__main__":
    import sys
    print("collector dentro")
    # Parametri: ticker, interval, period
    if len(sys.argv) != 4:
        print("Usage: python -m engine.data_collector <TICKER> <INTERVAL> <PERIOD>")
        print("Esempio: python -m engine.data_collector UCG.MI 1h 7d")
        sys.exit(1)

    ticker = sys.argv[1]
    interval = sys.argv[2]
    period = sys.argv[3]

    print(f"[INFO] Scarico dati di prova per {ticker} ({interval}, {period})")
    fetch_and_store_prices(ticker, interval=interval, period=period)
    print("[INFO] Fine scarico dati di prova.")
