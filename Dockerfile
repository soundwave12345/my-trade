# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Installa dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY . .

# Espone la porta usata dall'app Flask
EXPOSE 5002

# Creazione directory dati
RUN mkdir -p /app/data

# Volume per persistenza dati
VOLUME ["/app/data"]

# Comando di default: inizializza DB e avvia il servizio
CMD ["sh", "-c", "python -m db.init_db && python engine.data_collector UCG.MI 1h 7d"]
#CMD ["python", "db/init_db.py && python engine/data_collector.py"]
