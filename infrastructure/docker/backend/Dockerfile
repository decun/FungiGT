FROM node:18-alpine

WORKDIR /app

# Crear package.json si no existe
RUN echo '{ \
  "name": "fungigt-backend", \
  "version": "1.0.0", \
  "description": "Backend para FungiGT", \
  "main": "server.js", \
  "scripts": { \
    "start": "node server.js" \
  }, \
  "dependencies": { \
    "express": "^4.18.2", \
    "mongoose": "^6.9.0", \
    "cors": "^2.8.5", \
    "dotenv": "^16.0.3" \
  } \
}' > package.json

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/backend ./

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["npm", "start"]