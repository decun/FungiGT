FROM node:18-alpine

# Instalar curl para healthchecks
RUN apk add --no-cache curl

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
    "mongoose": "^8.15.0", \
    "jsonwebtoken": "^9.0.0", \
    "bcryptjs": "^2.4.3", \
    "cors": "^2.8.5", \
    "dotenv": "^16.0.3" \
  } \
}' > package.json

# Instalar dependencias
RUN npm install

# Copiar código del servicio auth
COPY src/core/auth/index.js ./
COPY src/core/auth/routes ./routes
COPY src/core/auth/middleware ./middleware
COPY src/core/auth/services ./services
COPY src/core/auth/models ./models

# Copiar módulo de database (creado automáticamente por el script)
COPY src/core/auth/database ./database

# Crear usuario no-root para seguridad
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Cambiar permisos
RUN chown -R nextjs:nodejs /app
USER nextjs

# Exponer el puerto
EXPOSE ${AUTH_PORT:-4001}

# Comando para iniciar la aplicación
CMD ["node", "index.js"] 