FROM node:18-alpine

# Instalar curl para healthchecks
RUN apk add --no-cache curl

WORKDIR /app

# Instalar nodemon globalmente
RUN npm install -g nodemon

# Copiar archivos de dependencias
COPY src/frontend/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/frontend ./

# Crear directorio config si no existe
RUN mkdir -p /app/config

# Crear archivo de configuración de base de datos que maneja errores de conexión
RUN echo "const mongoose = require('mongoose'); \n\
console.log('🔄 Intentando conectar a MongoDB...'); \n\
let db = null; \n\
const mongoUri = process.env.MONGODB_URI || 'mongodb://admin:admin123@mongodb:27017/fungigt?authSource=admin'; \n\
try { \n\
  mongoose.connect(mongoUri, { \n\
    serverSelectionTimeoutMS: 10000, \n\
    connectTimeoutMS: 10000, \n\
    socketTimeoutMS: 45000 \n\
  }).then(() => { \n\
    console.log('✅ Conectado a MongoDB desde frontend'); \n\
    db = mongoose.connection; \n\
  }).catch(err => { \n\
    console.log('⚠️ MongoDB connection disabled: ' + err.message); \n\
  }); \n\
} catch (error) { \n\
  console.log('⚠️ MongoDB connection disabled:', error.message); \n\
} \n\
module.exports = db;" > /app/config/database.js

# Crear usuario no-root para seguridad
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Cambiar permisos
RUN chown -R nextjs:nodejs /app
USER nextjs

# Exponer el puerto
EXPOSE ${FRONTEND_PORT:-4005}

# Comando para iniciar la aplicación
CMD ["nodemon", "--exitcrash", "app.js"] 