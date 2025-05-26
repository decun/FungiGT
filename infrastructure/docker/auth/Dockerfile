FROM node:18-alpine

WORKDIR /app

# Crear package.json si no existe o usar el existente
COPY src/core/auth/package*.json ./
RUN test -f package.json || echo '{ \
  "name": "fungigt-auth", \
  "version": "1.0.0", \
  "description": "Servicio de autenticación para FungiGT", \
  "main": "index.js", \
  "scripts": { \
    "start": "node index.js" \
  }, \
  "dependencies": { \
    "express": "^4.18.2", \
    "mongoose": "^6.9.0", \
    "jsonwebtoken": "^9.0.0", \
    "bcrypt": "^5.1.0", \
    "cors": "^2.8.5", \
    "dotenv": "^16.0.3" \
  } \
}' > package.json

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/core/auth ./

# Exponer el puerto
EXPOSE ${AUTH_PORT:-4001}

# Comando para iniciar la aplicación
CMD ["node", "index.js"] 