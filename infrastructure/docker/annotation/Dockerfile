FROM node:18-alpine

WORKDIR /app

# Este Dockerfile asume que el módulo de anotación usa Node.js
# Ajústalo según la tecnología real que utilice

# Copiar archivos de dependencias (si hay un package.json)
COPY src/modules/annotation/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar el resto de la aplicación
COPY src/modules/annotation ./

# Comando para iniciar la aplicación
CMD ["npm", "start"] 