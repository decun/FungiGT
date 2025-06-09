FROM node:18-alpine

# Instalar Docker CLI para poder ejecutar comandos docker desde dentro del contenedor
RUN apk add --no-cache docker-cli

WORKDIR /app

# Copiar archivos de dependencias desde la ubicación correcta
COPY src/modules/quality_control/checkm/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/quality_control/checkm/ ./

# Exponer el puerto correcto (el server.js usa puerto 4004)
EXPOSE 4004

# Comando para iniciar la aplicación
CMD ["npm", "start"] 