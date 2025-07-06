# Dockerfile para BinDash Visualizer
FROM python:3.11-slim

# Información del contenedor
LABEL maintainer="FungiGT Team"
LABEL description="Servidor de visualización para resultados BinDash"
LABEL version="1.0.0"

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY server.py .

# Crear directorios necesarios
RUN mkdir -p uploads output temp

# Exponer puerto
EXPOSE 4008

# Variables de entorno
ENV FLASK_APP=server.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:4008/')" || exit 1

# Comando de inicio
CMD ["python", "server.py"] 