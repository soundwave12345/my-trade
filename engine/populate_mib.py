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


def store_bulk_data(df, interval, db):
    """
    Salva i dati bulk nel database, gestendo i multi-ticker di yfinance.
    """
    # Se il timestamp è nell'indice, lo portiamo a colonna
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    # Rinomina la colonna "Datetime" in "timestamp" se presente
    if "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "timestamp"})

    # Ciclo su tutte le righe
    for _, row in df.iterrows():
        timestamp_value = pd.to_datetime(row["timestamp"]).to_pydatetime()

        # Estraggo i dati per ogni ticker
        for ticker in df.columns.levels[1]:
            try:
                adj_close = row[("Adj Close", ticker)]
                close = row[("Close", ticker)]
                open_price = row[("Open", ticker)]
                high = row[("High", ticker)]
                low = row[("Low", ticker)]
                volume = row[("Volume", ticker)]

                # Salva nel database
                db.add_price(
                    ticker=ticker,
                    timestamp=timestamp_value,
                    interval=interval,
                    open_price=open_price,
                    high=high,
                    low=low,
                    close=close,
                    adj_close=adj_close,
                    volume=volume,
                )
            except KeyError:
                # Il ticker potrebbe non avere dati completi
                continue


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
