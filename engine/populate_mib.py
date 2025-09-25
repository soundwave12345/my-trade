# engine/populate_mib.py
import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Stock, Price, ApiUsage
import time

# Timeframe supportati
INTERVALS = ["1m", "5m", "15m", "30m", "1h", "6h", "1d", "1w", "1mo"]

# Esempio tickers FTSE MIB (aggiornati e verificati)
FTSE_MIB_TICKERS = [
    "UCG.MI", "ENI.MI", "ISP.MI", "ENEL.MI", # "ATL.MI" rimosso - delisted
    "CNH.MI", "LUX.MI", "MONC.MI", "PIRC.MI", "PRY.MI",
    "STM.MI", "EXO.MI", "IT.MI", "A2A.MI", "AZM.MI",
    "MB.MI", "MS.MI", "SFER.MI", "SAF.MI", "TEN.MI",
    "TIT.MI", "TL.MI", "SCC.MI", "BMED.MI", "SRG.MI",
    "CSP.MI", "BAMI.MI", "MED.MI", "FE.MI", "FIAT.MI"
]

CHUNK_SIZE = 5  # scarica ticker in blocchi da 5 per volta

def increment_api_counter(db: Session):
    """Incrementa il contatore delle chiamate API"""
    today = datetime.utcnow().date()
    usage = db.query(ApiUsage).filter(ApiUsage.date == today).first()
    if not usage:
        usage = ApiUsage(date=today, count=0)
        db.add(usage)
    usage.count += 1
    db.commit()

def store_bulk_data(df, interval, db: Session):
    """Salva i dati bulk nel database, gestendo multi-ticker e ticker senza dati"""
    
    print(f"\n[DEBUG] Processing data for interval: {interval}")
    print(f"DataFrame type: {type(df)}")
    print(f"DataFrame shape: {df.shape}")
    
    # Gestisci il caso di DataFrame vuoto
    if df.empty:
        print(f"[WARNING] DataFrame vuoto per interval {interval}")
        return
    
    # Debug della struttura delle colonne PRIMA del reset_index
    print(f"Index name: {df.index.name}")
    print(f"Index type: {type(df.index)}")
    if hasattr(df.columns, 'levels'):
        print(f"Column levels: {len(df.columns.levels)}")
        if len(df.columns.levels) > 0:
            print(f"Level 0 (first 5): {list(df.columns.levels[0])[:5]}")
        if len(df.columns.levels) > 1:
            print(f"Level 1 (first 5): {list(df.columns.levels[1])[:5]}")
    else:
        print(f"Columns (first 10): {list(df.columns)[:10]}")
    
    # Reset index per avere timestamp come colonna
    df_reset = df.reset_index()
    
    print(f"[DEBUG] Dopo reset_index:")
    print(f"Columns dopo reset: {list(df_reset.columns)[:10]}")
    
    # Trova la colonna timestamp
    timestamp_col = None
    for col in df_reset.columns:
        col_name = col if isinstance(col, str) else str(col)
        if any(term in col_name.lower() for term in ['date', 'datetime', 'time']):
            timestamp_col = col
            break
    
    # Se non trovata, usa il primo elemento che non è una tupla
    if timestamp_col is None:
        for col in df_reset.columns:
            if not isinstance(col, tuple):
                timestamp_col = col
                break
    
    if timestamp_col is None:
        print(f"[ERROR] Impossibile trovare colonna timestamp")
        return
    
    print(f"[DEBUG] Usando come timestamp: {timestamp_col}")
    
    # Controlla se abbiamo multi-level columns
    has_multiindex_cols = any(isinstance(col, tuple) for col in df_reset.columns)
    
    if has_multiindex_cols:
        print(f"[INFO] Gestendo DataFrame multi-ticker")
        
        # Estrai tutti i ticker unici dalle colonne tuple
        tickers = set()
        for col in df_reset.columns:
            if isinstance(col, tuple) and len(col) == 2:
                ticker = col[0]
                tickers.add(ticker)
        
        print(f"[INFO] Ticker trovati: {list(tickers)}")
        
        # Processa ogni ticker
        for ticker in tickers:
            try:
                print(f"[INFO] Processando ticker: {ticker}")
                
                # Crea DataFrame per questo ticker
                ticker_data = {'timestamp': df_reset[timestamp_col]}
                
                # Cerca tutte le colonne per questo ticker
                for col in df_reset.columns:
                    if isinstance(col, tuple) and col[0] == ticker:
                        metric = col[1]  # Open, High, Low, Close, Volume
                        ticker_data[metric] = df_reset[col]
                
                # Verifica che abbiamo almeno alcune colonne essenziali
                if 'Close' not in ticker_data:
                    print(f"[WARNING] Ticker {ticker} senza dati Close, skip")
                    continue
                
                # Crea DataFrame per questo ticker
                ticker_df = pd.DataFrame(ticker_data)
                
                process_single_ticker(ticker_df, ticker, interval, db)
                
            except Exception as e:
                print(f"[ERROR] Errore processando ticker {ticker}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    else:
        # Caso singolo ticker senza multi-level
        print(f"[INFO] Gestendo singolo ticker")
        
        # Rinomina la colonna timestamp
        if timestamp_col != 'timestamp':
            df_reset = df_reset.rename(columns={timestamp_col: 'timestamp'})
        
        # Assumi che sia un singolo ticker (prendi il primo dal chunk corrente)
        ticker = "UNKNOWN"
        process_single_ticker(df_reset, ticker, interval, db)

def process_single_ticker(df, ticker, interval, db: Session):
    """Processa i dati di un singolo ticker"""
    
    # Rimuovi righe senza dati di chiusura
    if 'Close' not in df.columns:
        print(f"[WARNING] Colonna Close mancante per {ticker}")
        return
    
    df = df.dropna(subset=['Close'])
    
    if df.empty:
        print(f"[INFO] Nessun dato valido per {ticker}")
        return
    
    # Recupera o crea lo stock
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        stock = Stock(ticker=ticker)
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    # Salva i dati
    records_saved = 0
    for _, row in df.iterrows():
        try:
            # Converti timestamp
            if pd.isna(row['timestamp']):
                continue
                
            timestamp_value = pd.to_datetime(row['timestamp']).to_pydatetime()
            
            # Crea record Price
            price = Price(
                stock_id=stock.id,
                timestamp=timestamp_value,
                open=float(row.get('Open', 0)) if not pd.isna(row.get('Open', 0)) else 0,
                high=float(row.get('High', 0)) if not pd.isna(row.get('High', 0)) else 0,
                low=float(row.get('Low', 0)) if not pd.isna(row.get('Low', 0)) else 0,
                close=float(row['Close']),
                volume=int(row.get('Volume', 0)) if not pd.isna(row.get('Volume', 0)) else 0,
                interval=interval
            )
            
            db.merge(price)
            records_saved += 1
            
        except Exception as e:
            print(f"[ERROR] Errore salvando riga per {ticker}: {e}")
            continue
    
    try:
        db.commit()
        print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Salvati {records_saved} record per {ticker} ({interval})")
    except Exception as e:
        print(f"[ERROR] Errore commit per {ticker}: {e}")
        db.rollback()

def populate_all():
    """Popola tutti i dati FTSE MIB"""
    db = SessionLocal()
    
    try:
        for interval in INTERVALS:
            print(f"\n{'='*60}")
            print(f"[INFO] Scaricando dati FTSE MIB (interval={interval}, period=max)")
            print(f"{'='*60}")
            
            for i in range(0, len(FTSE_MIB_TICKERS), CHUNK_SIZE):
                chunk = FTSE_MIB_TICKERS[i:i+CHUNK_SIZE]
                
                print(f"[INFO] Processando chunk {i//CHUNK_SIZE + 1}: {chunk}")
                
                try:
                    # Download dati con retry logic
                    max_retries = 3
                    df = None
                    
                    for attempt in range(max_retries):
                        try:
                            print(f"[INFO] Tentativo {attempt + 1} di download per {chunk}")
                            df = yf.download(
                                tickers=chunk,
                                interval=interval,
                                period="max",
                                group_by="ticker",
                                auto_adjust=True,
                                prepost=True,
                                threads=True,
                                progress=False  # Disabilita progress bar per evitare spam
                            )
                            
                            # Controlla se il download è riuscito
                            if df is not None and not df.empty:
                                print(f"[SUCCESS] Download completato per chunk {chunk}")
                                break
                            else:
                                print(f"[WARNING] DataFrame vuoto per chunk {chunk}")
                                if attempt < max_retries - 1:
                                    time.sleep(2)
                                    continue
                                else:
                                    print(f"[ERROR] Tutti i tentativi falliti per chunk {chunk}")
                                    df = None
                                    break
                            
                        except Exception as download_error:
                            error_msg = str(download_error)
                            print(f"[WARNING] Tentativo {attempt + 1} fallito: {error_msg}")
                            
                            # Se è un errore di ticker delisted, non ritentare
                            if "delisted" in error_msg.lower() or "YFTzMissingError" in error_msg:
                                print(f"[INFO] Ticker probabilmente delisted in chunk {chunk}, continuo con i dati disponibili")
                                break
                            
                            if attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                            else:
                                print(f"[ERROR] Tutti i tentativi falliti per chunk {chunk}: {error_msg}")
                                df = None
                                break
                    
                    increment_api_counter(db)
                    
                    # Processa i dati se disponibili
                    if df is not None and not df.empty:
                        store_bulk_data(df, interval, db)
                    else:
                        print(f"[WARNING] Nessun dato da processare per chunk {chunk}")
                        
                    # Pausa tra i chunk per evitare rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"[ERROR] Errore scaricando chunk {chunk} ({interval}): {e}")
                    continue
            
            print(f"[INFO] Completato interval {interval}")
            
    except Exception as e:
        print(f"[ERROR] Errore generale: {e}")
    finally:
        db.close()
    
    print(f"\n{'='*60}")
    print("[INFO] Popolamento FTSE MIB completato.")
    print(f"{'='*60}")

if __name__ == "__main__":
    populate_all()