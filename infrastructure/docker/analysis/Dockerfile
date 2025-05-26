FROM node:18-alpine

WORKDIR /app

# Este Dockerfile asume que el módulo de análisis usa Node.js
# Ajústalo según la tecnología real que utilice

# Copiar archivos de dependencias (si hay un package.json)
COPY src/modules/analysis/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/analysis ./

# Comando para iniciar la aplicación
CMD ["npm", "start"] 