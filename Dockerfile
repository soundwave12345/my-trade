# Dockerfile
FROM python:3.11-slim

WORKDIR /app

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
CMD ["sh", "-c", "python db/init_db.py && python engine/data_collector.py"]
