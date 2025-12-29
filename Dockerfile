FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt ./

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy app sources
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
FROM python:3.11-slim

# Evitar prompts
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias (si hacen falta para pandas, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar ficheros de dependencias primero para aprovechar cache de docker
COPY requirements.txt ./
# Instalar solo dependencias de runtime (evitar paquetes de desarrollo que causan fallos)
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir \
       streamlit==1.52.2 \
       pandas==2.3.3 \
       filelock==3.12.2 \
       sentry-sdk==1.22.0

# Copiar el resto del proyecto
COPY . .

# Variables de entorno recomendadas
ENV LOG_LEVEL=INFO
ENV MAX_BACKUPS=5

# Exponer puerto default de Streamlit
EXPOSE 8501

# Ejecutar Streamlit
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true", "--server.enableCORS=false"]
