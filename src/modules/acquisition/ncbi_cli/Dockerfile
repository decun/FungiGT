FROM ubuntu:22.04

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Descargar datasets
RUN curl -o /usr/local/bin/datasets 'https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets' \
    && chmod +x /usr/local/bin/datasets

# Configurar directorio de trabajo
WORKDIR /data

# Comando por defecto
ENTRYPOINT ["datasets"]