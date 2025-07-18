FROM node:18-alpine

# Instalar dependencias del sistema para Sharp, Puppeteer, Chromium, Canvas y LaTeX
RUN apk add --no-cache \
    vips-dev \
    python3 \
    make \
    g++ \
    curl \
    bash \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    font-noto-emoji \
    cairo-dev \
    pango-dev \
    libjpeg-turbo-dev \
    giflib-dev \
    librsvg-dev \
    pixman-dev

# Configurar variables de entorno para Puppeteer
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Crear directorio de trabajo
WORKDIR /app

# Crear directorio de logs
RUN mkdir -p logs

# Copiar package.json y package-lock.json (si existe)
COPY src/modules/ai_agent/drfungito/package*.json ./

# Instalar dependencias Node.js (cambiar npm ci por npm install)
RUN npm install --production && npm cache clean --force

# Copiar el código fuente
COPY src/modules/ai_agent/drfungito/ .

# Crear usuario no-root por seguridad
RUN addgroup -g 1001 -S drfungito && \
    adduser -S drfungito -u 1001 -G drfungito

# Cambiar permisos
RUN chown -R drfungito:drfungito /app
USER drfungito

# Exponer puerto
EXPOSE 4009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:4009/health || exit 1

# Comando por defecto
CMD ["node", "server.js"] 