FROM node:18-alpine

# Instalar dependencias del sistema
RUN apk add --no-cache \
    python3 \
    py3-pip \
    docker-cli \
    curl \
    bash \
    shadow

# Crear directorio de trabajo
WORKDIR /app

# Copiar package.json y package-lock.json
COPY src/modules/analysis/eggnog/package*.json ./

# Instalar dependencias de Node.js
RUN npm ci --only=production

# Copiar código fuente
COPY src/modules/analysis/eggnog/ .

# Crear directorios necesarios
RUN mkdir -p /data/eggnog_uploads \
    && mkdir -p /data/eggnog_results \
    && mkdir -p /data/eggnog_db \
    && mkdir -p logs

# Crear directorios con permisos apropiados
RUN chown -R node:node /app /data

# NOTA: Ejecutamos como root para acceder a Docker socket
# El código Node.js manejará la seguridad internamente

# Exponer puerto
EXPOSE 3001

# Variables de entorno
ENV NODE_ENV=production
ENV PORT=3001

# Comando de inicio
CMD ["npm", "start"] 