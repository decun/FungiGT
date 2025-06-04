FROM node:18-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Descargar datasets CLI de NCBI
RUN curl -o /usr/local/bin/datasets 'https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets' \
    && chmod +x /usr/local/bin/datasets

# Crear directorios de trabajo
WORKDIR /app

# Copiar package.json y package-lock.json primero para aprovechar la cache
COPY src/modules/acquisition/ncbi_cli/package*.json ./

# Instalar dependencias de Node.js
RUN npm install

# Copiar resto de archivos
COPY src/modules/acquisition/ncbi_cli/ ./

# Crear directorios necesarios
RUN mkdir -p /data/raw/genomes /app/tmp

# Exponer puerto
EXPOSE 4006

# Comando para iniciar el servidor (en lugar de ENTRYPOINT)
CMD ["node", "server.js"]