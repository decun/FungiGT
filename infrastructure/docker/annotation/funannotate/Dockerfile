FROM node:18-alpine

# Instalar Docker CLI y dependencias necesarias
RUN apk add --no-cache docker-cli curl

WORKDIR /app

# Copiar archivos de dependencias
COPY src/modules/annotation/funannotate/package*.json ./

# Instalar dependencias de Node.js
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/annotation/funannotate ./

# Crear directorio de datos
RUN mkdir -p /data

# Exponer el puerto
EXPOSE 3005

# Comando para iniciar la aplicación
CMD ["npm", "start"]