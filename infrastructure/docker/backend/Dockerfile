FROM node:18-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY src/backend/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/backend ./

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["npm", "start"] 