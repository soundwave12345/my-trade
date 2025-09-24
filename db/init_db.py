# db/init_db.py
import os
from .database import Base, engine, DB_PATH
from .models import Stock, Price, ApiUsage

def init_db():
    """
    Inizializza il database SQLite solo se non esiste già.
    """
    if not os.path.exists(DB_PATH):
        print(f"[INFO] Database non trovato, creazione nuovo DB: {DB_PATH}")
        # Creazione directory se non esiste
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Creazione schema tabelle
        Base.metadata.create_all(bind=engine)
        print("[INFO] Database creato con successo.")
    else:
        print(f"[INFO] Database già esistente, nessuna modifica: {DB_PATH}")

if __name__ == "__main__":
    init_db()
