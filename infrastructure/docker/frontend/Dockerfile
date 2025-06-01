FROM node:18-alpine

WORKDIR /app

# Instalar nodemon globalmente
RUN npm install -g nodemon

# Copiar archivos de dependencias
COPY src/frontend/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/frontend ./

# Crear archivo de configuración de base de datos que maneja errores de conexión
RUN echo "const mongoose = require('mongoose'); \n\
console.log('Intentando conectar a MongoDB...'); \n\
let db = null; \n\
try { \n\
  mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/fungigt', { \n\
    useNewUrlParser: true, \n\
    useUnifiedTopology: true, \n\
    serverSelectionTimeoutMS: 5000 \n\
  }).then(() => { \n\
    console.log('Conectado a MongoDB'); \n\
    db = mongoose.connection; \n\
  }).catch(err => { \n\
    console.log('MongoDB connection disabled: ' + err.message); \n\
  }); \n\
} catch (error) { \n\
  console.log('MongoDB connection disabled'); \n\
} \n\
module.exports = db;" > /app/config/database.js

# Exponer el puerto
EXPOSE 4005

# Comando para iniciar la aplicación
CMD ["nodemon", "--exitcrash", "app.js"] 