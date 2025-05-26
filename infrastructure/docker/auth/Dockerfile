FROM node:18-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY src/core/auth/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/core/auth ./

# Exponer el puerto
EXPOSE ${AUTH_PORT:-4001}

# Comando para iniciar la aplicación
CMD ["node", "index.js"] 