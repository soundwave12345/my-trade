# engine/validator.py
import pandas as pd

def validate_volumes(df_small: pd.DataFrame, df_large: pd.DataFrame, small_interval: str, large_interval: str):
    """
    Verifica che la somma dei volumi del timeframe minore corrisponda
    ai volumi registrati nel timeframe maggiore.
    """
    grouped = df_small.resample(large_interval, on='timestamp').agg({'volume': 'sum'})
    merged = pd.merge(grouped, df_large[['timestamp', 'volume']], on='timestamp', suffixes=('_small', '_large'))

    errors = merged[abs(merged['volume_small'] - merged['volume_large']) > 1e-3]
    return errors

def validate_ohlc(df_small: pd.DataFrame, df_large: pd.DataFrame, large_interval: str):
    """
    Verifica che aperture/chiusure siano coerenti.
    """
    grouped = df_small.resample(large_interval, on='timestamp').agg({
        'open': 'first',
        'close': 'last'
    })
    merged = pd.merge(grouped, df_large[['timestamp', 'open', 'close']], on='timestamp', suffixes=('_small', '_large'))

    errors = merged[(abs(merged['open_small'] - merged['open_large']) > 1e-3) |
                    (abs(merged['close_small'] - merged['close_large']) > 1e-3)]
    return errors
