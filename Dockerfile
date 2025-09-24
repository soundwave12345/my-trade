# Usa una versione leggera di Python
FROM python:3.11-slim

# Imposta la working directory
WORKDIR /app

# Copia file di dipendenze e installa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il progetto
COPY . .

# Espone la porta usata dall'app Flask
EXPOSE 5000

# Comando per avviare l'app
CMD ["python", "app.py"]
