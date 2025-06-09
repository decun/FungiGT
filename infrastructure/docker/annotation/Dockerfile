FROM node:18-alpine

# Instalar Docker CLI y dependencias necesarias
RUN apk add --no-cache docker-cli curl

WORKDIR /app

# Este Dockerfile asume que el módulo de anotación usa Node.js
# Ajústalo según la tecnología real que utilice

# Copiar archivos de dependencias
COPY src/modules/annotation/braker3/package*.json ./

# Instalar dependencias de Node.js
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/annotation/braker3 ./

# Crear directorio de datos
RUN mkdir -p /data

# Exponer el puerto
EXPOSE 3004

# Comando para iniciar la aplicación
CMD ["npm", "start"] 