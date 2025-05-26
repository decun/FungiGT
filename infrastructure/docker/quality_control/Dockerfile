FROM node:18-alpine

WORKDIR /app

# Copiar archivos de dependencias
COPY src/modules/quality_control/checkm/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/quality_control/checkm ./

# Exponer el puerto si es necesario
EXPOSE 3000

# Comando para iniciar la aplicación
CMD ["npm", "start"] 