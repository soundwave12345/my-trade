# engine/populate_mib.py
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from db.database import SessionLocal
from db.models import Stock, Price, ApiUsage
from engine.data_collector import BUFFER_MINUTES

# Lista titoli FTSE MIB (con suffisso .MI)
FTSE_MIB_TICKERS = [
    "AMP.MI", "AZM.MI", "BAMI.MI", "BMPS.MI", "BZU.MI", "CPR.MI",
    "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "EXO.MI", "G.MI",
    "IG.MI", "INW.MI", "ISP.MI", "IT.MI", "JUVE.MI", "LDO.MI",
    "MB.MI", "MONC.MI", "NEXI.MI", "PIRC.MI", "PRY.MI", "REC.MI",
    "SFER.MI", "STLAM.MI", "STM.MI", "TEN.MI", "TRN.MI", "UCG.MI"
]

# Timeframes di interesse
TIMEFRAMES = ["1h", "6h", "1d", "1wk", "1mo"]

def store_bulk_data(df, interval, db: Session):
    """
    Salva i dati storici di tutti i titoli da un dataframe multi-index Yahoo
    """
    for ticker in df.columns.levels[1]:  # ogni ticker
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            stock = Stock(ticker=ticker)
            db.add(stock)
            db.commit()
            db.refresh(stock)

        ticker_df = df.xs(ticker, axis=1, level=1).copy()
        ticker_df.reset_index(inplace=True)
        ticker_df.rename(columns={
            "Datetime": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)

        for _, row in ticker_df.iterrows():
            timestamp_value = pd.to_datetime(row["timestamp"]).to_pydatetime()
            price = Price(
                stock_id=stock.id,
                timestamp=timestamp_value,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]) if not pd.isna(row["volume"]) else 0,
                interval=interval
            )
            db.merge(price)

        print(f"[{datetime.utcnow()}] Salvati {len(ticker_df)} record per {ticker} ({interval})")

    db.commit()

def populate_all():
    db = SessionLocal()

    for interval in TIMEFRAMES:
        print(f"[INFO] Scarico dati FTSE MIB (interval={interval}, period=max)")

        # Scarico in bulk per tutti i tickers
        df = yf.download(
            FTSE_MIB_TICKERS,
            interval=interval,
            period="max",
            group_by="ticker",
            auto_adjust=False,
            threads=True
        )

        if df.empty:
            print(f"[WARNING] Nessun dato scaricato per interval {interval}")
            continue

        # Salvo nel database
        store_bulk_data(df, interval, db)

        # Aggiorno contatore API
        today = datetime.utcnow().date()
        usage = db.query(ApiUsage).filter(ApiUsage.date == today).first()
        if not usage:
            usage = ApiUsage(date=today, count=0)
            db.add(usage)
        usage.count += 1
        db.commit()

    db.close()

if __name__ == "__main__":
    populate_all()
