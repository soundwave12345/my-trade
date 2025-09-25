# engine/populate_mib.py
import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Stock, Price, ApiUsage

# Timeframe supportati
INTERVALS = ["1m", "5m", "15m", "30m", "1h", "6h", "1d", "1w", "1mo"]

# Esempio tickers FTSE MIB (aggiornare se necessario)
FTSE_MIB_TICKERS = [
    "UCG.MI", "ENI.MI", "ISP.MI", "ENEL.MI", "ATL.MI",
    "CNH.MI", "LUX.MI", "MONC.MI", "PIRC.MI", "PRY.MI",
    "STM.MI", "EXO.MI", "IT.MI", "A2A.MI", "AZM.MI",
    "MB.MI", "MS.MI", "SFER.MI", "SAF.MI", "TEN.MI",
    "TIT.MI", "TL.MI", "SCC.MI", "BMED.MI", "SRG.MI",
    "CSP.MI", "BAMI.MI", "MED.MI", "FE.MI", "FIAT.MI"
]

CHUNK_SIZE = 5  # scarica ticker in blocchi da 5 per volta

def increment_api_counter(db: Session):
    today = datetime.utcnow().date()
    usage = db.query(ApiUsage).filter(ApiUsage.date == today).first()
    if not usage:
        usage = ApiUsage(date=today, count=0)
        db.add(usage)
    usage.count += 1
    db.commit()

def store_bulk_data(df, interval, db: Session):
    print("\n[DEBUG] Structure of Yahoo Finance DataFrame")
    print("Type:", type(df))
    print("Index type:", type(df.index))
    print("Index name:", df.index.name)
    print("Columns:", df.columns)
    print("Shape:", df.shape)
    print("\nHead of the DataFrame:")
    print(df.head(10))  # prime 10 righe
    print("-" * 80)
    """Salva i dati bulk nel database, gestendo multi-ticker e ticker senza dati"""
    # Garantisce sempre la colonna timestamp
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={df.index.name or "index": "timestamp"})
    if "timestamp" not in df.columns:
        print(f"[WARNING] DataFrame senza timestamp per interval {interval}. Skip batch.")
        return


    # Ciclo sui ticker presenti
    tickers_in_df = df.columns.levels[1]
    for ticker in tickers_in_df:
        try:
            ticker_df = df.xs(ticker, axis=1, level=1, drop_level=False)
            ticker_df = ticker_df.dropna(subset=["Close"])
            if ticker_df.empty:
                print(f"[INFO] Nessun dato per {ticker}, skip.")
                continue

            # Recupera o crea lo stock
            stock = db.query(Stock).filter(Stock.ticker == ticker).first()
            if not stock:
                stock = Stock(ticker=ticker)
                db.add(stock)
                db.commit()
                db.refresh(stock)

            ticker_df.reset_index(inplace=True)
            for _, row in ticker_df.iterrows():
                timestamp_value = pd.to_datetime(row["timestamp"]).to_pydatetime()
                price = Price(
                    stock_id=stock.id,
                    timestamp=timestamp_value,
                    open=float(row[("Open", ticker)]),
                    high=float(row[("High", ticker)]),
                    low=float(row[("Low", ticker)]),
                    close=float(row[("Close", ticker)]),
                    volume=int(row[("Volume", ticker)]) if not pd.isna(row[("Volume", ticker)]) else 0,
                    interval=interval
                )
                db.merge(price)
            db.commit()
            print(f"[{datetime.utcnow()}] Salvati {len(ticker_df)} record per {ticker} ({interval})")
        except Exception as e:
            print(f"[ERROR] Problema con ticker {ticker}: {e}")

def populate_all():
    db = SessionLocal()
    for interval in INTERVALS:
        print(f"[INFO] Scarico dati FTSE MIB (interval={interval}, period=max)")
        for i in range(0, len(FTSE_MIB_TICKERS), CHUNK_SIZE):
            chunk = FTSE_MIB_TICKERS[i:i+CHUNK_SIZE]
            try:
                df = yf.download(chunk, interval=interval, period="max", group_by="ticker", auto_adjust=True)
                increment_api_counter(db)
                store_bulk_data(df, interval, db)
            except Exception as e:
                print(f"[ERROR] Problema download chunk {chunk} ({interval}): {e}")
    db.close()
    print("[INFO] Popolamento FTSE MIB completato.")

if __name__ == "__main__":
    populate_all()
