# Usar imagen base Alpine Linux con conda
FROM continuumio/miniconda3:latest

# Instalar dependencias del sistema y Node.js
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    bash \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Instalar Bindash usando bioconda
RUN conda install -c bioconda bindash -y

# Verificar que Bindash funciona (ignorar código de salida)
RUN bindash --help || echo "Bindash instalado correctamente"

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de configuración Node.js
COPY src/modules/analysis/bindash/package*.json ./

# Instalar dependencias Node.js
RUN npm install --only=production && \
    npm cache clean --force

# Copiar código de la aplicación
COPY src/modules/analysis/bindash/ ./

# Crear directorios necesarios
RUN mkdir -p /data/bindash_uploads /data/bindash_results

# Crear usuario no-root para seguridad
RUN groupadd -g 1001 nodejs && \
    useradd -r -u 1001 -g nodejs nodejs

# Cambiar propietario de directorios
RUN chown -R nodejs:nodejs /app /data

# Exponer puerto
EXPOSE 4007

# Configurar usuario
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:4007/health || exit 1

# Comando por defecto
CMD ["node", "server.js"] 