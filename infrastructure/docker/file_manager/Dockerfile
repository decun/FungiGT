FROM node:18-alpine

# Instalar wget para health check
RUN apk add --no-cache wget

WORKDIR /app

# Copiar package.json
COPY src/modules/file_manager/package.json ./
COPY src/modules/file_manager/package-lock.json ./

# Instalar dependencias
RUN npm install --production

# Copiar código fuente
COPY src/modules/file_manager/ ./

# Crear directorios
RUN mkdir -p temp tmp

EXPOSE 4002

CMD ["node", "server.js"] 