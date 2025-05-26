#!/bin/bash

echo "======================================"
echo "= Iniciando Servicio de Autenticacion ="
echo "======================================"

# Configurar entorno
export AUTH_PORT=4001
export JWT_SECRET=fungi-gt-secret-key-2024-super-secure
export JWT_EXPIRATION=24h

# Cambiar al directorio del script
cd "$(dirname "$0")"

echo "Instalando dependencias..."
npm install

# Inicializar la base de datos
echo "Inicializando la base de datos..."
node scripts/init.js

echo "Iniciando el servicio de autenticacion..."
node index.js 