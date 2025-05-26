FROM node:18-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY src/frontend/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/frontend ./

# Exponer el puerto
EXPOSE 4005

# Comando para iniciar la aplicación
CMD ["npm", "start"] 