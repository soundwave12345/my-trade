# db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Path assoluto al DB nella cartella persistente
DB_PATH = os.getenv("DB_PATH", "data/trading.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
